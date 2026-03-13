import os
import re
from pymongo import MongoClient, ReturnDocument
from typing import List, Dict

def get_client():
    uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    return MongoClient(uri)

def get_db():
    client = get_client()
    return client.get_database(os.getenv("MONGODB_DB", "hospital_db"))

def get_collection(name: str):
    db = get_db()
    return db.get_collection(name)

def get_next_reg_no() -> str:
    counters = get_collection("counters")
    key = "patient_reg_global"
    doc = counters.find_one_and_update(
        {"_id": key},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    seq = int((doc or {}).get("seq", 1))
    return f"REG-{seq:06d}"

def get_next_token(doctor_name: str) -> int:
    import datetime as _dt
    today = _dt.date.today().isoformat()
    counters = get_collection("counters")
    # key like token:Dr. Smith:2026-03-12
    key = f"token:{doctor_name}:{today}"
    doc = counters.find_one_and_update(
        {"_id": key},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return int((doc or {}).get("seq", 1))

def save_patient(payload: dict):
    col = get_collection("patients")
    reg_no = get_next_reg_no()
    payload["reg_no"] = reg_no
    import datetime as _dt
    if "created_at" not in payload:
        payload["created_at"] = _dt.datetime.now().isoformat()
    col.insert_one(payload)
    return payload

def get_patient_by_reg_no(reg_no: str):
    col = get_collection("patients")
    return col.find_one({"reg_no": reg_no})

def update_patient_by_reg_no(reg_no: str, payload: dict):
    col = get_collection("patients")
    res = col.update_one({"reg_no": reg_no}, {"$set": payload})
    return res.modified_count > 0

def search_patients(reg_no: str = None, mobile: str = None) -> list:
    col = get_collection("patients")
    query = {}
    if reg_no:
        query["reg_no"] = {"$regex": f"^{re.escape(reg_no)}", "$options": "i"}
    if mobile:
        query["contact_number"] = {"$regex": f"^{re.escape(mobile)}", "$options": "i"}
    return list(col.find(query).limit(50))

def get_lookups(collection_name: str) -> list:
    col = get_collection(collection_name)
    return [doc.get("name") for doc in col.find({}, {"_id": 0, "name": 1}).sort("name", 1) if doc.get("name")]

def get_price(collection_name: str, name: str) -> float:
    col = get_collection(collection_name)
    doc = col.find_one({"name": name}, {"price": 1})
    return float((doc or {}).get("price", 0) or 0)

def list_doctors_with_fee() -> List[Dict]:
    col = get_collection("doctors")
    docs = list(col.find({}, {"name": 1, "fee": 1, "specialty": 1}).sort("name", 1))
    for d in docs:
        d["_id"] = str(d["_id"])
    return docs

def add_doctor(name: str, fee: float, specialty: str):
    col = get_collection("doctors")
    col.insert_one({"name": name, "fee": fee, "specialty": specialty})

def update_doctor(doctor_id: str, name: str, fee: float, specialty: str):
    col = get_collection("doctors")
    from bson.objectid import ObjectId
    col.update_one({"_id": ObjectId(doctor_id)}, {"$set": {"name": name, "fee": fee, "specialty": specialty}})

def delete_doctor(doctor_id: str):
    col = get_collection("doctors")
    from bson.objectid import ObjectId
    col.delete_one({"_id": ObjectId(doctor_id)})

# --- User Management ---
def get_user(username: str):
    col = get_collection("users")
    user = col.find_one({"username": username})
    if user and "_id" in user:
        user["id"] = str(user["_id"])
        del user["_id"]
    return user

def get_rights_for_user(username: str):
    expected_user = os.getenv("APP_USERNAME", "admin")
    if username == expected_user:
        return ["patient_registration", "search", "invoice", "reports", "admin"]
    user = get_user(username)
    if not user: return []
    return user.get("rights") or []

def ensure_admin_user():
    col = get_collection("users")
    u = os.getenv("APP_USERNAME", "admin")
    p = os.getenv("APP_PASSWORD", "admin")
    if not col.find_one({"username": u}):
        col.insert_one({"username": u, "password": p, "rights": ["patient_registration", "search", "invoice", "reports", "admin"]})

def list_users():
    col = get_collection("users")
    users = list(col.find({}, {"password": 0}))
    for u in users:
        if "_id" in u:
            u["id"] = str(u["_id"])
            del u["_id"]
    return users

def add_or_update_user(username, password, rights):
    col = get_collection("users")
    col.update_one(
        {"username": username},
        {"$set": {"password": password, "rights": rights}},
        upsert=True
    )

def delete_user(username):
    col = get_collection("users")
    col.delete_one({"username": username})

def list_modules():
    col = get_collection("modules")
    modules = list(col.find({}))
    for m in modules:
        if "_id" in m:
            m["id"] = str(m["_id"])
            del m["_id"]
    return modules

def add_module(key, label):
    col = get_collection("modules")
    col.update_one({"key": key}, {"$set": {"label": label}}, upsert=True)

# --- Aliases and Missing Lookups for Desktop App ---
def preview_registration_no():
    counters = get_collection("counters")
    doc = counters.find_one({"_id": "patient_reg_global"})
    seq = int((doc or {}).get("seq", 0)) + 1
    return f"REG-{seq:06d}"

def allocate_registration_no():
    return get_next_reg_no()

def list_referring_doctors():
    return get_lookups("referring_doctors")

def add_referring_doctor(name):
    col = get_collection("referring_doctors")
    if not col.find_one({"name": name}):
        col.insert_one({"name": name})

def list_lab_tests():
    col = get_collection("lab_tests")
    items = list(col.find({}))
    for i in items:
        if "_id" in i:
            i["id"] = str(i["_id"])
            del i["_id"]
    return items

def list_radiology_services():
    col = get_collection("radiology_services")
    items = list(col.find({}))
    for i in items:
        if "_id" in i:
            i["id"] = str(i["_id"])
            del i["_id"]
    return items

def list_misc_services():
    col = get_collection("misc_services")
    items = list(col.find({}))
    for i in items:
        if "_id" in i:
            i["id"] = str(i["_id"])
            del i["_id"]
    return items

def get_price_by_name(collection, name):
    return get_price(collection, name)


def save_invoice(doc: dict) -> str:
    col = get_collection("invoices")
    res = col.insert_one(doc)
    return str(res.inserted_id)

def list_invoices(reg_no: str = None, invoice_no: str = None) -> list:
    col = get_collection("invoices")
    filters = []
    if reg_no:
        filters.append({"reg_no": {"$regex": re.escape(reg_no), "$options": "i"}})
    if invoice_no:
        filters.append({"invoice_no": {"$regex": re.escape(invoice_no), "$options": "i"}})
    
    query = {}
    if filters:
        if len(filters) > 1:
            query = {"$or": filters}
        else:
            query = filters[0]
            
    docs = list(col.find(query).sort("created_at", -1).limit(50))
    for d in docs:
        d["invoice_id"] = str(d["_id"])
        if "_id" in d: del d["_id"]
    return docs

def get_mis_reports(start_date: str = None, end_date: str = None) -> dict:
    import datetime as _dt
    if not start_date:
        start_date = _dt.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    if not end_date:
        today = _dt.date.today()
        end_date = _dt.datetime.combine(today, _dt.time.max).isoformat()
    
    patients_col = get_collection("patients")
    invoices_col = get_collection("invoices")
    
    # Use the selected range for stats if provided, otherwise use system today
    range_s = start_date
    range_e = end_date
    
    # Filter today for stat cards (strictly today)
    sys_today_s = _dt.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    sys_today_e = _dt.datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999).isoformat()
    
    # 1. Today's Patient Registrations (Count only if created_at exists and is today)
    today_patients = patients_col.count_documents({"created_at": {"$gte": range_s, "$lte": range_e}})
    
    # 2. Invoices in range
    inv_cursor = invoices_col.find({"created_at": {"$gte": start_date, "$lte": end_date}})
    all_invoices = list(inv_cursor)
    
    total_invoices = len(all_invoices)
    total_revenue = sum(float(inv.get("net_total", 0) or 0) for inv in all_invoices)
    total_discount = sum(float(inv.get("discount", 0) or 0) for inv in all_invoices)
    
    # Aggregations
    user_summary = {}
    user_cash_summary = {}
    date_summary = {}
    date_cash_summary = {}
    category_summary = {}
    item_summary = {}
    doctor_summary = {}
    terminal_summary = {}
    
    for inv in all_invoices:
        net = float(inv.get("net_total", 0) or 0)
        mode = inv.get("payment_mode", "Cash")
        
        # User
        u = inv.get("created_by", "Unknown")
        user_summary[u] = user_summary.get(u, 0) + net
        if mode == "Cash":
            user_cash_summary[u] = user_cash_summary.get(u, 0) + net
        
        # Date (YYYY-MM-DD)
        d = inv.get("created_at", "")[:10]
        date_summary[d] = date_summary.get(d, 0) + net
        if mode == "Cash":
            date_cash_summary[d] = date_cash_summary.get(d, 0) + net
        
        # Category
        c = inv.get("category", "Other")
        category_summary[c] = category_summary.get(c, 0) + net
        
        # Item
        i = inv.get("item_name", "Unknown")
        item_summary[i] = item_summary.get(i, 0) + net
        
        # Doctor
        doc = inv.get("doctor_name")
        if doc:
            doctor_summary[doc] = doctor_summary.get(doc, 0) + net
            
        # Terminal
        t = inv.get("terminal_name", "Web")
        terminal_summary[t] = terminal_summary.get(t, 0) + net
        
    # Payment mode summary for selected range
    payment_summary = {}
    for inv in all_invoices:
        pm = inv.get("payment_mode", "Cash")
        payment_summary[pm] = payment_summary.get(pm, 0) + float(inv.get("net_total", 0) or 0)
        
    # Last 7 days revenue trend
    revenue_trend = []
    for i in range(6, -1, -1):
        day = _dt.date.today() - _dt.timedelta(days=i)
        d_start = _dt.datetime.combine(day, _dt.time.min).isoformat()
        d_end = _dt.datetime.combine(day, _dt.time.max).isoformat()
        day_total = sum(float(inv.get("net_total", 0) or 0) for inv in invoices_col.find({"created_at": {"$gte": d_start, "$lte": d_end}}))
        revenue_trend.append({"date": day.strftime("%d-%b"), "amount": day_total})

    # Prepare detailed invoice data (removing internal MongoDB IDs)
    details = []
    for inv in all_invoices:
        inv_copy = dict(inv)
        if "_id" in inv_copy:
            inv_copy["id"] = str(inv_copy["_id"])
            del inv_copy["_id"]
        details.append(inv_copy)

    return {
        "range_summary": {
            "patient_registrations": today_patients,
            "total_invoices": total_invoices,
            "total_revenue": total_revenue,
            "total_discount": total_discount
        },
        "today_stats": {
            "patient_registrations": patients_col.count_documents({"created_at": {"$gte": sys_today_s, "$lte": sys_today_e}}),
            "total_invoices": invoices_col.count_documents({"created_at": {"$gte": sys_today_s, "$lte": sys_today_e}}),
            "total_revenue": sum(float(inv.get("net_total", 0) or 0) for inv in invoices_col.find({"created_at": {"$gte": sys_today_s, "$lte": sys_today_e}}))
        },
        "user_wise": [{"name": k, "value": v} for k, v in user_summary.items()],
        "user_cash_wise": [{"name": k, "value": v} for k, v in user_cash_summary.items()],
        "date_wise": [{"name": k, "value": v} for k, v in sorted(date_summary.items())],
        "date_cash_wise": [{"name": k, "value": v} for k, v in sorted(date_cash_summary.items())],
        "category_wise": [{"name": k, "value": v} for k, v in category_summary.items()],
        "item_wise": [{"name": k, "value": v} for k, v in item_summary.items()],
        "doctor_wise": [{"name": k, "value": v} for k, v in doctor_summary.items()],
        "terminal_wise": [{"name": k, "value": v} for k, v in terminal_summary.items()],
        "payment_wise": [{"name": k, "value": v} for k, v in payment_summary.items()],
        "revenue_trend": revenue_trend,
        "details": details
    }

