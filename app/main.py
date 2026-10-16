import logging
from typing import Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.extractors.structure_extractor import StructureExtractor
from app.extractors.vision_extractor import VisionExtractor
from app.models import InvoiceData

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Invoice Data Extractor",
    description="Document text extraction and LLM structuring for invoices",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize extractors
vision_extractor = VisionExtractor()
structure_extractor = StructureExtractor()

# File size limit (50MB)
MAX_FILE_SIZE = 50 * 1024 * 1024


class ExtractionResponse(BaseModel):
    success: bool
    data: Optional[InvoiceData] = None
    error: Optional[str] = None
    stage1_output: Optional[str] = None  # Raw extraction (for debugging)


@app.post("/extract", response_model=ExtractionResponse)
async def extract_invoice(
    file: UploadFile = File(...),
    include_raw: bool = False,  # Include stage 1 output for debugging
):
    """
    Two-stage invoice extraction:
    1. OCR/vision or document parsing extracts raw text
    2. Structure LLM formats data into JSON

    Supported formats: PNG, JPG, PDF, DOCX, XLSX
    """
    raw_text = None
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")

        # Read file content
        content = await file.read()

        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Max {MAX_FILE_SIZE // 1024 // 1024}MB",
            )

        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Empty file")

        logger.info(f"Processing file: {file.filename} ({len(content)} bytes)")

        # STAGE 1: Extract all raw data using Vision LLM
        logger.info("Stage 1: Extracting raw document text (OCR/vision)...")
        raw_text = await vision_extractor.extract(content, file.filename)

        if not raw_text or len(raw_text.strip()) < 10:
            raise HTTPException(
                status_code=400, detail="No content could be extracted from the file"
            )

        logger.info(f"Stage 1 complete: Extracted {len(raw_text)} characters")

        # STAGE 2: Structure data using Text LLM
        logger.info("Stage 2: Structuring data with Text LLM...")
        structured_data = await structure_extractor.structure(raw_text)

        logger.info("Stage 2 complete: Data structured successfully")

        # Build response
        response = ExtractionResponse(success=True, data=structured_data)

        if include_raw:
            response.stage1_output = raw_text

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Extraction failed")
        return ExtractionResponse(success=False, error=str(e), stage1_output=raw_text if include_raw else None)


@app.get("/health")
async def health_check():
    """Check if services are running"""
    try:
        # Readiness checks should not trigger expensive inference.
        models = await vision_extractor.client.list()
        names = [(m.get("model") or m.get("name")) for m in models["models"]]
        required = [vision_extractor.model, structure_extractor.model]
        missing = [m for m in required if m not in names and f"{m}:latest" not in names]
        return {
            "status": "unhealthy" if missing else "healthy",
            "missing_models": missing,
            "services": {
                "api": "running",
                "ollama": "connected",
                "vision_model": vision_extractor.model,
                "structure_model": structure_extractor.model,
            },
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@app.get("/models")
async def list_models():
    """List available Ollama models"""
    try:
        models = await vision_extractor.client.list()
        return {"models": [(m.get("model") or m.get("name")) for m in models["models"]]}
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
