import os
import hashlib
import secrets
import urllib.parse
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Response, Query, Depends, Request
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, FileResponse, HTMLResponse

from app.database import get_db_connection, init_db, hash_password, verify_password
from app.schemas import (
    BillCreate, ExpenseCreate, ProductCreate, ProductUpdate,
    StoreProfileUpdate, CustomerPaymentCreate
)
from app.pdf_generator import generate_bill_pdf

app = FastAPI(
    title="Cement Resale Store Billing & Accounts API",
    version="1.0.0",
)

SESSION_COOKIE = "cement_store_session"
SESSION_DAYS = 14


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)


class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=200)


def session_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def current_user_from_token(token: str | None):
    if not token:
        return None
    conn = get_db_connection()
    row = conn.execute(
        """
        SELECT u.id, u.username, u.is_admin
        FROM sessions s JOIN users u ON u.id = s.user_id
        WHERE s.token_hash = ? AND s.expires_at > ? AND u.is_active = 1
        """,
        (session_digest(token), datetime.utcnow().isoformat()),
    ).fetchone()
    conn.close()
    return row


@app.middleware("http")
async def require_api_session(request: Request, call_next):
    if request.url.path.startswith("/api/") and request.url.path != "/api/auth/login":
        user = current_user_from_token(request.cookies.get(SESSION_COOKIE))
        if not user:
            return Response(
                content='{"detail":"Login required"}',
                status_code=401,
                media_type="application/json",
            )
        request.state.user = user
    return await call_next(request)


@app.post("/api/auth/login")
def login(credentials: LoginRequest, response: Response):
    conn = get_db_connection()
    user = conn.execute(
        "SELECT id, username, password_hash, is_admin FROM users WHERE username = ? COLLATE NOCASE AND is_active = 1",
        (credentials.username.strip(),),
    ).fetchone()
    if not user or not verify_password(credentials.password, user["password_hash"]):
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(days=SESSION_DAYS)
    conn.execute(
        "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
        (session_digest(token), user["id"], expires_at.isoformat()),
    )
    conn.commit()
    conn.close()
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=os.getenv("APP_ENV", "development").lower() == "production",
        samesite="lax",
    )
    return {"username": user["username"], "is_admin": bool(user["is_admin"])}


@app.post("/api/auth/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        conn = get_db_connection()
        conn.execute("DELETE FROM sessions WHERE token_hash = ?", (session_digest(token),))
        conn.commit()
        conn.close()
    response.delete_cookie(SESSION_COOKIE)
    return {"status": "success"}


@app.get("/api/auth/me")
def get_current_user(request: Request):
    user = request.state.user
    return {"username": user["username"], "is_admin": bool(user["is_admin"])}


@app.post("/api/users")
def create_user(user_in: UserCreate, request: Request):
    if not request.state.user["is_admin"]:
        raise HTTPException(status_code=403, detail="Only an administrator can create users")
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (user_in.username, hash_password(user_in.password)),
        )
        conn.commit()
    except Exception as exc:
        conn.close()
        if "UNIQUE" in str(exc).upper():
            raise HTTPException(status_code=409, detail="Username already exists")
        raise
    conn.close()
    return {"id": cursor.lastrowid, "username": user_in.username}

allowed_origins = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup event to ensure database is created
@app.on_event("startup")
def on_startup():
    init_db()

# --- Store Profile Endpoints ---

@app.get("/api/profile")
def get_profile():
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM store_profile WHERE id = 1").fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Store profile not found")
    return dict(row)

@app.put("/api/profile")
def update_profile(profile: StoreProfileUpdate):
    conn = get_db_connection()
    conn.execute("""
    UPDATE store_profile SET
        store_name = ?, owner_name = ?, phone = ?, alt_phone = ?,
        address = ?, gstin = ?, upi_id = ?, bill_footer_note = ?
    WHERE id = 1
    """, (
        profile.store_name, profile.owner_name, profile.phone, profile.alt_phone,
        profile.address, profile.gstin, profile.upi_id, profile.bill_footer_note
    ))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Store profile updated successfully"}

# --- Products / Cement Inventory Endpoints ---

@app.get("/api/products")
def list_products():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM products WHERE is_active = 1 ORDER BY brand, grade").fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/products")
def create_product(prod: ProductCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO products (brand, grade, hsn_code, bag_weight_kg, purchase_price, selling_price, stock_bags)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (prod.brand, prod.grade, prod.hsn_code, prod.bag_weight_kg, prod.purchase_price, prod.selling_price, prod.stock_bags))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"id": new_id, "status": "success"}

