# Cement Resale Store: Billing, Invoicing & Accounts System

A mobile-friendly billing, thermal printing, WhatsApp sharing, and periodic accounting application designed specifically for **Cement Resale Stores** (in **INR ₹**).

---

## Features

1. **⚡ Fast Billing POS**:
   - Pre-configured Cement Brands: UltraTech (PPC & OPC 53), ACC Gold, ACC Suraksha, Ambuja Plus, Dalmia DSP, Bharathi Cement, Ramco Supergrade, Birla A1, Birla White.
   - Quick bag quantity entry with automatic Metric Tonnes (MT) conversion (e.g., `100 Bags = 5.00 MT`).
   - Lorry / Vehicle number & Delivery site address tracking.
   - Transport / Lorry Freight charges & Hamali (unloading) charges.
   - Multiple payment options: **Cash**, **UPI**, **Credit / Udhar (Khata)**, **Cheque**.

2. **🖨️ Thermal Printing & PDF Invoicing**:
   - **One-Click Print**: Directly prints formatted receipts for 80mm / 58mm thermal POS roll printers and standard desktop printers.
   - **Professional PDF Invoice**: Generated via Python ReportLab with store logo/name, GSTIN, HSN 2523, bag weight, totals in words, terms, and authorized signature.

3. **📱 Direct WhatsApp Bill Sharing**:
   - One-tap WhatsApp button opening `https://wa.me/{customer_phone}?text=...` with a complete itemized bill summary and payment info.

4. **💰 Daily Expenses Book**:
   - Dedicated cement store expense categories: *Hamali / Labor, Lorry Freight, Cement Stock Procurement, Godown Rent, Staff Salary, Electricity, Tea & Refreshments, Vehicle Maintenance, Misc*.

5. **📊 Monthly, Quarterly & Yearly Accounting**:
   - Interactive toggles: **Monthly**, **Quarterly (Q1 to Q4)**, and **Yearly**.
   - Net Profit & Loss Calculation: `Sales - (Cost of Goods + Operating Expenses)`.
   - Visual trend charts for sales revenue and bag volumes.
   - Category-wise expense distribution.

6. **👥 Contractor & Customer Khata (Credit Book)**:
   - Tracks outstanding credit (Udhar) per customer/contractor.
   - One-click "Receive Payment" dialog to log partial or full balance settlements.

---

## How to Run the Application

### Option 1: Double Click Launcher
Simply double-click `start_app.bat` inside `cement-store-app/`.

### Option 2: Command Line
```powershell
cd C:\Users\Chaithanya\.gemini\antigravity\scratch\cement-store-app
& "C:\Users\Chaithanya\AppData\Local\Python\bin\python.exe" backend\run_server.py
```

Open your browser to:
👉 **[http://localhost:8000](http://localhost:8000)**

### Accessing on Mobile Phone / Tablet on the Same Wi-Fi:
Find your computer's local IP address (run `ipconfig` in terminal, e.g. `192.168.1.15`), then on your mobile browser go to:
👉 `http://<your-computer-ip>:8000`
You can tap **"Add to Home Screen"** on Chrome or Safari to install it as a full-screen mobile app!

## Hosted Deployment

The included Docker Compose stack uses only open-source software: the app, SQLite, Docker, and Caddy. Caddy automatically obtains and renews a free HTTPS certificate. Use a small Linux server with persistent disk storage; a free Oracle Cloud Always Free VM is one possible host, subject to its availability and terms.

### Server setup

Install Docker and Git on an Ubuntu server, then upload or clone this project:

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin git
sudo systemctl enable --now docker
git clone YOUR_REPOSITORY_URL
cd cement-store-app
```

Point a DNS name to the server's public IP before starting Caddy. Copy the environment template and set a unique password and domain:

```bash
cp .env.example .env
nano .env
```

Set at least:

```env
APP_ENV=production
DOMAIN=billing.your-domain.example
```

Start the app:

```bash
sudo docker compose up -d --build
sudo docker compose logs -f
```

Open `https://billing.your-domain.example` on the phone. Caddy exposes only the HTTPS proxy; the FastAPI app and SQLite file remain inside the Docker network and persistent volume.

Back up the data volume regularly:

```bash
chmod +x backup_db.sh
./backup_db.sh
```

The database remains SQLite for this single-company deployment. It is not intended for multiple stores or concurrent multi-worker deployments. On a fresh database, create the first administrator directly on the login screen; after login, additional users can be created through Store Settings. Never commit `.env` or `backups/`.
