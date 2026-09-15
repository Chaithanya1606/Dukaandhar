# 🚀 Free Cloud Deployment Guide for Your Cement Store App

This guide explains how to host your app on **Render.com** (100% free) connected to **GitHub**, so your uncle can access the app from his mobile phone 24/7, and you can maintain it from your system.

---

## Step 1: Create a Free GitHub Repository

1. Go to **[https://github.com](https://github.com)** and log in (or create a free account).
2. Click the **`+`** icon at the top right -> **"New repository"**.
3. Repository name: `cement-store-app` (you can choose **Private** so only you can see it).
4. Do **not** check "Add a README" or ".gitignore" (we already created them).
5. Click **"Create repository"**.

---

## Step 2: Push Your Code to GitHub (One-Time Setup)

In your terminal or PowerShell, run:

```powershell
cd C:\Users\Chaithanya\.gemini\antigravity\scratch\cement-store-app

# Link to your new GitHub repository (replace with your GitHub username):
git remote add origin https://github.com/Chaithanya1606/Dukaandhar.git

# Push the code to GitHub:
git push -u origin main
```

*(If prompted, log in with your GitHub account credentials or Personal Access Token)*.

---

## Step 3: Deploy on Render.com (100% Free 24/7 Hosting)

1. Go to **[https://render.com](https://render.com)** and sign up / log in with your **GitHub account**.
2. On your Render dashboard, click **"New +"** -> select **"Web Service"**.
3. Choose **"Build and deploy from a Git repository"** and connect your GitHub account.
4. Select your **`cement-store-app`** repository.
5. In the settings form:
   - **Name**: `cement-store-app` (or any name you like)
   - **Region**: Singapore or Frankfurt (choose nearest to India)
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `python backend/run_server.py`
   - **Instance Type**: Select **"Free"** ($0/month)
6. Click **"Create Web Service"**.

Render will now build your app and in ~2 minutes give you a permanent, secure HTTPS link like:
👉 **`https://cement-store-app.onrender.com`**

---

## Step 4: Setup on Your Uncle's Mobile Phone

1. Send the link (`https://cement-store-app.onrender.com`) to your uncle on **WhatsApp**.
2. Have him open the link in **Chrome** (Android) or **Safari** (iPhone).
3. In Chrome, tap the **three dots menu (⋮)** at the top right -> tap **"Add to Home Screen"** (or "Install app").
4. An icon will appear on his phone screen named **"Cement Store"**.
5. He can now open it just like any native mobile app to create bills, share on WhatsApp, and print!

---

## How You Maintain the App in the Future

Whenever you make any changes, fixes, or improvements to the code on your computer:

```powershell
cd C:\Users\Chaithanya\.gemini\antigravity\scratch\cement-store-app

git add .
git commit -m "Added new feature or updated prices"
git push
```

**That's it!** Render will automatically detect the push, rebuild, and update the live app on your uncle's phone within 2 minutes — with zero downtime and zero manual server work.

---

## 💾 Daily Store Data Safety

Because free cloud web tiers may spin down after long inactivity:
- Inside **Store Settings (⚙️)**, your uncle or you can click **"Download Database Backup"** anytime to save a `.db` file to Google Drive or phone storage with 1 click.
- If needed, you can restore all past bills and accounts with the **"Restore from Backup"** button.