@app.put("/api/products/{prod_id}")
def update_product(prod_id: int, update: ProductUpdate):
    conn = get_db_connection()
    fields = []
    values = []
    if update.brand is not None:
        fields.append("brand = ?")
        values.append(update.brand)
    if update.grade is not None:
        fields.append("grade = ?")
        values.append(update.grade)
    if update.selling_price is not None:
        fields.append("selling_price = ?")
        values.append(update.selling_price)
    if update.purchase_price is not None:
        fields.append("purchase_price = ?")
        values.append(update.purchase_price)
    if update.stock_bags is not None:
        fields.append("stock_bags = ?")
        values.append(update.stock_bags)
    
    if not fields:
        conn.close()
        return {"status": "no change"}
    
    values.append(prod_id)
    conn.execute(f"UPDATE products SET {', '.join(fields)} WHERE id = ?", values)
    conn.commit()
    conn.close()
    return {"status": "success"}

# --- Billing Endpoints ---

@app.post("/api/bills")
def create_bill(bill_in: BillCreate):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Generate sequential bill number: CEM-YYYY-XXXX
    current_year = datetime.now().strftime("%Y")
    count_row = cursor.execute("SELECT COUNT(*) FROM bills").fetchone()
    seq = (count_row[0] if count_row else 0) + 1
    bill_number = f"CEM-{current_year}-{seq:04d}"
    bill_date = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Calculate subtotal, total bags, total weight
    subtotal = sum(item.total_price for item in bill_in.items)
    total_bags = sum(item.quantity_bags for item in bill_in.items)
    total_tonnes = sum(item.weight_tonnes for item in bill_in.items)

    gst_amount = (subtotal - bill_in.discount) * (bill_in.gst_rate / 100.0) if bill_in.gst_rate > 0 else 0.0
    grand_total = subtotal - bill_in.discount + bill_in.transport_charges + bill_in.hamali_charges + gst_amount
    due_amount = max(0.0, grand_total - bill_in.amount_paid)

    # Manage Customer / Khata
    customer_id = None
    if bill_in.customer_name.strip():
        cust_row = cursor.execute("SELECT id, pending_balance FROM customers WHERE name = ? COLLATE NOCASE", (bill_in.customer_name.strip(),)).fetchone()
        if cust_row:
            customer_id = cust_row["id"]
            new_bal = cust_row["pending_balance"] + due_amount
            cursor.execute("UPDATE customers SET pending_balance = ?, phone = COALESCE(NULLIF(?, ''), phone), site_address = COALESCE(NULLIF(?, ''), site_address) WHERE id = ?",
                           (new_bal, bill_in.customer_phone, bill_in.delivery_site, customer_id))
        else:
            cursor.execute("""
            INSERT INTO customers (name, phone, site_address, pending_balance)
            VALUES (?, ?, ?, ?)
            """, (bill_in.customer_name.strip(), bill_in.customer_phone, bill_in.delivery_site, due_amount))
            customer_id = cursor.lastrowid

    # Insert Bill
    cursor.execute("""
    INSERT INTO bills (
        bill_number, date, customer_id, customer_name, customer_phone, delivery_site, vehicle_no,
        subtotal, discount, transport_charges, hamali_charges, gst_rate, gst_amount,
        grand_total, payment_mode, amount_paid, due_amount, total_bags, total_tonnes, notes
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        bill_number, bill_date, customer_id, bill_in.customer_name, bill_in.customer_phone,
        bill_in.delivery_site, bill_in.vehicle_no, subtotal, bill_in.discount,
        bill_in.transport_charges, bill_in.hamali_charges, bill_in.gst_rate, gst_amount,
        grand_total, bill_in.payment_mode, bill_in.amount_paid, due_amount,
        total_bags, total_tonnes, bill_in.notes
    ))
    bill_id = cursor.lastrowid

    # Insert Items and Deduct Stock
    for itm in bill_in.items:
        cursor.execute("""
        INSERT INTO bill_items (bill_id, product_id, brand, grade, hsn_code, quantity_bags, weight_tonnes, unit_price, total_price)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (bill_id, itm.product_id, itm.brand, itm.grade, itm.hsn_code, itm.quantity_bags, itm.weight_tonnes, itm.unit_price, itm.total_price))
        
        # Deduct stock
        cursor.execute("UPDATE products SET stock_bags = MAX(0, stock_bags - ?) WHERE id = ?", (itm.quantity_bags, itm.product_id))

    conn.commit()
    conn.close()

    return {
        "status": "success",
        "bill_id": bill_id,
        "bill_number": bill_number,
        "grand_total": grand_total,
        "due_amount": due_amount
    }

