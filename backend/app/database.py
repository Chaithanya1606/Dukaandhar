import sqlite3
import os
import hashlib
import secrets
from datetime import datetime

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cement_store.db")
DB_PATH = os.getenv("DATABASE_PATH", DEFAULT_DB_PATH)

db_directory = os.path.dirname(DB_PATH)
if db_directory:
    os.makedirs(db_directory, exist_ok=True)

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), 200_000
    )
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, expected_digest = stored_hash.split("$", 1)
    except ValueError:
        return False
    actual_digest = hash_password(password, salt).split("$", 1)[1]
    return secrets.compare_digest(actual_digest, expected_digest)

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL COLLATE NOCASE,
        password_hash TEXT NOT NULL,
        is_admin INTEGER NOT NULL DEFAULT 0,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        token_hash TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        expires_at TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    # 1. Store Profile Settings
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS store_profile (
        id INTEGER PRIMARY KEY,
        store_name TEXT NOT NULL,
        owner_name TEXT,
        phone TEXT NOT NULL,
        alt_phone TEXT,
        address TEXT NOT NULL,
        gstin TEXT,
        upi_id TEXT,
        state_code TEXT DEFAULT '36',
        bill_footer_note TEXT DEFAULT 'Thank you for your business! Goods once sold will not be taken back.'
    )
    """)

    # 2. Cement Products Catalog
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        brand TEXT NOT NULL,
        grade TEXT NOT NULL,
        hsn_code TEXT DEFAULT '2523',
        bag_weight_kg REAL DEFAULT 50.0,
        purchase_price REAL NOT NULL,
        selling_price REAL NOT NULL,
        stock_bags INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1
    )
    """)

    # 3. Customers / Contractors Khata
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT,
        site_address TEXT,
        pending_balance REAL DEFAULT 0.0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 4. Invoices / Bills
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bill_number TEXT UNIQUE NOT NULL,
        date TEXT NOT NULL,
        customer_id INTEGER,
        customer_name TEXT NOT NULL,
        customer_phone TEXT,
        delivery_site TEXT,
        vehicle_no TEXT,
        subtotal REAL NOT NULL,
        discount REAL DEFAULT 0.0,
        transport_charges REAL DEFAULT 0.0,
        hamali_charges REAL DEFAULT 0.0,
        gst_rate REAL DEFAULT 0.0,
        gst_amount REAL DEFAULT 0.0,
        grand_total REAL NOT NULL,
        payment_mode TEXT NOT NULL,
        amount_paid REAL NOT NULL,
        due_amount REAL DEFAULT 0.0,
        total_bags INTEGER NOT NULL,
        total_tonnes REAL NOT NULL,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (customer_id) REFERENCES customers(id)
    )
    """)

    # 5. Bill Items
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bill_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bill_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        brand TEXT NOT NULL,
        grade TEXT NOT NULL,
        hsn_code TEXT DEFAULT '2523',
        quantity_bags INTEGER NOT NULL,
        weight_tonnes REAL NOT NULL,
        unit_price REAL NOT NULL,
        total_price REAL NOT NULL,
        FOREIGN KEY (bill_id) REFERENCES bills(id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES products(id)
    )
    """)

    # 6. Expenses Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        category TEXT NOT NULL,
        description TEXT NOT NULL,
        amount REAL NOT NULL,
        payment_mode TEXT DEFAULT 'Cash',
        vendor_name TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 7. Customer Payments (Ledger repayments)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customer_payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        bill_id INTEGER,
        date TEXT NOT NULL,
        amount REAL NOT NULL,
        payment_mode TEXT DEFAULT 'Cash',
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (customer_id) REFERENCES customers(id)
    )
    """)

    # Seed Default Store Profile if empty
    cursor.execute("SELECT COUNT(*) FROM store_profile")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO store_profile (id, store_name, owner_name, phone, alt_phone, address, gstin, upi_id, bill_footer_note)
        VALUES (1, 'Sri Lakshmi Cement Resale & Suppliers', 'K. Venkat Rao', '9876543210', '9848012345', 'Shop No. 4, Main Road, Industrial Estate, Hyderabad', '36AAAAA0000A1Z5', 'srilakshmi.cement@upi', 'Goods loaded in good condition. Unloading charges as per agreement.')
        """)

    # Seed Default Cement Products if empty
    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] == 0:
        default_products = [
            ("UltraTech Cement", "PPC (Weather Plus)", "2523", 50.0, 340.0, 385.0, 450),
            ("UltraTech Cement", "OPC 53 Grade", "2523", 50.0, 360.0, 410.0, 300),
            ("ACC Cement", "Gold Water Shield", "2523", 50.0, 350.0, 395.0, 250),
            ("ACC Cement", "Suraksha Power (PPC)", "2523", 50.0, 335.0, 375.0, 350),
            ("Ambuja Cement", "Plus Roof Special", "2523", 50.0, 345.0, 390.0, 280),
            ("Dalmia Cement", "DSP PPC", "2523", 50.0, 340.0, 385.0, 220),
            ("Bharathi Cement", "Ultrafast PPC", "2523", 50.0, 325.0, 365.0, 400),
            ("Ramco Cement", "Supergrade PPC", "2523", 50.0, 330.0, 370.0, 180),
            ("Birla A1", "StrongCrete 53", "2523", 50.0, 345.0, 385.0, 200),
            ("Birla White", "White Cement (50kg)", "2523", 50.0, 680.0, 780.0, 60),
        ]
        cursor.executemany("""
        INSERT INTO products (brand, grade, hsn_code, bag_weight_kg, purchase_price, selling_price, stock_bags)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, default_products)

    # Keep demonstration data out of a new production database.
    if os.getenv("APP_ENV", "development").lower() != "production":
        cursor.execute("SELECT COUNT(*) FROM expenses")
        if cursor.fetchone()[0] == 0:
            sample_expenses = [
                ("2026-09-02", "Hamali / Labor", "Unloading 500 bags from lorry (₹4/bag)", 2000.0, "Cash", "Ramesh Hamali Union"),
                ("2026-09-05", "Lorry Freight", "Transport freight for 400 bags delivery to Site B", 3500.0, "UPI", "Balaji Transport"),
                ("2026-09-10", "Godown Rent", "Godown monthly rent for September", 18000.0, "Bank Transfer", "Landlord Reddy"),
                ("2026-09-12", "Electricity & Utilities", "Godown and office power bill", 2450.0, "UPI", "TSSPDCL"),
                ("2026-09-14", "Tea & Refreshments", "Labor tea and water supply", 650.0, "Cash", "Local Canteen"),
                ("2026-08-15", "Hamali / Labor", "Unloading stock from plant rake", 4200.0, "Cash", "Hamali Union"),
                ("2026-08-20", "Lorry Freight", "Cement freight charges", 5000.0, "Bank Transfer", "National Roadways"),
                ("2026-07-10", "Godown Rent", "Godown rent for July", 18000.0, "Bank Transfer", "Landlord Reddy"),
            ]
            cursor.executemany("""
            INSERT INTO expenses (date, category, description, amount, payment_mode, vendor_name)
            VALUES (?, ?, ?, ?, ?, ?)
            """, sample_expenses)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at:", DB_PATH)
