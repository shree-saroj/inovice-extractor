import base64
import io
import os
import shutil
import asyncio
import sys
from pathlib import Path

import magic
import ollama
import pandas as pd
from docx import Document
from pdf2image import convert_from_bytes
from PIL import Image


class VisionExtractor:
    """Stage 1: Extract ALL raw data from file using Vision LLM"""

    def __init__(self, model: str | None = None):
        self.model = model or os.getenv("VISION_MODEL", "llava")
        self.client = ollama.AsyncClient(host=os.getenv("OLLAMA_HOST", "http://localhost:11434"))
        self.mime = magic.Magic(mime=True)

    def _image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL Image to base64 string"""
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()

    async def _extract_printed_text(self, image: Image.Image) -> str:
        """Prefer OCR for printed text; generative vision can invent invoice values."""
        if os.getenv("OCR_ENABLED", "true").lower() not in {"1", "true", "yes"}:
            return ""
        executable = shutil.which("tesseract")
        local_executable = Path(sys.prefix) / "bin" / "tesseract"
        if executable is None and local_executable.is_file():
            executable = str(local_executable)
        if executable is None:
            raise RuntimeError(
                "OCR is enabled but tesseract is not installed. Install tesseract-ocr "
                "or explicitly set OCR_ENABLED=false to use vision-only extraction."
            )
        buffer = io.BytesIO()
        image.convert("RGB").save(buffer, format="PNG")
        process = await asyncio.create_subprocess_exec(
            executable, "stdin", "stdout", "--psm", "6",
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            output, error = await asyncio.wait_for(process.communicate(buffer.getvalue()), timeout=60)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise RuntimeError("OCR timed out after 60 seconds")
        if process.returncode:
            raise RuntimeError(f"OCR failed: {error.decode(errors='replace').strip()}")
        text = output.decode(errors="replace").strip()
        return text if sum(char.isalnum() for char in text) >= 20 else ""

    async def extract_from_image(self, image_bytes: bytes) -> str:
        """Extract all text from image using Vision LLM"""
        try:
            image = Image.open(io.BytesIO(image_bytes))
            text = await self._extract_printed_text(image)
            if text:
                return text
            image_b64 = self._image_to_base64(image)

            prompt = """
            Carefully read and extract ALL text content from this invoice document.
            Include EVERYTHING you can see:
            - Company name and address at top
            - Phone numbers, PAN, TPIN
            - Bill number, date, customer details
            - ALL line items with their details
            - All totals, discounts, taxes
            - Any notes or footer information

            Return the raw text exactly as you see it. Do not format or structure yet.
            Just extract all visible text content. Do not invent missing content or repeat text.
            Stop after the final visible line.
            """

            response = await self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt, "images": [image_b64]}],
                options={
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "num_predict": 2048,
                    "repeat_penalty": 1.1,
                },
            )

            return response["message"]["content"]
        except Exception as e:
            if "unknown model architecture" in str(e):
                raise RuntimeError(
                    f"Vision model {self.model!r} is unsupported by the Ollama runner at "
                    f"{os.getenv('OLLAMA_HOST', 'http://localhost:11434')}. "
                    "Run `ollama pull llava`, set VISION_MODEL=llava, and restart the API. "
                    "Alternatively install an Ollama runtime supporting this model architecture. "
                    f"Original error: {e}"
                ) from e
            raise RuntimeError(f"Vision extraction failed: {e}") from e

    async def extract_from_pdf(self, pdf_bytes: bytes) -> str:
        """Extract all text from PDF using Vision LLM"""
        try:
            # Convert PDF pages to images
            images = convert_from_bytes(pdf_bytes)

            all_text = []
            for i, img in enumerate(images):
                print(f"Processing PDF page {i + 1}/{len(images)}")
                buffer = io.BytesIO()
                img.save(buffer, format="PNG")
                text = await self.extract_from_image(buffer.getvalue())
                all_text.append(f"--- PAGE {i + 1} ---\n{text}")

            return "\n\n".join(all_text)
        except Exception as e:
            raise RuntimeError(f"PDF extraction failed: {str(e)}")

    async def extract_from_docx(self, docx_bytes: bytes) -> str:
        """Extract text from DOCX file"""
        try:
            doc = Document(io.BytesIO(docx_bytes))
            text = []

            for para in doc.paragraphs:
                text.append(para.text)

            for table in doc.tables:
                for row in table.rows:
                    row_text = [cell.text for cell in row.cells]
                    text.append(" | ".join(row_text))

            return "\n".join(text)
        except Exception as e:
            raise RuntimeError(f"DOCX extraction failed: {str(e)}")

    async def extract_from_excel(self, excel_bytes: bytes) -> str:
        """Extract text from Excel file"""
        try:
            df = pd.read_excel(io.BytesIO(excel_bytes), sheet_name=None)

            all_text = []
            for sheet_name, sheet_df in df.items():
                all_text.append(f"=== Sheet: {sheet_name} ===")
                all_text.append(sheet_df.to_string())

            return "\n\n".join(all_text)
        except Exception as e:
            raise RuntimeError(f"Excel extraction failed: {str(e)}")

    async def extract(self, file_bytes: bytes, filename: str) -> str:
        """Main extraction method - routes to appropriate handler"""
        file_ext = filename.lower().split(".")[-1]

        if file_ext in ["png", "jpg", "jpeg", "gif", "bmp", "webp"]:
            return await self.extract_from_image(file_bytes)

        elif file_ext == "pdf":
            return await self.extract_from_pdf(file_bytes)

        elif file_ext == "docx":
            return await self.extract_from_docx(file_bytes)

        elif file_ext in ["xlsx", "xls"]:
            return await self.extract_from_excel(file_bytes)

        else:
            # Try to detect file type
            file_type = self.mime.from_buffer(file_bytes)

            if "image" in file_type:
                return await self.extract_from_image(file_bytes)
            elif "pdf" in file_type:
                return await self.extract_from_pdf(file_bytes)
            else:
                raise ValueError(f"Unsupported file type: {file_ext}")