@app.get("/api/bills")
def list_bills(limit: int = 50):
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM bills ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.get("/api/bills/{bill_id}")
def get_bill_detail(bill_id: int):
    conn = get_db_connection()
    bill_row = conn.execute("SELECT * FROM bills WHERE id = ?", (bill_id,)).fetchone()
    if not bill_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Bill not found")
    
    items = conn.execute("SELECT * FROM bill_items WHERE bill_id = ?", (bill_id,)).fetchall()
    conn.close()

    bill_dict = dict(bill_row)
    bill_dict["items"] = [dict(it) for it in items]
    return bill_dict

@app.get("/api/bills/{bill_id}/pdf")
def download_bill_pdf(bill_id: int):
    conn = get_db_connection()
    bill_row = conn.execute("SELECT * FROM bills WHERE id = ?", (bill_id,)).fetchone()
    if not bill_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Bill not found")
    
    items = conn.execute("SELECT * FROM bill_items WHERE bill_id = ?", (bill_id,)).fetchall()
    store_row = conn.execute("SELECT * FROM store_profile WHERE id = 1").fetchone()
    conn.close()

    bill_dict = dict(bill_row)
    bill_dict["items"] = [dict(it) for it in items]
    store_profile = dict(store_row) if store_row else {}

    pdf_buffer = generate_bill_pdf(bill_dict, store_profile)
    filename = f"Invoice_{bill_dict['bill_number']}.pdf"

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={filename}"}
    )

@app.get("/api/bills/{bill_id}/whatsapp")
def get_whatsapp_link(bill_id: int):
    conn = get_db_connection()
    bill_row = conn.execute("SELECT * FROM bills WHERE id = ?", (bill_id,)).fetchone()
    if not bill_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Bill not found")
    
    items = conn.execute("SELECT brand, grade, quantity_bags, total_price FROM bill_items WHERE bill_id = ?", (bill_id,)).fetchall()
    store_row = conn.execute("SELECT store_name, phone, upi_id FROM store_profile WHERE id = 1").fetchone()
    conn.close()

    store_name = store_row["store_name"] if store_row else "Cement Store"
    store_phone = store_row["phone"] if store_row else ""
    upi_id = store_row["upi_id"] if store_row else ""

    item_lines = []
    for it in items:
        item_lines.append(f"• {it['brand']} ({it['grade']}): {it['quantity_bags']} Bags = Rs. {it['total_price']:,.2f}")
    items_text = "\n".join(item_lines)

    msg = (
        f"🧾 *TAX INVOICE - {store_name}*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Bill No: *{bill_row['bill_number']}*\n"
        f"Date: {bill_row['date']}\n"
        f"Customer: {bill_row['customer_name']}\n"
        f"Vehicle No: {bill_row['vehicle_no'] or 'N/A'}\n"
        f"Site: {bill_row['delivery_site'] or 'Direct Store'}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"*Items:*\n{items_text}\n"
        f"Total Bags: *{bill_row['total_bags']} Bags* ({bill_row['total_tonnes']:.2f} MT)\n"
    )
    if bill_row['transport_charges'] > 0:
        msg += f"Transport / Freight: Rs. {bill_row['transport_charges']:,.2f}\n"
    if bill_row['hamali_charges'] > 0:
        msg += f"Hamali / Unloading: Rs. {bill_row['hamali_charges']:,.2f}\n"

    msg += (
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💰 *Grand Total: Rs. {bill_row['grand_total']:,.2f}*\n"
        f"Amount Paid: Rs. {bill_row['amount_paid']:,.2f} ({bill_row['payment_mode']})\n"
    )
    if bill_row['due_amount'] > 0:
        msg += f"⚠️ *Balance Due: Rs. {bill_row['due_amount']:,.2f}*\n"
    else:
        msg += "✅ *Status: Paid in Full*\n"
    
    if upi_id:
        msg += f"\n📲 Pay via UPI: `{upi_id}`\n"
    
    msg += f"\nContact: {store_phone}\nThank you for choosing {store_name}!"

    # Clean phone number (add 91 if 10 digits without code)
    raw_phone = (bill_row['customer_phone'] or "").strip().replace(" ", "").replace("-", "")
    if len(raw_phone) == 10:
        phone_param = "91" + raw_phone
    elif len(raw_phone) > 10:
        phone_param = raw_phone.lstrip("+")
    else:
        phone_param = ""

    encoded_text = urllib.parse.quote(msg)
    wa_url = f"https://wa.me/{phone_param}?text={encoded_text}" if phone_param else f"https://wa.me/?text={encoded_text}"

    return {
        "whatsapp_url": wa_url,
        "message_text": msg,
        "customer_phone": bill_row['customer_phone']
    }

