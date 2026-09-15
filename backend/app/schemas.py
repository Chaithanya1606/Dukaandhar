from pydantic import BaseModel, Field
from typing import List, Optional

class BillItemCreate(BaseModel):
    product_id: int
    brand: str
    grade: str
    hsn_code: str = "2523"
    quantity_bags: int = Field(gt=0)
    weight_tonnes: float
    unit_price: float = Field(ge=0)
    total_price: float = Field(ge=0)

class BillCreate(BaseModel):
    customer_name: str
    customer_phone: Optional[str] = ""
    delivery_site: Optional[str] = ""
    vehicle_no: Optional[str] = ""
    items: List[BillItemCreate]
    discount: float = 0.0
    transport_charges: float = 0.0
    hamali_charges: float = 0.0
    gst_rate: float = 0.0
    payment_mode: str = "Cash" # Cash, UPI, Credit / Udhar, Cheque
    amount_paid: float
    notes: Optional[str] = ""

class ExpenseCreate(BaseModel):
    date: str
    category: str
    description: str
    amount: float = Field(gt=0)
    payment_mode: str = "Cash"
    vendor_name: Optional[str] = ""

class ProductCreate(BaseModel):
    brand: str
    grade: str
    hsn_code: str = "2523"
    bag_weight_kg: float = 50.0
    purchase_price: float
    selling_price: float
    stock_bags: int = 0

class ProductUpdate(BaseModel):
    brand: Optional[str] = None
    grade: Optional[str] = None
    selling_price: Optional[float] = None
    purchase_price: Optional[float] = None
    stock_bags: Optional[int] = None

class StoreProfileUpdate(BaseModel):
    store_name: str
    owner_name: Optional[str] = ""
    phone: str
    alt_phone: Optional[str] = ""
    address: str
    gstin: Optional[str] = ""
    upi_id: Optional[str] = ""
    bill_footer_note: Optional[str] = ""

class CustomerPaymentCreate(BaseModel):
    customer_id: int
    amount: float = Field(gt=0)
    payment_mode: str = "Cash"
    notes: Optional[str] = ""
