import os
import sys
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse
from pydantic import BaseModel

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Correct project root to access branding/ folder inside PT-Reg/
BRANDING_DIR = os.path.join(os.path.dirname(BASE_DIR), "branding")
os.makedirs(BRANDING_DIR, exist_ok=True)

APP_DIR = os.path.join(os.path.dirname(BASE_DIR), "app")
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

import db as dbm

app = FastAPI(title="Hospital ERP API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

WEBUI_DIR = os.path.join(os.path.dirname(BASE_DIR), "webui")
if os.path.isdir(WEBUI_DIR):
    app.mount("/ui", StaticFiles(directory=WEBUI_DIR, html=True), name="ui")

INVOICE_DIR = os.path.join(BASE_DIR, "invoices")
os.makedirs(INVOICE_DIR, exist_ok=True)
app.mount("/files", StaticFiles(directory=INVOICE_DIR, html=False), name="files")

# Mount branding folder correctly
app.mount("/branding", StaticFiles(directory=BRANDING_DIR, html=False), name="branding")


@app.get("/")
def root():
    if os.path.isdir(WEBUI_DIR):
        return RedirectResponse(url="/ui/")
    return {"ok": True, "message": "Hospital ERP API", "docs": "/docs", "health": "/health"}


class LoginPayload(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    username: str
    rights: List[str]


class PatientIn(BaseModel):
    title: Optional[str] = ""
    first_name: Optional[str] = ""
    middle_name: Optional[str] = ""
    last_name: Optional[str] = ""
    name: Optional[str] = ""
    guardian: Optional[str] = ""
    gender: Optional[str] = ""
    dob: Optional[str] = ""
    age_value: Optional[str] = ""
    age_unit: Optional[str] = ""
    cnic: Optional[str] = ""
    contact_number: Optional[str] = ""
    address: Optional[str] = ""
    blood_group: Optional[str] = ""
    referring_doctor: Optional[str] = ""
    patient_type: Optional[str] = ""
    company_name: Optional[str] = ""


class PatientResponse(PatientIn):
    reg_no: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginPayload):
    try:
        dbm.ensure_admin_user()
    except Exception:
        pass
    u = payload.username.strip()
    p = payload.password.strip()
    expected_user = os.getenv("APP_USERNAME", "admin")
    expected_pass = os.getenv("APP_PASSWORD", "admin")
    rights: List[str] = []
    if u == expected_user and p == expected_pass:
        rights = dbm.get_rights_for_user(u)
    else:
        user = dbm.get_user(u)
        if not user or str(user.get("password", "")) != p:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        rights = user.get("rights") or []
    if not rights:
        raise HTTPException(status_code=403, detail="No rights assigned")
    return {"username": u, "rights": rights}


@app.get("/patients", response_model=List[PatientResponse])
def search_patients(reg_no: Optional[str] = None, mobile: Optional[str] = None):
    return dbm.search_patients(reg_no=reg_no, mobile=mobile)


@app.get("/patients/{reg_no}", response_model=PatientResponse)
def get_patient(reg_no: str):
    res = dbm.get_patient_by_reg_no(reg_no)
    if not res:
        raise HTTPException(status_code=404, detail="Patient not found")
    return res


@app.post("/patients", response_model=PatientResponse)
def register_patient(payload: PatientIn):
    res = dbm.save_patient(payload.model_dump())
    if not res:
        raise HTTPException(status_code=500, detail="Failed to save")
    return res


@app.put("/patients/{reg_no}", response_model=PatientResponse)
def update_patient(reg_no: str, payload: PatientIn):
    res = dbm.update_patient_by_reg_no(reg_no, payload.model_dump())
    if not res:
        raise HTTPException(status_code=404, detail="Patient not found")
    return res


@app.get("/registration/preview")
def preview_registration():
    reg_no = dbm.get_next_reg_no()
    return {"reg_no": reg_no}


@app.get("/lookups/referring-doctors")
def get_referring_doctors():
    return dbm.get_lookups("referring_doctors")


@app.get("/lookups/doctors-with-fee")
def get_doctors_with_fee():
    return dbm.list_doctors_with_fee()

class DoctorIn(BaseModel):
    name: str
    fee: float
    specialty: str

@app.post("/doctors")
def create_doctor(payload: DoctorIn):
    dbm.add_doctor(payload.name, payload.fee, payload.specialty)
    return {"ok": True}

@app.put("/doctors/{doctor_id}")
def update_doctor(doctor_id: str, payload: DoctorIn):
    dbm.update_doctor(doctor_id, payload.name, payload.fee, payload.specialty)
    return {"ok": True}

@app.delete("/doctors/{doctor_id}")
def delete_doctor(doctor_id: str):
    dbm.delete_doctor(doctor_id)
    return {"ok": True}


@app.get("/lookups/lab-tests")
def get_lab_tests():
    return dbm.get_lookups("lab_tests")


@app.get("/lookups/radiology")
def get_radiology():
    return dbm.get_lookups("radiology_services")


@app.get("/lookups/misc")
def get_misc():
    return dbm.get_lookups("misc_services")


@app.get("/price")
def get_price(collection: str, name: str):
    p = dbm.get_price(collection, name)
    return {"price": p}


class InvoiceIn(BaseModel):
    reg_no: str
    patient_name: str
    category: str
    item_name: str
    doctor_name: Optional[str] = ""
    charges: float
    discount: float = 0.0
    payment_mode: str = "Cash"
    cardholder_name: Optional[str] = ""
    card_last4: Optional[str] = ""
    card_expiry: Optional[str] = ""
    remarks: Optional[str] = ""
    created_by: Optional[str] = "admin"
    terminal_name: Optional[str] = "Web"


def _generate_invoice_pdf(doc: dict, fpath: str):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors
    import datetime as _dt
    
    c = canvas.Canvas(fpath, pagesize=A4)
    w, h = A4
    
    # --- Header Section ---
    # Logo (if exists)
    logo_path = os.path.join(BRANDING_DIR, "logo.png")
    if os.path.exists(logo_path):
        try:
            c.drawImage(logo_path, 50, h - 80, width=120, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass

    # AMI Medical Center Title
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(w/2, h - 50, "AMI Medical Center")
    
    c.setFont("Helvetica", 9)
    c.drawCentredString(w/2, h - 65, "Address: A-1 block-0 FB Area Karachi")
    c.drawCentredString(w/2, h - 77, "Email: youremail@domain.com | Contact: 0300-0000000")
    
    c.setLineWidth(1)
    c.line(50, h - 85, w - 50, h - 85)
    
    # "INVOICE" title
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(w/2, h - 105, "INVOICE")
    
    # --- Details Section ---
    c.setFont("Helvetica-Bold", 10)
    y = h - 130
    
    # Row 1
    c.drawString(50, y, "Date/Time:")
    c.setFont("Helvetica", 10)
    c.drawString(110, y, _dt.datetime.now().strftime('%d-%m-%Y %H:%M:%S'))
    
    c.setFont("Helvetica-Bold", 10)
    c.drawString(w - 180, y, "Token No:")
    c.setFont("Helvetica", 10)
    c.drawString(w - 120, y, str(doc.get("token_number", "")))
    
    y -= 18
    # Row 2
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Invoice No:")
    c.setFont("Helvetica", 10)
    c.drawString(110, y, str(doc.get("invoice_no", "")))
    
    c.setFont("Helvetica-Bold", 10)
    c.drawString(w - 180, y, "Invoice Date:")
    c.setFont("Helvetica", 10)
    c.drawString(w - 120, y, _dt.datetime.now().strftime('%d-%m-%Y'))
    
    y -= 18
    # Row 3
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Patient Name:")
    c.setFont("Helvetica", 10)
    c.drawString(125, y, str(doc.get("patient_name", "")))
    
    c.setFont("Helvetica-Bold", 10)
    c.drawString(w - 180, y, "Patient Reg No:")
    c.setFont("Helvetica", 10)
    c.drawString(w - 100, y, str(doc.get("reg_no", "")))
    
    y -= 18
    # Row 4
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Age:")
    c.setFont("Helvetica", 10)
    age_str = f"{doc.get('age_value','')} {doc.get('age_unit','')}".strip()
    c.drawString(85, y, age_str)
    
    c.setFont("Helvetica-Bold", 10)
    c.drawString(w - 180, y, "Contact No:")
    c.setFont("Helvetica", 10)
    c.drawString(w - 120, y, str(doc.get("contact_number", "")))
    
    y -= 18
    # Row 5
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Address:")
    c.setFont("Helvetica", 10)
    c.drawString(100, y, str(doc.get("address", "")))
    
    y -= 25
    
    # --- Table Section ---
    # Header
    c.setFillColor(colors.lightgrey)
    c.rect(50, y - 5, w - 100, 20, fill=1)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(60, y, "S.No")
    c.drawString(100, y, "Service")
    c.drawRightString(w - 150, y, "Qty")
    c.drawRightString(w - 60, y, "Amount")
    
    y -= 25
    # Data Row
    c.setFont("Helvetica", 10)
    c.drawString(60, y, "1")
    service_text = str(doc.get("item_name", ""))
    if doc.get("doctor_name"):
        service_text += f" ({doc.get('doctor_name')})"
    c.drawString(100, y, service_text)
    c.drawRightString(w - 150, y, "1")
    c.drawRightString(w - 60, y, f"{float(doc.get('charges', 0)):.2f}")
    
    # --- Totals Section ---
    y -= 40
    c.setLineWidth(0.5)
    c.line(w - 200, y + 35, w - 50, y + 35) # separator
    
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(w - 120, y, "Total:")
    c.setFont("Helvetica", 10)
    c.drawRightString(w - 60, y, f"{float(doc.get('charges', 0)):.2f}")
    
    y -= 15
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(w - 120, y, "Discount:")
    c.setFont("Helvetica", 10)
    c.drawRightString(w - 60, y, f"{float(doc.get('discount', 0)):.2f}")
    
    y -= 20
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(w - 120, y, "Net Total:")
    c.drawRightString(w - 60, y, f"{float(doc.get('net_total', 0)):.2f}")
    
    # --- Footer Section ---
    y -= 40
    c.setFont("Helvetica-Bold", 9)
    c.drawString(50, y, "Payment Mode:")
    c.setFont("Helvetica", 9)
    c.drawString(125, y, str(doc.get("payment_mode", "")))
    
    c.setFont("Helvetica-Bold", 9)
    c.drawString(200, y, "User Name:")
    c.setFont("Helvetica", 9)
    c.drawString(260, y, str(doc.get("created_by", "")))
    
    c.setFont("Helvetica-Bold", 9)
    c.drawString(350, y, "Terminal:")
    c.setFont("Helvetica", 9)
    c.drawString(400, y, str(doc.get("terminal_name", "")))
    
    # Disclaimer
    y -= 40
    c.setFont("Helvetica-Oblique", 8)
    c.drawCentredString(w/2, y, "Developed by AMI Technologies – “Technology That Powers Your Business.”")
    
    c.showPage()
    c.save()


@app.post("/invoices")
def create_invoice(payload: InvoiceIn):
    # Detect environment for terminal name
    import socket
    is_render = os.getenv("RENDER") == "true"
    if payload.terminal_name == "Web":
        if is_render:
            payload.terminal_name = "Cloud"
        else:
            try:
                payload.terminal_name = socket.gethostname()
            except Exception:
                payload.terminal_name = "LocalPC"
    
    # auto invoice number
    inv_no = None
    try:
        client = dbm.get_client()
        db = client.get_database(os.getenv("MONGODB_DB", "hospital_db"))
        counters = db.get_collection("counters")
        key = "invoice_global"
        doc = counters.find_one_and_update(
            {"_id": key},
            {"$inc": {"seq": 1}},
            upsert=True,
            return_document=__import__("pymongo").ReturnDocument.AFTER,  # type: ignore
        )
        seq = int((doc or {}).get("seq", 1))
        inv_no = f"INV-{seq:06d}"
    except Exception:
        inv_no = None
    try:
        c = float(payload.charges or 0)
    except Exception:
        c = 0.0
    try:
        d = float(payload.discount or 0)
    except Exception:
        d = 0.0
    net = c - d
    if net < 0:
        net = 0.0
    
    # Token logic for Consultancy
    token_number = None
    if payload.category == "Consultancy" and payload.item_name == "Consultancy Fee" and payload.doctor_name:
        token_number = dbm.get_next_token(payload.doctor_name)

    import datetime as _dt
    now = _dt.datetime.now().isoformat()
    import uuid
    fname = f"invoice-{payload.reg_no or 'reg'}-{uuid.uuid4().hex[:8]}.pdf"
    fpath = os.path.join(INVOICE_DIR, fname)
    pdf_url = f"/files/{fname}"

    doc = payload.model_dump()
    doc["token_number"] = token_number
    
    # Fetch additional patient info for PDF
    patient = dbm.get_patient_by_reg_no(payload.reg_no)
    if patient:
        doc["age_value"] = patient.get("age_value", "")
        doc["age_unit"] = patient.get("age_unit", "")
        doc["contact_number"] = patient.get("contact_number", "")
        doc["address"] = patient.get("address", "")

    doc["net_total"] = net
    doc["invoice_no"] = inv_no
    doc["created_at"] = now
    doc["pdf"] = pdf_url
    
    # Generate PDF
    try:
        _generate_invoice_pdf(doc, fpath)
    except Exception as ex:
        print(f"PDF Error: {ex}")
        pdf_url = None
        doc["pdf"] = None

    res = dbm.save_invoice(doc)
    if not res:
        raise HTTPException(status_code=500, detail="Failed to save invoice")
    
    return {
        "ok": True,
        "invoice_id": str(res),
        "invoice_no": inv_no,
        "token_number": token_number,
        "net_total": net,
        "pdf": pdf_url
    }


@app.get("/invoices")
def list_invoices(reg_no: Optional[str] = None, invoice_no: Optional[str] = None):
    return dbm.list_invoices(reg_no=reg_no, invoice_no=invoice_no)


@app.get("/reports/mis")
def get_mis_reports(start_date: Optional[str] = None, end_date: Optional[str] = None):
    return dbm.get_mis_reports(start_date=start_date, end_date=end_date)


@app.get("/invoices/preview")
def preview_invoice():
    try:
        client = dbm.get_client()
        db = client.get_database(os.getenv("MONGODB_DB", "hospital_db"))
        counters = db.get_collection("counters")
        doc = counters.find_one({"_id": "invoice_global"})
        seq = int((doc or {}).get("seq", 0)) + 1
        return {"invoice_no": f"INV-{seq:06d}"}
    except Exception:
        return {"invoice_no": ""}


class RefundIn(BaseModel):
    invoice_id: str
    reason: str


@app.post("/invoices/refund")
def refund_invoice(payload: RefundIn):
    res = dbm.refund_invoice(payload.invoice_id, payload.reason)
    if not res:
        raise HTTPException(status_code=400, detail="Refund failed or already refunded")
    return {"ok": True}


class ShiftStartIn(BaseModel):
    username: str


@app.post("/shifts/start")
def start_shift(payload: ShiftStartIn):
    client = dbm.get_client()
    db = client.get_database(os.getenv("MONGODB_DB", "hospital_db"))
    col = db.get_collection("shifts")
    # Check if already active
    active = col.find_one({"username": payload.username, "end_time": None})
    if active:
        return {"ok": True, "message": "Shift already active"}
    import datetime as _dt
    now = _dt.datetime.now().isoformat()
    col.insert_one({
        "username": payload.username,
        "start_time": now,
        "end_time": None
    })
    return {"ok": True}


@app.post("/shifts/end")
def end_shift(payload: ShiftStartIn):
    client = dbm.get_client()
    db = client.get_database(os.getenv("MONGODB_DB", "hospital_db"))
    col = db.get_collection("shifts")
    active = col.find_one({"username": payload.username, "end_time": None})
    if not active:
        raise HTTPException(status_code=400, detail="No active shift found")
    
    import datetime as _dt
    now = _dt.datetime.now().isoformat()
    
    # Calculate Summary
    inv_col = db.get_collection("invoices")
    query = {
        "created_by": payload.username,
        "created_at": {"$gte": active["start_time"], "$lte": now}
    }
    invoices = list(inv_col.find(query))
    
    summary = {
        "total_services": 0,
        "cash_received": 0.0,
        "card_received": 0.0,
        "total_refunded": 0.0,
        "refund_count": 0,
        "total_discount": 0.0,
        "net_collection": 0.0,
        "invoices": [],
        "refunds": []
    }
    
    for inv in invoices:
        is_refund = bool(inv.get("refunded", False))
        net = float(inv.get("net_total", 0) or 0)
        mode = inv.get("payment_mode", "Cash")
        disc = float(inv.get("discount", 0) or 0)
        
        if is_refund:
            summary["total_refunded"] += net
            summary["refund_count"] += 1
            summary["refunds"].append({
                "reg_no": inv.get("reg_no"),
                "patient_name": inv.get("patient_name"),
                "amount": net,
                "reason": inv.get("refund_reason", "N/A")
            })
        else:
            summary["total_services"] += 1
            summary["total_discount"] += disc
            if mode == "Cash":
                summary["cash_received"] += net
            else:
                summary["card_received"] += net
            summary["invoices"].append({
                "reg_no": inv.get("reg_no"),
                "patient_name": inv.get("patient_name"),
                "service": inv.get("item_name"),
                "amount": net,
                "discount": disc
            })
    
    summary["net_collection"] = summary["cash_received"] + summary["card_received"] - summary["total_refunded"]
    
    col.update_one({"_id": active["_id"]}, {"$set": {"end_time": now, "summary": summary}})
    return {"ok": True, "summary": summary}


@app.get("/shifts/current")
def get_current_shift(username: str):
    client = dbm.get_client()
    db = client.get_database(os.getenv("MONGODB_DB", "hospital_db"))
    col = db.get_collection("shifts")
    active = col.find_one({"username": username, "end_time": None})
    if not active:
        return {"active": False}
    
    # Calculate real-time summary
    import datetime as _dt
    now = _dt.datetime.now().isoformat()
    inv_col = db.get_collection("invoices")
    query = {
        "created_by": username,
        "created_at": {"$gte": active["start_time"], "$lte": now}
    }
    invoices = list(inv_col.find(query))
    
    summary = {
        "total_services": 0,
        "cash_received": 0.0,
        "card_received": 0.0,
        "total_refunded": 0.0,
        "refund_count": 0,
        "total_discount": 0.0,
        "net_collection": 0.0,
        "invoices": [],
        "refunds": []
    }
    for inv in invoices:
        is_refund = bool(inv.get("refunded", False))
        net = float(inv.get("net_total", 0) or 0)
        mode = inv.get("payment_mode", "Cash")
        disc = float(inv.get("discount", 0) or 0)
        
        if is_refund:
            summary["total_refunded"] += net
            summary["refund_count"] += 1
            summary["refunds"].append({
                "reg_no": inv.get("reg_no"),
                "patient_name": inv.get("patient_name"),
                "amount": net,
                "reason": inv.get("refund_reason", "N/A")
            })
        else:
            summary["total_services"] += 1
            summary["total_discount"] += disc
            if mode == "Cash":
                summary["cash_received"] += net
            else:
                summary["card_received"] += net
            summary["invoices"].append({
                "reg_no": inv.get("reg_no"),
                "patient_name": inv.get("patient_name"),
                "service": inv.get("item_name"),
                "amount": net,
                "discount": disc
            })
    summary["net_collection"] = summary["cash_received"] + summary["card_received"] - summary["total_refunded"]

    return {
        "active": True,
        "start_time": active["start_time"],
        "summary": summary
    }


@app.get("/users")
def list_users():
    return dbm.list_users()

@app.get("/users/{username}")
def get_user(username: str):
    u = dbm.get_user(username)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return u

class UserIn(BaseModel):
    username: str
    password: str
    rights: List[str]

@app.post("/users")
def save_user(payload: UserIn):
    dbm.add_or_update_user(payload.username, payload.password, payload.rights)
    return {"ok": True}

@app.delete("/users/{username}")
def delete_user(username: str):
    dbm.delete_user(username)
    return {"ok": True}

@app.get("/modules/list")
def list_modules():
    return dbm.list_modules()

class ModuleIn(BaseModel):
    key: str
    label: str

@app.post("/modules/list")
def add_module(payload: ModuleIn):
    dbm.add_module(payload.key, payload.label)
    return {"ok": True}

@app.get("/modules")
def get_modules():
    return [
        {"key": "appointment", "icon": "📅", "label": "Appointment", "href": "#"},
        {"key": "patient_registration", "icon": "📝", "label": "Patient Registration", "href": "patient.html"},
        {"key": "search", "icon": "🔍", "label": "Search Patients", "href": "search.html"},
        {"key": "clinical", "icon": "🧑‍⚕️", "label": "Clinical Management", "href": "#"},
        {"key": "daycare", "icon": "🛏️", "label": "Day Care", "href": "#"},
        {"key": "invoice", "icon": "🧾", "label": "Invoice / Service", "href": "invoice.html"},
        {"key": "ot", "icon": "🩺", "label": "Operation Theatre", "href": "#"},
        {"key": "insurance", "icon": "🛡️", "label": "Insurance and eClaim", "href": "#"},
        {"key": "phlebotomy", "icon": "💉", "label": "Phlebotomy", "href": "#"},
        {"key": "lab", "icon": "🧪", "label": "Laboratory", "href": "#"},
        {"key": "bloodbank", "icon": "🩸", "label": "Blood Bank", "href": "#"},
        {"key": "radiology", "icon": "🩻", "label": "Radiology", "href": "#"},
        {"key": "inventory", "icon": "📦", "label": "Inventory", "href": "#"},
        {"key": "reports", "icon": "📊", "label": "MIS Reports", "href": "reports.html"},
        {"key": "nurse", "icon": "👩‍⚕️", "label": "Nurse Station", "href": "#"},
        {"key": "inventory_setup", "icon": "🛠️", "label": "Inventory Setup", "href": "#"},
        {"key": "discharge", "icon": "📄", "label": "Discharge Summary", "href": "#"},
        {"key": "custom", "icon": "✅", "label": "Custom Template", "href": "#"},
        {"key": "software", "icon": "⚙️", "label": "Software Management", "href": "admin.html"},
    ]