# --- Expenses Endpoints ---

@app.get("/api/expenses")
def list_expenses(limit: int = 100):
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM expenses ORDER BY date DESC, id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/expenses")
def create_expense(exp: ExpenseCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO expenses (date, category, description, amount, payment_mode, vendor_name)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (exp.date, exp.category, exp.description, exp.amount, exp.payment_mode, exp.vendor_name))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"id": new_id, "status": "success"}

@app.delete("/api/expenses/{expense_id}")
def delete_expense(expense_id: int):
    conn = get_db_connection()
    conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}

# --- Periodic Accounting & Reports Endpoints ---

@app.get("/api/reports/summary")
def get_report_summary(
    period: str = Query("monthly", pattern="^(monthly|quarterly|yearly)$"),
    year: int = 2026,
    month: Optional[int] = 9,
    quarter: Optional[int] = 3
):
    conn = get_db_connection()

    # Determine date filtering conditions
    if period == "monthly":
        date_prefix = f"{year}-{month:02d}"
        bill_condition = "strftime('%Y-%m', date) = ?"
        exp_condition = "strftime('%Y-%m', date) = ?"
        params = (date_prefix,)
        period_title = f"{datetime(year, month or 1, 1).strftime('%B %Y')}"
    elif period == "quarterly":
        # Indian Financial or standard calendar quarter
        # Q1: 01-03, Q2: 04-06, Q3: 07-09, Q4: 10-12
        q_map = {
            1: ("01", "03", "Q1 (Jan - Mar)"),
            2: ("04", "06", "Q2 (Apr - Jun)"),
            3: ("07", "09", "Q3 (Jul - Sep)"),
            4: ("10", "12", "Q4 (Oct - Dec)")
        }
        start_m, end_m, q_name = q_map.get(quarter or 1, ("01", "03", "Q1"))
        start_date = f"{year}-{start_m}-01"
        end_date = f"{year}-{end_m}-31"
        bill_condition = "date >= ? AND date <= ?"
        exp_condition = "date >= ? AND date <= ?"
        params = (start_date, end_date)
        period_title = f"{q_name} {year}"
    else: # yearly
        date_prefix = f"{year}"
        bill_condition = "strftime('%Y', date) = ?"
        exp_condition = "strftime('%Y', date) = ?"
        params = (date_prefix,)
        period_title = f"Year {year}"

    # 1. Total Sales & Bags
    sales_query = f"""
    SELECT 
        COUNT(*) as total_bills,
        COALESCE(SUM(grand_total), 0) as total_sales,
        COALESCE(SUM(amount_paid), 0) as total_collected,
        COALESCE(SUM(due_amount), 0) as total_unpaid_due,
        COALESCE(SUM(total_bags), 0) as total_bags_sold,
        COALESCE(SUM(total_tonnes), 0) as total_tonnes_sold,
        COALESCE(SUM(transport_charges), 0) as total_transport_collected,
        COALESCE(SUM(hamali_charges), 0) as total_hamali_collected
    FROM bills
    WHERE {bill_condition}
    """
    sales_summary = dict(conn.execute(sales_query, params).fetchone())

    # 2. Total Expenses & Category Breakdown
    exp_query = f"""
    SELECT 
        category,
        COALESCE(SUM(amount), 0) as category_total
    FROM expenses
    WHERE {exp_condition}
    GROUP BY category
    ORDER BY category_total DESC
    """
    exp_categories = [dict(r) for r in conn.execute(exp_query, params).fetchall()]
    total_expenses = sum(c["category_total"] for c in exp_categories)

    # 3. Cost of Goods Sold (estimated from product purchase price * quantity)
    cogs_query = f"""
    SELECT 
        COALESCE(SUM(bi.quantity_bags * p.purchase_price), 0) as total_cogs
    FROM bill_items bi
    JOIN bills b ON bi.bill_id = b.id
    JOIN products p ON bi.product_id = p.id
    WHERE {b_cond_prefix(bill_condition, 'b.date')}
    """
    cogs_row = conn.execute(cogs_query, params).fetchone()
    total_cogs = cogs_row["total_cogs"] if cogs_row else 0.0

    # 4. Net Profit calculation: Total Sales - Operating Expenses (or Gross Margin = Sales - COGS - Expenses)
    gross_profit = sales_summary["total_sales"] - total_cogs
    net_profit = gross_profit - total_expenses

    # 5. Daily or Monthly Trend for Charting
    if period == "monthly":
        trend_query = f"""
        SELECT 
            strftime('%Y-%m-%d', date) as day,
            SUM(grand_total) as daily_sales,
            SUM(total_bags) as daily_bags
        FROM bills
        WHERE {bill_condition}
        GROUP BY day
        ORDER BY day ASC
        """
    else:
        trend_query = f"""
        SELECT 
            strftime('%Y-%m', date) as month_label,
            SUM(grand_total) as monthly_sales,
            SUM(total_bags) as monthly_bags
        FROM bills
        WHERE {bill_condition}
        GROUP BY month_label
        ORDER BY month_label ASC
        """
    sales_trend = [dict(r) for r in conn.execute(trend_query, params).fetchall()]

    # 6. Overall Outstanding Receivables across all time
    all_due_row = conn.execute("SELECT COALESCE(SUM(pending_balance), 0) as all_time_due FROM customers").fetchone()
    all_time_due = all_due_row["all_time_due"] if all_due_row else 0.0

    conn.close()

    return {
        "period": period,
        "period_title": period_title,
        "sales": sales_summary,
        "total_expenses": total_expenses,
        "expense_categories": exp_categories,
        "total_cogs": total_cogs,
        "gross_profit": gross_profit,
        "net_profit": net_profit,
        "sales_trend": sales_trend,
        "all_time_pending_due": all_time_due
    }

