# Invoice Data Extractor

A two-stage LLM pipeline for extracting structured data from invoices using Ollama and vision models.

## Features

- **Multi-format Support**: PNG, JPG, PDF, DOCX, XLSX
- **Two-Stage Extraction**:
  1. **Vision LLM** (llama3.2-vision): Extracts all raw text from invoice images/documents
  2. **Text LLM** (llama3): Structures extracted text into standardized JSON format
- **Structured Output**: Company info, bill details, line items, totals, taxes
- **Docker Support**: Full containerization with GPU acceleration
- **REST API**: FastAPI-based API with automatic documentation

## Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────────┐     ┌─────────────┐
│   Upload    │────▶│  Vision LLM      │────▶│  Structure LLM   │────▶│   JSON      │
│  (Invoice)  │     │  (llama3.2-v)    │     │  (llama3)        │     │   Output    │
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
docker-compose up -d

# Pull models (if not done automatically)
docker-compose exec ollama ollama pull llama3
docker-compose exec ollama ollama pull llama3.2-vision
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
python test_extraction.py
```

Update `test_extraction.py` with your invoice file path.

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | `http://ollama:11434` | Ollama service URL |
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
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── setup.sh
└── test_extraction.py
```

### Running Locally (without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Start Ollama service
ollama serve

# Pull models
ollama pull llama3
ollama pull llama3.2-vision

# Run API
uvicorn app.main:app --reload
```

## Troubleshooting

### GPU Issues

If you don't have an NVIDIA GPU, remove the GPU requirements from `docker-compose.yml`:

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
docker-compose logs -f ollama
docker-compose logs -f invoice-api
```

### Memory Issues

If experiencing OOM errors, reduce batch size or use smaller models.

## License

MIT
