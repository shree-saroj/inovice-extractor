from typing import List, Optional

from pydantic import BaseModel, Field


class InvoiceItem(BaseModel):
    sno: Optional[int] = None
    particular: str = ""
    quantity: str = ""
    rate: float = 0.0
    amount: float = 0.0


class InvoiceData(BaseModel):
    # Header Information
    company_name: str = ""
    company_address: str = ""
    phone: str = ""
    pan: str = ""

    # Bill Information
    bill_no: str = ""
    bill_to: str = ""
    bill_address: str = ""
    tpin: str = ""
    miti: str = ""
    date: str = ""
    mode: str = ""

    # Line Items
    items: List[InvoiceItem] = []

    # Totals
    sub_total: float = 0.0
    discount: float = 0.0
    taxable_amount: float = 0.0
    tax: float = 0.0
    grand_total: float = 0.0
    amount_in_words: str = ""

    # Additional
    notes: str = ""
    print_date: str = ""
