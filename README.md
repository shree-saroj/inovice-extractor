# Invoice Data Extractor

A two-stage pipeline for extracting structured invoice data using OCR, document parsing, and local Ollama models.

## Features

- **Multi-format Support**: PNG, JPG, PDF, DOCX, XLSX
- **Two-Stage Extraction**:
  1. **Text extraction**: Tesseract OCR reads printed invoice images/PDFs; `llava` is a fallback when OCR finds too little text. DOCX/XLSX text is read directly.
  2. **Text LLM** (llama3): Structures extracted text into standardized JSON format
- **Structured Output**: Company info, bill details, line items, totals, taxes
- **Docker Support**: Full containerization with GPU acceleration
- **REST API**: FastAPI-based API with automatic documentation

## Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────────┐     ┌─────────────┐
│   Upload    │────▶│  OCR / Vision    │────▶│  Structure LLM   │────▶│   JSON      │
│  (Invoice)  │     │  (llava)    │     │  (llama3)        │     │   Output    │
└─────────────┘     └──────────────────┘     └──────────────────┘     └─────────────┘
```

## Quick Start

### Prerequisites

- Docker & Docker Compose with NVIDIA GPU support
- NVIDIA GPU (recommended for performance)

### Setup

```bash
# Make setup script executable
chmod +x setup.sh

# Run setup (downloads models and starts services)
./setup.sh
```

### Manual Setup

```bash
# Start services
docker compose up -d

# Pull models (if not done automatically)
docker compose exec ollama ollama pull llama3
docker compose exec ollama ollama pull llava
```

## API Usage

### Extract Invoice

```bash
curl -X POST "http://localhost:8000/extract" \
  -F "file=@invoice.pdf" \
  -F "include_raw=false"
```

### Health Check

```bash
curl "http://localhost:8000/health"
```

### List Models

```bash
curl "http://localhost:8000/models"
```

## API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Response Format

```json
{
  "success": true,
  "data": {
    "company_name": "Company Name",
    "company_address": "Company Address",
    "phone": "+1234567890",
    "pan": "123456789",
    "bill_no": "INV-001",
    "bill_to": "Customer Name",
    "bill_address": "Customer Address",
    "tpin": "",
    "miti": "",
    "date": "2024-01-15",
    "mode": "Credit",
    "items": [
      {
        "sno": 1,
        "particular": "Product A",
        "quantity": "10 pcs",
        "rate": 100.00,
        "amount": 1000.00
      }
    ],
    "sub_total": 1000.00,
    "discount": 0.00,
    "taxable_amount": 1000.00,
    "tax": 130.00,
    "grand_total": 1130.00,
    "amount_in_words": "One Thousand One Hundred Thirty Only",
    "notes": "",
    "print_date": "2024-01-15 10:30:00"
  }
}
```

## Testing

```bash
# Run test script
venv/bin/python -m unittest discover -s tests -v

# Manual extraction (requires invoice.png)
venv/bin/python test_extraction.py
```

Update `test_extraction.py` with your invoice file path.

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama service URL (Compose uses `http://ollama:11434`) |
| `PYTHONUNBUFFERED` | `1` | Python output buffering |

### File Size Limits

- **Maximum**: 50MB
- **Minimum**: 1KB

## Supported Fields

### Header Information
- Company name, address, phone, PAN

### Bill Information
- Bill number, customer details, TPIN, MITI, date, payment mode

### Line Items
- Serial number, particular, quantity, rate, amount

### Totals
- Sub-total, discount, taxable amount, tax, grand total, amount in words

### Additional
- Notes, print date

## Development

### Project Structure

```
invoice-extractor/
├── app/
│   ├── main.py                 # FastAPI application
│   ├── models.py               # Pydantic models
│   ├── extractors/
│   │   ├── vision_extractor.py    # Stage 1: Vision extraction
│   │   └── structure_extractor.py # Stage 2: Data structuring
│   └── utils/
│       └── file_handler.py     # File handling utilities
├── compose.yaml
├── Dockerfile
├── requirements.txt
├── setup.sh
└── test_extraction.py
```

### Running Locally (without Docker)

```bash
# Install system dependencies (Debian/Ubuntu)
sudo apt-get install tesseract-ocr poppler-utils libmagic1

# Install Python dependencies
pip install -r requirements.txt

# Start Ollama service
ollama serve

# Pull models
ollama pull llama3
ollama pull llava

# Run API
uvicorn app.main:app --reload
```

