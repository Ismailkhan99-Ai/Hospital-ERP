# Hospital ERP System

A local-first Hospital ERP system for patient registration, billing, and MIS reports.

## 🛠 Features
- **Patient Registration**: Search and manage patient records.
- **Billing & Invoices**: Generate and manage service invoices.
- **MIS Reports**: Real-time revenue and patient analytics.
- **User Management**: Admin-controlled access and rights.

## 🚀 Local Setup
1. **Prerequisites**: Install Python 3.10+.
2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Database**: The system connects to a MongoDB Atlas cluster (configured in `.env`).
4. **Run Server**:
   ```bash
   uvicorn webapi.main:app --reload
   ```
5. **Access**: Open `http://localhost:8000` in your browser or use the `Open_Hospital_ERP.url` shortcut.

## 🔒 Security Note
The `.env` file contains your database credentials and should **never** be shared or committed to public repositories.