def b_cond_prefix(cond: str, col_name: str) -> str:
    return cond.replace("date", col_name)

# --- Customers / Udhar Ledger Endpoints ---

@app.get("/api/customers")
def list_customers():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM customers ORDER BY pending_balance DESC, name ASC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/customers/{customer_id}/payments")
def record_customer_payment(customer_id: int, payment: CustomerPaymentCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    pay_date = datetime.now().strftime("%Y-%m-%d %H:%M")

    cursor.execute("""
    INSERT INTO customer_payments (customer_id, date, amount, payment_mode, notes)
    VALUES (?, ?, ?, ?, ?)
    """, (customer_id, pay_date, payment.amount, payment.payment_mode, payment.notes))

    cursor.execute("""
    UPDATE customers
    SET pending_balance = MAX(0.0, pending_balance - ?)
    WHERE id = ?
    """, (payment.amount, customer_id))

    conn.commit()
    conn.close()
# --- Database Backup & Restore Endpoints ---

from app.database import DB_PATH
from fastapi import UploadFile, File
import shutil

@app.get("/api/backup/download")
def download_backup():
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=404, detail="Database file not found")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"cement_store_backup_{timestamp}.db"
    return FileResponse(
        DB_PATH,
        media_type="application/x-sqlite3",
        filename=filename,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.post("/api/backup/restore")
async def restore_backup(file: UploadFile = File(...)):
    if not file.filename.endswith(".db"):
        raise HTTPException(status_code=400, detail="Only .db files are supported for database restore")
    
    # Create a temporary backup of current db first
    temp_bk = DB_PATH + ".bak"
    if os.path.exists(DB_PATH):
        shutil.copy2(DB_PATH, temp_bk)
    
    try:
        with open(DB_PATH, "wb") as f:
            content = await file.read()
            f.write(content)
        # Verify db is valid sqlite
        conn = get_db_connection()
        conn.execute("SELECT COUNT(*) FROM bills").fetchone()
        conn.close()
        if os.path.exists(temp_bk):
            os.remove(temp_bk)
        return {"status": "success", "message": "Database restored successfully"}
    except Exception as e:
        # Rollback
        if os.path.exists(temp_bk):
            shutil.copy2(temp_bk, DB_PATH)
            os.remove(temp_bk)
        raise HTTPException(status_code=500, detail=f"Failed to restore database: {str(e)}")

# --- Static Frontend Serving ---

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def serve_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h1>Cement Store App API is running. UI index.html not yet built.</h1>")