## Troubleshooting

### GPU Issues

If you don't have an NVIDIA GPU, remove the GPU requirements from `compose.yaml`:

```yaml
services:
  invoice-api:
    # Remove the deploy section
  ollama:
    # Remove the deploy section
```

### Model Loading

First run may take longer as models are downloaded. Check logs:

```bash
docker compose logs -f ollama
docker compose logs -f invoice-api
```

### Memory Issues

If experiencing OOM errors, reduce batch size or use smaller models.

## License

MIT

## Local running and debugging

Local development uses port 8001 (`API_PORT`) so Docker can keep port 8000.

The local launcher installs dependencies into `venv`, pulls the configured models,
and starts Uvicorn with reload:

```bash
cp .env.example .env
# Ollama must already be running locally or in Docker:
docker compose up -d ollama
./run_local.sh
```

Open http://127.0.0.1:8001/docs to upload an invoice. For raw stage-one output,
set the `include_raw` query parameter to true:

```bash
curl 'http://127.0.0.1:8001/extract?include_raw=true' -F 'file=@invoice.pdf'
```

Set breakpoints in `app/extractors/vision_extractor.py` or
`app/extractors/structure_extractor.py`. In VS Code, install the Python Debugger
extension, select **Debug invoice API**, and press F5 after stopping the local
launcher. The launch configuration uses `venv/bin/python` and `.env`, without
reload so breakpoints stay in the server process. For another debugger client,
`./run_local.sh --debug` listens on localhost port 5678; select
**Attach to local invoice API** to connect to it. Python 3.14 is used in Docker
and in the tested local environment.

`VISION_MODEL` defaults to `llava`; `STRUCTURE_MODEL` defaults to `llama3`.
Both are configurable through `.env` locally and environment variables in Compose.
The `/health` endpoint checks connection and model presence; it does not prove
that inference works. API failures log full tracebacks; when stage two fails,
`include_raw=true` preserves the stage-one output in the response.

### Unsupported `mllama` architecture

`unknown model architecture: 'mllama'` means the Ollama server's runner cannot
load `llama3.2-vision`. Updating the Python client alone cannot fix the runner.
This project defaults to `llava` to avoid that failing architecture. Pull the
model and recreate the API to apply the code and configuration:

```bash
docker compose exec -T ollama ollama pull llava
docker compose up -d --build invoice-api
```

For local execution set `VISION_MODEL=llava` in `.env` and run `./run_local.sh`.
If you specifically need `llama3.2-vision`, use an Ollama runtime that supports
`mllama` and test a real image request against that server before changing
`VISION_MODEL`. Check the server you actually call with
`curl http://localhost:11434/api/version`; the CLI version may differ.

PDF inputs require Poppler (`pdftoppm`); MIME detection requires libmagic.
On Debian/Ubuntu install `poppler-utils libmagic1` through your package manager.

### Verify real model extraction

With the services running and both models downloaded:

```bash
venv/bin/python tests/smoke_extraction.py
# To verify the local API instead:
venv/bin/python tests/smoke_extraction.py --url http://127.0.0.1:8001
```

This creates a temporary sample invoice in PNG, PDF, DOCX, and XLSX formats,
calls both extraction stages using the actual models, and checks the invoice
number, line items, and grand total. Detailed responses are written to
`/tmp/invoice-smoke-results.json`. These checks verify a simple sample; review
accuracy on your own invoices before relying on extracted values.

### Printed invoice accuracy

Image and PDF extraction now uses Tesseract OCR first, then the text model
structures that transcription. Vision-only `llava` invented fields in the
sample verification, so it is retained only as a fallback for low-text images.
Set `OCR_ENABLED=false` only when deliberately testing vision-only behavior.
Docker includes Tesseract. Local development requires `tesseract-ocr` (including
English language data), Poppler, and libmagic. A project-local Tesseract wrapper
at `venv/bin/tesseract` is also supported. JSON generation is constrained to JSON
format and both model stages have output limits.

OCR can confuse similar characters such as `0` and `O`, including in invoice
numbers. The synthetic smoke fixture uses a monospace font; passing it does not
guarantee accurate transcription of every font, scan, handwriting, or language.
