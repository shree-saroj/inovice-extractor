import json
import re

import ollama

from app.models import InvoiceData, InvoiceItem


class StructureExtractor:
    """Stage 2: Structure raw text into proper JSON using Text LLM"""

    def __init__(self, model: str = "llama3"):
        self.model = model

    async def structure(self, raw_text: str) -> InvoiceData:
        """Structure extracted text into InvoiceData model"""

        prompt = f"""
You are an expert invoice data structuring assistant. Your task is to extract and structure
invoice information from the following raw text into a precise JSON format.

RAW INVOICE TEXT:
{raw_text}

Extract the following fields and return ONLY valid JSON (no markdown, no explanations):

{{
    "company_name": "extract supplier/company name from header",
    "company_address": "extract company address",
    "phone": "extract phone number",
    "pan": "extract PAN number (format like :060263694)",
    "bill_no": "extract bill number (format like :PGSI-26-2082/83)",
    "bill_to": "extract customer name",
    "bill_address": "extract customer address if available",
    "tpin": "extract TPIN if present",
    "miti": "extract MITI number if present",
    "date": "extract date in YYYY-MM-DD format",
    "mode": "extract payment mode (Credit/Cash/etc)",
    "items": [
        {{
            "sno": 1,
            "particular": "item name",
            "quantity": "quantity with unit",
            "rate": 0.00,
            "amount": 0.00
        }}
    ],
    "sub_total": 0.00,
    "discount": 0.00,
    "taxable_amount": 0.00,
    "tax": 0.00,
    "grand_total": 0.00,
    "amount_in_words": "extract amount in words",
    "notes": "extract any notes",
    "print_date": "extract print date/time if available"
}}

IMPORTANT RULES:
1. Extract ALL line items from the invoice table (Sno, Particular, Quantity, Rate, Amount)
2. Convert all monetary values to float (remove commas, currency symbols)
3. For dates, convert to YYYY-MM-DD format
4. If a field is not found, use empty string "" or 0.0
5. Return ONLY the JSON object, no other text
6. Ensure all numbers are actual numbers, not strings
7. Match the exact format shown above
"""

        try:
            response = ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={
                    "temperature": 0.1,  # Low for consistency
                    "top_p": 0.9,
                },
            )

            content = response["message"]["content"]

            # Clean and extract JSON
            json_str = self._extract_json(content)
            data = json.loads(json_str)

            # Convert to Pydantic model for validation
            return self._to_invoice_data(data)

        except json.JSONDecodeError as e:
            raise ValueError(
                f"Invalid JSON returned by LLM: {str(e)}. Response: {content[:500]}"
            )
        except Exception as e:
            raise RuntimeError(f"Structure extraction failed: {str(e)}")

    def _extract_json(self, text: str) -> str:
        """Extract JSON from LLM response"""
        # Remove markdown code blocks
        text = re.sub(r"```json\s*", "", text)
        text = re.sub(r"```\s*", "", text)

        # Find JSON object
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            return json_match.group()

        return text

    def _to_invoice_data(self, data: dict) -> InvoiceData:
        """Convert dict to InvoiceData model"""
        items = []
        for item in data.get("items", []):
            items.append(
                InvoiceItem(
                    sno=item.get("sno"),
                    particular=str(item.get("particular", "")),
                    quantity=str(item.get("quantity", "")),
                    rate=float(item.get("rate", 0) or 0),
                    amount=float(item.get("amount", 0) or 0),
                )
            )

        return InvoiceData(
            company_name=str(data.get("company_name", "")),
            company_address=str(data.get("company_address", "")),
            phone=str(data.get("phone", "")),
            pan=str(data.get("pan", "")),
            bill_no=str(data.get("bill_no", "")),
            bill_to=str(data.get("bill_to", "")),
            bill_address=str(data.get("bill_address", "")),
            tpin=str(data.get("tpin", "")),
            miti=str(data.get("miti", "")),
            date=str(data.get("date", "")),
            mode=str(data.get("mode", "")),
            items=items,
            sub_total=float(data.get("sub_total", 0) or 0),
            discount=float(data.get("discount", 0) or 0),
            taxable_amount=float(data.get("taxable_amount", 0) or 0),
            tax=float(data.get("tax", 0) or 0),
            grand_total=float(data.get("grand_total", 0) or 0),
            amount_in_words=str(data.get("amount_in_words", "")),
            notes=str(data.get("notes", "")),
            print_date=str(data.get("print_date", "")),
        )
