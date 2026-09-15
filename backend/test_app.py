import os
import sys
import tempfile
import uuid

os.environ.setdefault("INITIAL_ADMIN_USERNAME", "admin")
os.environ.setdefault("INITIAL_ADMIN_PASSWORD", "test-password-123")
os.environ["APP_ENV"] = "development"
os.environ["DATABASE_PATH"] = os.path.join(
    tempfile.gettempdir(), f"cement_store_test_{uuid.uuid4().hex}.db"
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import init_db, get_db_connection
from app.pdf_generator import generate_bill_pdf
from fastapi.testclient import TestClient
from app.main import app

def run_tests():
    print("=== 1. Initializing Database ===")
    init_db()
    
    client = TestClient(app)

    login_res = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "test-password-123"},
    )
    assert login_res.status_code == 200, f"Login error: {login_res.text}"

    print("\n=== 2. Testing Store Profile API ===")
    res = client.get("/api/profile")
    assert res.status_code == 200, f"Profile error: {res.text}"
    profile = res.json()
    print("Store Name:", profile["store_name"])
    print("GSTIN:", profile["gstin"])
    print("UPI:", profile["upi_id"])

    print("\n=== 3. Testing Products API ===")
    res = client.get("/api/products")
    assert res.status_code == 200, f"Products error: {res.text}"
    products = res.json()
    print(f"Loaded {len(products)} cement products.")
    first_prod = products[0]
    print(f"Sample: {first_prod['brand']} - {first_prod['grade']} @ Rs. {first_prod['selling_price']}/bag")

    print("\n=== 4. Testing Bill Creation ===")
    bill_payload = {
        "customer_name": "Balaji Builders & Contractors",
        "customer_phone": "9848012345",
        "delivery_site": "Sector 4, Dream Valley Project",
        "vehicle_no": "TS 08 UB 5678",
        "items": [
            {
                "product_id": first_prod["id"],
                "brand": first_prod["brand"],
                "grade": first_prod["grade"],
                "hsn_code": "2523",
                "quantity_bags": 100,
                "weight_tonnes": 5.0,
                "unit_price": first_prod["selling_price"],
                "total_price": 100 * first_prod["selling_price"]
            }
        ],
        "discount": 500.0,
        "transport_charges": 1500.0,
        "hamali_charges": 400.0,
        "gst_rate": 0.0,
        "payment_mode": "UPI",
        "amount_paid": 20000.0, # Part payment, remaining due
        "notes": "Delivered in morning batch"
    }

    res = client.post("/api/bills", json=bill_payload)
    assert res.status_code == 200, f"Bill creation error: {res.text}"
    bill_data = res.json()
    print("Created Bill:", bill_data["bill_number"])
    print(f"Grand Total: Rs. {bill_data['grand_total']:,.2f}")
    print(f"Balance Due: Rs. {bill_data['due_amount']:,.2f}")
    bill_id = bill_data["bill_id"]

    print("\n=== 5. Testing PDF Invoice Generation ===")
    pdf_res = client.get(f"/api/bills/{bill_id}/pdf")
    assert pdf_res.status_code == 200, f"PDF generation error: {pdf_res.text}"
    assert pdf_res.headers["content-type"] == "application/pdf"
    pdf_bytes = pdf_res.content
    print(f"PDF generated successfully! Size: {len(pdf_bytes)} bytes")
    
    # Save a test copy
    sample_pdf_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_invoice.pdf")
    with open(sample_pdf_path, "wb") as f:
        f.write(pdf_bytes)
    print("Saved sample PDF copy to:", sample_pdf_path)

    print("\n=== 6. Testing WhatsApp Link Generation ===")
    wa_res = client.get(f"/api/bills/{bill_id}/whatsapp")
    assert wa_res.status_code == 200, f"WhatsApp error: {wa_res.text}"
    wa_data = wa_res.json()
    print("WhatsApp Share URL:", wa_data["whatsapp_url"][:80] + "...")

    print("\n=== 7. Testing Expense Logging ===")
    exp_payload = {
        "date": "2026-09-15",
        "category": "Hamali / Labor",
        "description": "Unloading 100 bags from lorry",
        "amount": 400.0,
        "payment_mode": "Cash",
        "vendor_name": "Site Laborers"
    }
    exp_res = client.post("/api/expenses", json=exp_payload)
    assert exp_res.status_code == 200, f"Expense error: {exp_res.text}"
    print("Expense logged successfully!")

    print("\n=== 8. Testing Monthly, Quarterly, and Yearly Reports ===")
    # Monthly
    m_res = client.get("/api/reports/summary?period=monthly&year=2026&month=9")
    assert m_res.status_code == 200
    m_data = m_res.json()
    print(f"[Monthly {m_data['period_title']}]: Sales = Rs. {m_data['sales']['total_sales']:,.2f}, Expenses = Rs. {m_data['total_expenses']:,.2f}, Net Profit = Rs. {m_data['net_profit']:,.2f}")

    # Quarterly
    q_res = client.get("/api/reports/summary?period=quarterly&year=2026&quarter=3")
    assert q_res.status_code == 200
    q_data = q_res.json()
    print(f"[Quarterly {q_data['period_title']}]: Sales = Rs. {q_data['sales']['total_sales']:,.2f}, Expenses = Rs. {q_data['total_expenses']:,.2f}, Net Profit = Rs. {q_data['net_profit']:,.2f}")

    # Yearly
    y_res = client.get("/api/reports/summary?period=yearly&year=2026")
    assert y_res.status_code == 200
    y_data = y_res.json()
    print(f"[Yearly {y_data['period_title']}]: Sales = Rs. {y_data['sales']['total_sales']:,.2f}, Expenses = Rs. {y_data['total_expenses']:,.2f}, Net Profit = Rs. {y_data['net_profit']:,.2f}")

    print("\n=== 9. Testing Customer Khata / Ledger ===")
    cust_res = client.get("/api/customers")
    assert cust_res.status_code == 200
    customers = cust_res.json()
    print(f"Total customers in khata: {len(customers)}")
    for c in customers:
        if c["name"] == "Balaji Builders & Contractors":
            print(f"Customer '{c['name']}': Pending Due = Rs. {c['pending_balance']:,.2f}")

    print("\nALL VERIFICATION TESTS PASSED SUCCESSFULLY! [OK]")

if __name__ == "__main__":
    run_tests()
