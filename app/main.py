import datetime
import os
import re
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from db import save_patient, preview_registration_no, allocate_registration_no, list_referring_doctors, add_referring_doctor, get_patient_by_reg_no, update_patient_by_reg_no, search_patients_by_reg_no, search_patients_by_contact, list_doctors_with_fee, list_lab_tests, list_radiology_services, list_misc_services, get_price_by_name, save_invoice, get_user, get_rights_for_user, ensure_admin_user, list_users, add_or_update_user, delete_user, list_modules, add_module

class PatientRegistration(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self.pack(fill="both", expand=True)
        master.title("Patient Registration")
        self.editing = False
        self._build_form()

    def _build_form(self):
        self.vars = {
            "reg_no": tk.StringVar(),
            "title": tk.StringVar(),
            "first_name": tk.StringVar(),
            "middle_name": tk.StringVar(),
            "last_name": tk.StringVar(),
            "name": tk.StringVar(),
            "guardian": tk.StringVar(),
            "gender": tk.StringVar(),
            "age": tk.StringVar(),
            "age_unit": tk.StringVar(value="Years"),
            "dob": tk.StringVar(),
            "cnic": tk.StringVar(),
            "contact_number": tk.StringVar(),
            "address": tk.StringVar(),
            "blood_group": tk.StringVar(),
            "referring_doctor": tk.StringVar(),
            "patient_type": tk.StringVar(value="Private"),
            "company_name": tk.StringVar(),
        }

        labels = [
            ("Registration No", "reg_no"),
            ("Type", "patient_type"),
            ("Company Name", "company_name"),
            ("Patient Name", "name"),
            ("Father/Husband Name", "guardian"),
            ("Gender", "gender"),
            ("Date of Birth (DD-MM-YYYY)", "dob"),
            ("Age Unit", "age_unit"),
            ("Age", "age"),
            ("CNIC (13 digits)", "cnic"),
            ("Contact Number", "contact_number"),
            ("Address", "address"),
            ("Blood Group", "blood_group"),
            ("Referring Doctor", "referring_doctor"),
        ]

        for i, (text, key) in enumerate(labels):
            ttk.Label(self, text=text).grid(row=i, column=0, sticky="w", padx=6, pady=4)
            if key in ("gender", "blood_group"):
                if key == "gender":
                    widget = ttk.Combobox(self, textvariable=self.vars[key], values=["Male", "Female", "Other"], state="readonly")
                elif key == "blood_group":
                    widget = ttk.Combobox(self, textvariable=self.vars[key], values=["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"], state="readonly")
            elif key in ("address",):
                widget = tk.Text(self, height=3, width=40)
                widget.bind("<Tab>", lambda e: self._focus_next(e.widget))
                widget.bind("<Shift-Tab>", lambda e: self._focus_prev(e.widget))
            elif key in ("age_unit",):
                widget = ttk.Combobox(self, textvariable=self.vars[key], values=["Days", "Months", "Years"], state="readonly")
            else:
                if key == "reg_no":
                    widget = ttk.Entry(self, textvariable=self.vars[key], width=40, state="readonly")
                    try:
                        self.vars["reg_no"].set(preview_registration_no())
                    except Exception:
                        self.vars["reg_no"].set("")
                elif key == "patient_type":
                    widget = ttk.Combobox(self, textvariable=self.vars[key], values=["Private", "Company"], state="readonly")
                elif key == "company_name":
                    widget = ttk.Entry(self, textvariable=self.vars[key], width=40, state="disabled")
                elif key == "name":
                    row_frame = ttk.Frame(self)
                    ttk.Label(row_frame, text="Title").grid(row=0, column=0, padx=(0,6), pady=(0,4), sticky="w")
                    ttk.Label(row_frame, text="First Name").grid(row=0, column=1, padx=(0,6), pady=(0,4), sticky="w")
                    ttk.Label(row_frame, text="Middle Name").grid(row=0, column=2, padx=(0,6), pady=(0,4), sticky="w")
                    ttk.Label(row_frame, text="Last Name").grid(row=0, column=3, padx=(0,6), pady=(0,4), sticky="w")
                    title_cb = ttk.Combobox(row_frame, textvariable=self.vars["title"], values=["Mr.", "Mrs.", "Miss", "Ms.", "Master", "Baby", "Sir", "Madam", "Mx."], state="readonly", width=8)
                    title_cb.grid(row=1, column=0, padx=(0,6), sticky="w")
                    fn = ttk.Entry(row_frame, textvariable=self.vars["first_name"], width=16)
                    fn.grid(row=1, column=1, padx=(0,6), sticky="ew")
                    mn = ttk.Entry(row_frame, textvariable=self.vars["middle_name"], width=16)
                    mn.grid(row=1, column=2, padx=(0,6), sticky="ew")
                    ln = ttk.Entry(row_frame, textvariable=self.vars["last_name"], width=16)
                    ln.grid(row=1, column=3, padx=(0,6), sticky="ew")
                    row_frame.columnconfigure(3, weight=1)
                    widget = row_frame
                    setattr(self, "input_title", title_cb)
                    setattr(self, "input_first_name", fn)
                    setattr(self, "input_middle_name", mn)
                    setattr(self, "input_last_name", ln)
                elif key == "referring_doctor":
                    try:
                        docs = ["SELF"] + list_referring_doctors()
                    except Exception:
                        docs = ["SELF"]
                    widget = ttk.Combobox(self, textvariable=self.vars[key], values=docs, state="normal")
                    if not self.vars[key].get():
                        self.vars[key].set("SELF")
                elif key == "contact_number":
                    vcmd = (self.register(self._vc_only_digits), "%P", "11")
                    widget = tk.Entry(self, textvariable=self.vars[key], width=40, validate="key", validatecommand=vcmd)
                elif key == "cnic":
                    vcmd = (self.register(self._vc_only_digits), "%P", "13")
                    widget = tk.Entry(self, textvariable=self.vars[key], width=40, validate="key", validatecommand=vcmd)
                else:
                    widget = ttk.Entry(self, textvariable=self.vars[key], width=40)
            widget.grid(row=i, column=1, sticky="ew", padx=6, pady=4)
            setattr(self, f"input_{key}", widget)

        self.columnconfigure(1, weight=1)

        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=len(labels), column=0, columnspan=2, sticky="e", pady=8)
        ttk.Button(btn_frame, text="💾 Save", command=self._on_save, style="Icon.TButton").pack(side="right", padx=6)
        ttk.Button(btn_frame, text="🧹 Clear", command=self._clear, style="Icon.TButton").pack(side="right", padx=6)
        ttk.Button(btn_frame, text="🔍 Search", command=self._open_search, style="Icon.TButton").pack(side="left", padx=6)
        inv_frame = ttk.Frame(self)
        inv_frame.grid(row=len(labels)+1, column=0, columnspan=2, pady=8)
        ttk.Button(inv_frame, text="🧾 Invoice", command=self._open_invoice, style="Invoice.TButton").pack(padx=6)

        self.vars["dob"].trace_add("write", lambda *args: self._update_age_from_dob())
        self.vars["age_unit"].trace_add("write", lambda *args: (self._update_age_from_dob(), self._update_dob_from_age(True)))
        self.vars["age"].trace_add("write", lambda *args: self._update_dob_from_age(True))
        self.vars["title"].trace_add("write", lambda *args: self._update_gender_from_title())
        self.vars["patient_type"].trace_add("write", lambda *args: self._on_type_change())
        self.bind_all("<y>", lambda e: self.vars["age_unit"].set("Years"))
        self.bind_all("<Y>", lambda e: self.vars["age_unit"].set("Years"))
        self.bind_all("<m>", lambda e: self.vars["age_unit"].set("Months"))
        self.bind_all("<M>", lambda e: self.vars["age_unit"].set("Months"))
        self.bind_all("<d>", lambda e: self.vars["age_unit"].set("Days"))
        self.bind_all("<D>", lambda e: self.vars["age_unit"].set("Days"))
        self.bind_all("<Control-s>", lambda e: self._on_save())
        self.bind_all("<Control-S>", lambda e: self._on_save())
        self.bind_all("<Control-f>", lambda e: self._open_search())
        self.bind_all("<Control-F>", lambda e: self._open_search())
        self.bind_all("<Control-Shift-c>", lambda e: self._clear())
        try:
            self.input_age.bind("<Button-1>", lambda e: self._reset_dob())
            self.input_age.bind("<FocusIn>", lambda e: self._reset_dob())
        except Exception:
            pass
        try:
            self.input_age_unit.bind("<Button-1>", lambda e: self._reset_dob())
            self.input_age_unit.bind("<FocusIn>", lambda e: self._reset_dob())
        except Exception:
            pass

    def _text_value(self, widget):
        if isinstance(widget, tk.Text):
            return widget.get("1.0", "end").strip()
        return widget.get()

    def _clear(self):
        current_reg = self.vars["reg_no"].get()
        for key, var in self.vars.items():
            if key in ("address",):
                getattr(self, f"input_{key}").delete("1.0", "end")
            else:
                var.set("")
        self.editing = False
        self.vars["reg_no"].set(current_reg or preview_registration_no())
        self.vars["age_unit"].set("Years")
        self.vars["patient_type"].set("Private")
        try:
            self.input_company_name.configure(state="disabled")
        except Exception:
            pass
    def _reset_dob(self):
        self.vars["dob"].set("")

    def _validate(self, data):
        if not data["reg_no"].strip():
            return "Registration No is required"
        if not data["name"].strip():
            return "Patient Name is required"
        if data["gender"] not in {"Male", "Female", "Other"}:
            return "Select Gender"
        if data.get("patient_type") not in {"Private", "Company"}:
            return "Select Type"
        if data.get("patient_type") == "Company":
            if not data.get("company_name","").strip():
                return "Company Name is required for Company Type"
        if data["dob"]:
            if not re.fullmatch(r"\d{1,2}-\d{1,2}-\d{4}", data["dob"]):
                return "DOB format must be DD-MM-YYYY"
            try:
                datetime.datetime.strptime(data["dob"], "%d-%m-%Y")
            except ValueError:
                return "Invalid DOB date"
        else:
            if not data["age"].strip():
                return "Age is required or enter Date of Birth"
            if not data["age"].isdigit():
                return "Age must be a number"
            if data.get("age_unit") not in {"Days", "Months", "Years"}:
                return "Select Age Unit"
        if data["cnic"]:
            if not re.fullmatch(r"\d{13}", data["cnic"]):
                return "CNIC must be 13 digits"
        if data.get("contact_number"):
            if not re.fullmatch(r"\d{10,11}", data["contact_number"]):
                return "Contact Number must be 10–11 digits"
        return None

    def _on_save(self):
        payload = {
            "reg_no": self.vars["reg_no"].get().strip(),
            "title": self.vars["title"].get().strip(),
            "first_name": self.vars["first_name"].get().strip(),
            "middle_name": self.vars["middle_name"].get().strip(),
            "last_name": self.vars["last_name"].get().strip(),
            "name": " ".join([s for s in [self.vars['first_name'].get().strip(), self.vars['middle_name'].get().strip(), self.vars['last_name'].get().strip()] if s]),
            "guardian": self.vars["guardian"].get().strip(),
            "gender": self.vars["gender"].get().strip(),
            "dob": self.vars["dob"].get().strip(),
            "age_value": self.vars["age"].get().strip(),
            "age_unit": self.vars["age_unit"].get().strip(),
            "cnic": self.vars["cnic"].get().strip(),
            "contact_number": self.vars["contact_number"].get().strip(),
            "address": self._text_value(self.input_address),
            "blood_group": self.vars["blood_group"].get().strip(),
            "created_at": datetime.datetime.now().isoformat(),
            "referring_doctor": self.vars["referring_doctor"].get().strip(),
            "patient_type": self.vars["patient_type"].get().strip(),
            "company_name": self.vars["company_name"].get().strip(),
        }
        if self.vars["dob"].get().strip():
            dob_age = self._compute_age(self.vars["dob"].get().strip(), self.vars["age_unit"].get().strip() or "Months")
            payload["age_value"] = str(dob_age)
        err = self._validate(payload)
        if err:
            messagebox.showerror("Validation Error", err)
            return
        try:
            if self.editing:
                reg = payload["reg_no"]
                update_patient_by_reg_no(reg, {k: v for k, v in payload.items() if k != "reg_no"})
                inserted_id = reg
            else:
                reg = allocate_registration_no()
                payload["reg_no"] = reg
                inserted_id = save_patient(payload)
            rd = payload.get("referring_doctor", "").strip()
            if rd and rd != "SELF":
                add_referring_doctor(rd)
            messagebox.showinfo("Saved", f"Saved with ID: {inserted_id}")
            self._clear()
        except Exception as e:
            messagebox.showerror("Database Error", str(e))

    def _compute_age(self, dob_str: str, unit: str) -> int:
        try:
            dob = datetime.datetime.strptime(dob_str, "%d-%m-%Y").date()
        except ValueError:
            return 0
        today = datetime.date.today()
        if unit == "Days":
            delta = today - dob
            return max(delta.days, 0)
        months = (today.year - dob.year) * 12 + (today.month - dob.month)
        if today.day < dob.day:
            months -= 1
        if unit == "Months":
            return max(months, 0)
        years = months // 12
        return max(years, 0)

    def _update_age_from_dob(self):
        dob = self.vars["dob"].get().strip()
        if dob:
            try:
                datetime.datetime.strptime(dob, "%d-%m-%Y")
            except ValueError:
                return
            months = self._compute_age(dob, "Months")
            if months >= 12:
                new_unit = "Years"
                val = self._compute_age(dob, "Years")
            elif months > 0:
                new_unit = "Months"
                val = months
            else:
                new_unit = "Days"
                val = self._compute_age(dob, "Days")
            if self.vars["age_unit"].get() != new_unit:
                self.vars["age_unit"].set(new_unit)
            self.vars["age"].set(str(val))

    def _update_dob_from_age(self, force: bool = False):
        dob_current = self.vars["dob"].get().strip()
        age_str = self.vars["age"].get().strip()
        unit = self.vars["age_unit"].get().strip() or "Months"
        if dob_current and not force:
            return
        if not age_str.isdigit():
            return
        age_val = int(age_str)
        today = datetime.date.today()
        if unit == "Days":
            dob = today - datetime.timedelta(days=age_val)
        elif unit == "Months":
            y = today.year
            m = today.month - age_val
            d = today.day
            while m <= 0:
                m += 12
                y -= 1
            try:
                dob = datetime.date(y, m, d)
            except ValueError:
                while True:
                    d -= 1
                    try:
                        dob = datetime.date(y, m, d)
                        break
                    except ValueError:
                        if d <= 1:
                            dob = datetime.date(y, m, 1)
                            break
        elif unit == "Years":
            try:
                dob = datetime.date(today.year - age_val, today.month, today.day)
            except ValueError:
                dob = datetime.date(today.year - age_val, today.month, 1)
        else:
            return
        self.vars["dob"].set(dob.strftime("%d-%m-%Y"))
    def _focus_next(self, w):
        w.tk_focusNext().focus()
        return "break"
    def _focus_prev(self, w):
        w.tk_focusPrev().focus()
        return "break"
    def _update_gender_from_title(self):
        t = self.vars["title"].get().strip()
        male_titles = {"Mr.", "Master", "Sir"}
        female_titles = {"Mrs.", "Miss", "Ms.", "Madam"}
        if t in male_titles:
            self.vars["gender"].set("Male")
        elif t in female_titles:
            self.vars["gender"].set("Female")
    def _vc_only_digits(self, value, max_len):
        if value is None:
            return True
        if not value.isdigit() and value != "":
            return False
        try:
            m = int(max_len)
        except Exception:
            m = 0
        if m > 0 and len(value) > m:
            return False
        return True
    def _open_search(self):
        win = tk.Toplevel(self)
        win.title("Search Patients")
        frm = ttk.Frame(win, padding=8)
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text="Search By").grid(row=0, column=0, padx=4, pady=4, sticky="w")
        mode = tk.StringVar(value="Mobile")
        ttk.Combobox(frm, textvariable=mode, values=["Mobile", "Registration"], state="readonly").grid(row=0, column=1, padx=4, pady=4, sticky="w")
        ttk.Label(frm, text="Query").grid(row=1, column=0, padx=4, pady=4, sticky="w")
        query = tk.StringVar()
        ttk.Entry(frm, textvariable=query, width=30).grid(row=1, column=1, padx=4, pady=4, sticky="ew")
        tv = ttk.Treeview(frm, columns=("reg_no", "name", "mobile"), show="headings", height=10)
        tv.heading("reg_no", text="Reg No")
        tv.heading("name", text="Name")
        tv.heading("mobile", text="Mobile")
        tv.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=4, pady=8)
        frm.rowconfigure(2, weight=1)
        frm.columnconfigure(1, weight=1)
        def do_search():
            q = query.get().strip()
            tv.delete(*tv.get_children())
            if not q:
                return
            if mode.get() == "Mobile":
                results = search_patients_by_contact(q)
            else:
                results = search_patients_by_reg_no(q)
            for doc in results:
                tv.insert("", "end", values=(doc.get("reg_no",""), doc.get("name",""), doc.get("contact_number","")), iid=str(doc.get("_id","")))
        ttk.Button(frm, text="🔍 Search", command=do_search, style="Icon.TButton").grid(row=1, column=2, padx=4, pady=4, sticky="w")
        def on_open(evt):
            sel = tv.selection()
            if not sel:
                return
            item = tv.item(sel[0])
            reg = item["values"][0]
            doc = get_patient_by_reg_no(reg)
            if not doc:
                return
            self._load_patient(doc)
            win.destroy()
        tv.bind("<Double-Button-1>", on_open)
    def _load_patient(self, doc: dict):
        self.editing = True
        self.vars["reg_no"].set(doc.get("reg_no",""))
        self.vars["title"].set(doc.get("title",""))
        self.vars["first_name"].set(doc.get("first_name",""))
        self.vars["middle_name"].set(doc.get("middle_name",""))
        self.vars["last_name"].set(doc.get("last_name",""))
        if not any([self.vars["first_name"].get(), self.vars["middle_name"].get(), self.vars["last_name"].get()]):
            parts = (doc.get("name","") or "").split()
            if parts:
                self.vars["first_name"].set(parts[0])
                if len(parts) > 2:
                    self.vars["middle_name"].set(" ".join(parts[1:-1]))
                    self.vars["last_name"].set(parts[-1])
                elif len(parts) == 2:
                    self.vars["last_name"].set(parts[1])
        self.vars["guardian"].set(doc.get("guardian",""))
        self.vars["gender"].set(doc.get("gender",""))
        self.vars["dob"].set(doc.get("dob",""))
        self.vars["age"].set(str(doc.get("age_value","") or ""))
        self.vars["age_unit"].set(doc.get("age_unit","") or "Months")
        self.vars["cnic"].set(doc.get("cnic",""))
        self.vars["contact_number"].set(doc.get("contact_number",""))
        self.input_address.delete("1.0", "end")
        self.input_address.insert("1.0", doc.get("address",""))
        self.vars["blood_group"].set(doc.get("blood_group",""))
        self.vars["referring_doctor"].set(doc.get("referring_doctor","") or "SELF")
        self.vars["patient_type"].set(doc.get("patient_type","") or "Private")
        self.vars["company_name"].set(doc.get("company_name",""))
        self._on_type_change()

    def _on_type_change(self):
        t = self.vars["patient_type"].get().strip()
        try:
            if t == "Company":
                self.input_company_name.configure(state="normal")
            else:
                self.input_company_name.configure(state="disabled")
                self.vars["company_name"].set("")
        except Exception:
            pass
    def _open_invoice(self):
        win = tk.Toplevel(self)
        win.title("Invoice / Service")
        frm = ttk.Frame(win, padding=12)
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text="Registration No").grid(row=0, column=0, padx=6, pady=6, sticky="w")
        ttk.Label(frm, text=self.vars["reg_no"].get()).grid(row=0, column=1, padx=6, pady=6, sticky="w")
        ttk.Label(frm, text="Patient Name").grid(row=1, column=0, padx=6, pady=6, sticky="w")
        name_display = " ".join([s for s in [self.vars["title"].get(), self.vars["first_name"].get(), self.vars["middle_name"].get(), self.vars["last_name"].get()] if s]).strip()
        ttk.Label(frm, text=name_display).grid(row=1, column=1, padx=6, pady=6, sticky="w")
        ttk.Label(frm, text="Date/Time").grid(row=2, column=0, padx=6, pady=6, sticky="w")
        dt_val = tk.StringVar(value=datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S"))
        ttk.Label(frm, textvariable=dt_val).grid(row=2, column=1, padx=6, pady=6, sticky="w")
        ttk.Label(frm, text="Category").grid(row=3, column=0, padx=6, pady=6, sticky="w")
        category = tk.StringVar(value="Consultancy")
        ttk.Combobox(frm, textvariable=category, values=["Consultancy", "LAB", "Radiology", "Miscellaneous"], state="readonly").grid(row=3, column=1, padx=6, pady=6, sticky="ew")
        ttk.Label(frm, text="Item").grid(row=4, column=0, padx=6, pady=6, sticky="w")
        item = tk.StringVar()
        item_cb = ttk.Combobox(frm, textvariable=item, state="readonly")
        item_cb.grid(row=4, column=1, padx=6, pady=6, sticky="ew")
        ttk.Label(frm, text="Doctor").grid(row=5, column=0, padx=6, pady=6, sticky="w")
        doctor = tk.StringVar()
        doctor_cb = ttk.Combobox(frm, textvariable=doctor, state="readonly")
        doctor_cb.grid(row=5, column=1, padx=6, pady=6, sticky="ew")
        ttk.Label(frm, text="Charges").grid(row=6, column=0, padx=6, pady=6, sticky="w")
        charges = tk.StringVar(value="0")
        ttk.Entry(frm, textvariable=charges, width=18).grid(row=6, column=1, padx=6, pady=6, sticky="w")
        ttk.Label(frm, text="Discount").grid(row=7, column=0, padx=6, pady=6, sticky="w")
        discount = tk.StringVar(value="0")
        ttk.Entry(frm, textvariable=discount, width=18).grid(row=7, column=1, padx=6, pady=6, sticky="w")
        ttk.Label(frm, text="Net Total").grid(row=8, column=0, padx=6, pady=6, sticky="w")
        net_total = tk.StringVar(value="0")
        ttk.Label(frm, textvariable=net_total).grid(row=8, column=1, padx=6, pady=6, sticky="w")
        ttk.Label(frm, text="Payment Mode").grid(row=9, column=0, padx=6, pady=6, sticky="w")
        pay_mode = tk.StringVar(value="Cash")
        ttk.Combobox(frm, textvariable=pay_mode, values=["Cash", "Card"], state="readonly").grid(row=9, column=1, padx=6, pady=6, sticky="w")
        card_frame = ttk.Frame(frm)
        card_frame.grid(row=10, column=0, columnspan=2, sticky="ew", padx=6, pady=6)
        ttk.Label(card_frame, text="Cardholder Name").grid(row=0, column=0, padx=6, pady=4, sticky="w")
        ch_name = tk.StringVar()
        ttk.Entry(card_frame, textvariable=ch_name, width=24).grid(row=0, column=1, padx=6, pady=4, sticky="w")
        ttk.Label(card_frame, text="Card Number").grid(row=1, column=0, padx=6, pady=4, sticky="w")
        ch_number = tk.StringVar()
        ttk.Entry(card_frame, textvariable=ch_number, width=24).grid(row=1, column=1, padx=6, pady=4, sticky="w")
        ttk.Label(card_frame, text="Expiry (MM/YY)").grid(row=2, column=0, padx=6, pady=4, sticky="w")
        ch_exp = tk.StringVar()
        ttk.Entry(card_frame, textvariable=ch_exp, width=10).grid(row=2, column=1, padx=6, pady=4, sticky="w")
        btns = ttk.Frame(frm)
        btns.grid(row=11, column=0, columnspan=2, sticky="e", pady=8)
        def compute_net(*args):
            try:
                c = float(charges.get().strip() or "0")
            except Exception:
                c = 0.0
            try:
                d = float(discount.get().strip() or "0")
            except Exception:
                d = 0.0
            if d < 0:
                d = 0.0
            net = c - d
            if net < 0:
                net = 0.0
            net_total.set(f"{net:.2f}")
        charges.trace_add("write", compute_net)
        discount.trace_add("write", compute_net)
        def refresh_items():
            cat = category.get().strip()
            if cat == "Consultancy":
                ds = list_doctors_with_fee()
                doctor_cb.configure(state="readonly")
                doctor_cb["values"] = [d.get("name","") for d in ds] or list_referring_doctors()
                if doctor_cb["values"]:
                    doctor.set(doctor_cb["values"][0])
                item_cb.configure(state="readonly")
                item_cb["values"] = ["Consultancy Fee"]
                item.set("Consultancy Fee")
                try:
                    sel = doctor.get().strip()
                    fee = 0.0
                    for d in ds:
                        if d.get("name","") == sel:
                            fee = float(d.get("fee", 0) or 0)
                            break
                    charges.set(str(fee))
                except Exception:
                    charges.set("0")
            elif cat == "LAB":
                doctor_cb.configure(state="disabled")
                doctor.set("")
                tests = list_lab_tests()
                vals = [t.get("name","") for t in tests]
                item_cb.configure(state="readonly")
                item_cb["values"] = vals
                if vals:
                    item.set(vals[0])
                else:
                    item.set("")
                if item.get():
                    pr = get_price_by_name("lab_tests", item.get())
                    charges.set(str(pr))
                else:
                    charges.set("0")
            elif cat == "Radiology":
                doctor_cb.configure(state="disabled")
                doctor.set("")
                rs = list_radiology_services()
                vals = [r.get("name","") for r in rs]
                item_cb.configure(state="readonly")
                item_cb["values"] = vals
                if vals:
                    item.set(vals[0])
                else:
                    item.set("")
                if item.get():
                    pr = get_price_by_name("radiology_services", item.get())
                    charges.set(str(pr))
                else:
                    charges.set("0")
            else:
                doctor_cb.configure(state="disabled")
                doctor.set("")
                ms = list_misc_services()
                base = [m.get("name","") for m in ms]
                if not base:
                    base = ["Dressing", "Injection charges"]
                item_cb.configure(state="readonly")
                item_cb["values"] = base
                item.set(base[0] if base else "")
                if item.get():
                    pr = get_price_by_name("misc_services", item.get())
                    charges.set(str(pr))
                else:
                    charges.set("0")
            compute_net()
        def on_item_change(*args):
            cat = category.get().strip()
            nm = item.get().strip()
            if not nm:
                charges.set("0")
                compute_net()
                return
            if cat == "LAB":
                charges.set(str(get_price_by_name("lab_tests", nm)))
            elif cat == "Radiology":
                charges.set(str(get_price_by_name("radiology_services", nm)))
            elif cat == "Miscellaneous":
                charges.set(str(get_price_by_name("misc_services", nm)))
            compute_net()
        def on_doctor_change(*args):
            ds = list_doctors_with_fee()
            sel = doctor.get().strip()
            fee = 0.0
            for d in ds:
                if d.get("name","") == sel:
                    fee = float(d.get("fee", 0) or 0)
                    break
            charges.set(str(fee))
            compute_net()
        def on_mode_change(*args):
            if pay_mode.get() == "Card":
                for c in card_frame.winfo_children():
                    c.configure(state="normal")
            else:
                ch_name.set("")
                ch_number.set("")
                ch_exp.set("")
                for c in card_frame.winfo_children():
                    c.configure(state="disabled")
        category.trace_add("write", lambda *a: refresh_items())
        item.trace_add("write", on_item_change)
        doctor.trace_add("write", on_doctor_change)
        pay_mode.trace_add("write", on_mode_change)
        refresh_items()
        on_mode_change()
        def generate():
            try:
                c = float(charges.get().strip() or "0")
            except Exception:
                c = 0.0
            try:
                d = float(discount.get().strip() or "0")
            except Exception:
                d = 0.0
            if d < 0:
                d = 0.0
            net = c - d
            if net < 0:
                net = 0.0
            inv = {
                "created_at": datetime.datetime.now().isoformat(),
                "reg_no": self.vars["reg_no"].get().strip(),
                "patient_name": name_display,
                "category": category.get().strip(),
                "item_name": item.get().strip(),
                "doctor_name": doctor.get().strip(),
                "charges": c,
                "discount": d,
                "net_total": net,
                "payment_mode": pay_mode.get().strip(),
            }
            if not inv["reg_no"] or not inv["category"] or not inv["item_name"]:
                messagebox.showerror("Validation Error", "Select category and item; ensure Registration No is present")
                return
            if inv["net_total"] <= 0:
                messagebox.showerror("Validation Error", "Net Total must be greater than 0")
                return
            if inv["payment_mode"] == "Card":
                num = "".join([ch for ch in ch_number.get() if ch.isdigit()])
                last4 = num[-4:] if len(num) >= 4 else ""
                inv["cardholder_name"] = ch_name.get().strip()
                inv["card_last4"] = last4
                inv["card_expiry"] = ch_exp.get().strip()
                if not inv["cardholder_name"] or len(num) < 12 or not inv["card_expiry"]:
                    messagebox.showerror("Validation Error", "Enter cardholder, valid card number, and expiry")
                    return
            try:
                iid = save_invoice(inv)
            except Exception as e:
                messagebox.showerror("Invoice Error", str(e))
                return
            try:
                folder = os.path.join(os.path.dirname(__file__), "invoices")
                os.makedirs(folder, exist_ok=True)
                ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
                fname = f"invoice-{self.vars['reg_no'].get().strip()}-{ts}.pdf"
                fpath = os.path.join(folder, fname)
                self._generate_invoice_pdf(inv, fpath)
                messagebox.showinfo("Invoice Generated", f"Saved #{iid}\nPDF: {fpath}")
                try:
                    if os.path.exists(fpath):
                        os.startfile(fpath)
                except Exception:
                    pass
            except Exception as e:
                messagebox.showerror("PDF Error", str(e))
        ttk.Button(btns, text="🧾 Generate", command=generate, style="Icon.TButton").pack(side="right", padx=6)
        ttk.Button(btns, text="❌ Close", command=win.destroy, style="Icon.TButton").pack(side="right", padx=6)
        frm.columnconfigure(1, weight=1)
    def _generate_invoice_pdf(self, inv: dict, fpath: str):
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(fpath, pagesize=A4)
        w, h = A4
        y = h - 50
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, y, "Invoice")
        y -= 30
        c.setFont("Helvetica", 11)
        c.drawString(50, y, f"Date/Time: {datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')}")
        y -= 20
        c.drawString(50, y, f"Registration No: {inv.get('reg_no','')}")
        y -= 20
        c.drawString(50, y, f"Patient Name: {inv.get('patient_name','')}")
        y -= 20
        c.drawString(50, y, f"Category: {inv.get('category','')}")
        y -= 20
        if inv.get("doctor_name"):
            c.drawString(50, y, f"Doctor: {inv.get('doctor_name','')}")
            y -= 20
        if inv.get("item_name"):
            c.drawString(50, y, f"Item: {inv.get('item_name','')}")
            y -= 20
        c.drawString(50, y, f"Charges: {inv.get('charges',0):.2f}")
        y -= 20
        c.drawString(50, y, f"Discount: {inv.get('discount',0):.2f}")
        y -= 20
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, f"Net Total: {inv.get('net_total',0):.2f}")
        y -= 30
        c.setFont("Helvetica", 11)
        c.drawString(50, y, f"Payment Mode: {inv.get('payment_mode','')}")
        y -= 20
        if inv.get("payment_mode") == "Card":
            c.drawString(50, y, f"Cardholder: {inv.get('cardholder_name','')}")
            y -= 20
            c.drawString(50, y, f"Card Last4: {inv.get('card_last4','')}")
            y -= 20
            c.drawString(50, y, f"Expiry: {inv.get('card_expiry','')}")
            y -= 20
        c.showPage()
        c.save()

class LoginDialog(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Login")
        self.resizable(False, False)
        try:
            self.geometry("520x420")
            self.update_idletasks()
            w = 520
            h = 420
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            x = (sw - w) // 2
            y = (sh - h) // 3
            self.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            pass
        self.authorized = False
        self.username = ""
        self.rights = []
        top = ttk.Frame(self)
        top.pack(fill="both", expand=True)
        img_frame = ttk.Frame(top)
        img_frame.pack(fill="x")
        self._bg_img = None
        try:
            base1 = os.path.dirname(__file__)
            base2 = os.path.dirname(base1)
            base3 = os.path.dirname(base2)
            candidates = [
                os.path.join(base3, "login.jpg"),
                os.path.join(base3, "login.png"),
                os.path.join(base2, "login.jpg"),
                os.path.join(base2, "login.png"),
                os.path.join(base1, "login.jpg"),
                os.path.join(base1, "login.png"),
            ]
            img_path = ""
            for p in candidates:
                if os.path.exists(p):
                    img_path = p
                    break
            if os.path.exists(img_path):
                try:
                    from PIL import Image, ImageTk  # type: ignore
                    im = Image.open(img_path)
                    im = im.resize((520, 220))
                    self._bg_img = ImageTk.PhotoImage(im)
                except Exception:
                    try:
                        self._bg_img = tk.PhotoImage(file=img_path)
                    except Exception:
                        self._bg_img = None
                if self._bg_img:
                    lbl_img = ttk.Label(img_frame, image=self._bg_img)
                    lbl_img.pack(fill="x")
        except Exception:
            pass
        frm = ttk.Frame(top, padding=16)
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text="Username").grid(row=0, column=0, padx=6, pady=8, sticky="w")
        ttk.Label(frm, text="Password").grid(row=1, column=0, padx=6, pady=8, sticky="w")
        self._u = tk.StringVar()
        self._p = tk.StringVar()
        ttk.Entry(frm, textvariable=self._u, width=28).grid(row=0, column=1, padx=6, pady=8, sticky="ew")
        ttk.Entry(frm, textvariable=self._p, show="*", width=28).grid(row=1, column=1, padx=6, pady=8, sticky="ew")
        frm.columnconfigure(1, weight=1)
        btns = ttk.Frame(frm)
        btns.grid(row=2, column=0, columnspan=2, sticky="e", pady=12)
        ttk.Button(btns, text="🔐 Login", command=self._do_login, style="Icon.TButton").pack(side="right", padx=6)
        ttk.Button(btns, text="❌ Cancel", command=self._cancel, style="Icon.TButton").pack(side="right", padx=6)
        self.bind("<Return>", lambda e: self._do_login())
        self.protocol("WM_DELETE_WINDOW", self._cancel)
    def _do_login(self):
        user = self._u.get().strip()
        pwd = self._p.get().strip()
        expected_user = os.getenv("APP_USERNAME", "admin")
        expected_pass = os.getenv("APP_PASSWORD", "admin")
        try:
            ensure_admin_user()
        except Exception:
            pass
        ok = False
        if user == expected_user and pwd == expected_pass:
            ok = True
            self.rights = get_rights_for_user(user)
        else:
            doc = get_user(user)
            if doc and str(doc.get("password","")) == pwd:
                ok = True
                self.rights = doc.get("rights") or []
        if ok:
            self.authorized = True
            self.username = user
            if not self.rights:
                self.rights = ["patient_registration"]
            self.destroy()
        else:
            messagebox.showerror("Login Failed", "Invalid username or password")
    def _cancel(self):
        self.authorized = False
        self.destroy()

class TileButton(tk.Canvas):
    def __init__(self, master, icon, label, command=None, width=180, height=150, bg="#f4f7fb", tile="#ffffff", hover="#e5f0ff", text="#2d557d"):
        super().__init__(master, width=width, height=height, highlightthickness=0, bd=0, bg=bg)
        self._bg_color = bg
        self._tile_color = tile
        self._hover_color = hover
        self._text_color = text
        self._command = command
        self._shadow = self.create_rectangle(10, 12, width-6, height-6, outline="", fill="#dfe6ed")
        self._rect = self.create_rectangle(6, 6, width-10, height-10, outline="", fill=self._tile_color)
        self._icon = self.create_text(width//2, 52, text=icon, font=("Segoe UI Emoji", 30), fill=self._text_color)
        self._label = self.create_text(width//2, height-40, text=label, font=("Segoe UI", 12, "bold"), fill=self._text_color)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
    def _on_enter(self, e):
        self.itemconfig(self._rect, fill=self._hover_color)
    def _on_leave(self, e):
        self.itemconfig(self._rect, fill=self._tile_color)
    def _on_click(self, e):
        if self._command:
            try:
                self._command()
            except Exception as ex:
                try:
                    messagebox.showerror("Error", str(ex))
                except Exception:
                    pass
class SidebarIcon(tk.Canvas):
    def __init__(self, master, icon, tooltip, command=None, size=44, bg="#0e3a5d", fg="#ffffff", hover="#195a8e"):
        super().__init__(master, width=size+12, height=size+12, bg=bg, highlightthickness=0, bd=0)
        self._bg = bg
        self._hover = hover
        self._cmd = command
        self._circle = self.create_oval(6, 6, size+6, size+6, outline="", fill=hover if tooltip == "Dashboard" else "#114b78")
        self._text = self.create_text((size+12)//2, (size+12)//2, text=icon, fill=fg, font=("Segoe UI Emoji", 16))
        self.bind("<Enter>", lambda e: self._set(True))
        self.bind("<Leave>", lambda e: self._set(False))
        self.bind("<Button-1>", self._click)
    def _set(self, hov):
        self.itemconfig(self._circle, fill=self._hover if hov else "#114b78")
    def _click(self, e):
        if self._cmd:
            try:
                self._cmd()
            except Exception:
                pass

class Dashboard(ttk.Frame):
    def __init__(self, master, host):
        super().__init__(master, padding=16)
        self.pack(fill="both", expand=True)
        self.host = host
        self._banner_img = None
        try:
            base1 = os.path.dirname(__file__)
            base2 = os.path.dirname(base1)
            base3 = os.path.dirname(base2)
            candidates = [
                os.path.join(base3, "Main screen.png"),
                os.path.join(base3, "Main screen.jpg"),
                os.path.join(base2, "Main screen.png"),
                os.path.join(base2, "Main screen.jpg"),
            ]
            bpath = ""
            for p in candidates:
                if os.path.exists(p):
                    bpath = p
                    break
            if bpath:
                top = ttk.Frame(self)
                top.pack(fill="x", pady=(0, 8))
                try:
                    from PIL import Image, ImageTk  # type: ignore
                    im = Image.open(bpath)
                    w = min(920, im.size[0])
                    ratio = w / im.size[0]
                    h = int(im.size[1] * ratio)
                    im = im.resize((w, h))
                    self._banner_img = ImageTk.PhotoImage(im)
                except Exception:
                    try:
                        self._banner_img = tk.PhotoImage(file=bpath)
                    except Exception:
                        self._banner_img = None
                if self._banner_img:
                    ttk.Label(top, image=self._banner_img).pack()
        except Exception:
            pass
        try:
            grid = ttk.Frame(self)
            grid.pack(fill="both", expand=True)
            tiles = [
                ("📅", "Appointment", lambda: self.host._open_placeholder("Appointment")),
                ("📝", "Patient Registration", self.host._open_pr),
                ("🧑‍⚕️", "Clinical Management", lambda: self.host._open_placeholder("Clinical Management")),
                ("🛏️", "Day Care", lambda: self.host._open_placeholder("Day Care")),
                ("🚨", "Emergency Room", lambda: self.host._open_placeholder("Emergency Room")),
                ("🩺", "Operation Theatre", lambda: self.host._open_placeholder("Operation Theatre")),
                ("🛡️", "Insurance and eClaim", lambda: self.host._open_placeholder("Insurance and eClaim")),
                ("💉", "Phlebotomy", lambda: self.host._open_placeholder("Phlebotomy")),
                ("🧪", "Laboratory", lambda: self.host._open_placeholder("Laboratory")),
                ("🩸", "Blood Bank", lambda: self.host._open_placeholder("Blood Bank")),
                ("🩻", "Radiology", lambda: self.host._open_placeholder("Radiology")),
                ("📦", "Inventory", lambda: self.host._open_placeholder("Inventory")),
                ("📊", "MIS Reports", self.host._open_reports),
                ("👩‍⚕️", "Nurse Station", lambda: self.host._open_placeholder("Nurse Station")),
                ("🛠️", "Inventory Setup", lambda: self.host._open_placeholder("Inventory Setup")),
                ("📄", "Discharge Summary", lambda: self.host._open_placeholder("Discharge Summary")),
                ("✅", "Custom Template", lambda: self.host._open_placeholder("Custom Template")),
                ("⚙️", "Software Management", self.host._open_admin),
            ]
            cols = 5
            for i, (icon, label, cmd) in enumerate(tiles):
                r = i // cols
                c = i % cols
                tile = TileButton(grid, icon, label, cmd)
                tile.grid(row=r, column=c, padx=12, pady=12, sticky="nsew")
            for i in range(cols):
                grid.columnconfigure(i, weight=1)
            for j in range((len(tiles) + cols - 1) // cols):
                grid.rowconfigure(j, weight=1)
        except Exception:
            f = ttk.Frame(self, padding=8)
            f.pack(fill="both", expand=True)
            ttk.Label(f, text="Dashboard", font=("Segoe UI", 14, "bold")).pack(anchor="w")
            ttk.Button(f, text="Patient Registration", command=self.host._open_pr, style="Icon.TButton").pack(anchor="w", pady=6)

class ERPMain(ttk.Frame):
    def __init__(self, master, username: str, rights: list[str]):
        super().__init__(master, padding=0)
        self.pack(fill="both", expand=True)
        master.title("Hospital ERP")
        self.username = username
        self.rights = set(rights or [])
        top = ttk.Frame(self, padding=8)
        top.pack(side="top", fill="x")
        
        # Load Logo for Desktop App
        try:
            logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logo.png")
            if os.path.exists(logo_path):
                from PIL import Image, ImageTk
                im = Image.open(logo_path)
                im = im.resize((50, 50))
                self._desktop_logo = ImageTk.PhotoImage(im)
                ttk.Label(top, image=self._desktop_logo).pack(side="left", padx=(0, 10))
        except Exception:
            pass

        ttk.Label(top, text="AMI Medical Center", font=("Segoe UI", 16, "bold")).pack(side="left")
        ttk.Label(top, text="\"Your Health, Our Commitment.\"", font=("Segoe UI", 10, "italic")).pack(side="left", padx=12)
        ttk.Label(top, text=f"Admin ▾  {self.username}", font=("Segoe UI", 10)).pack(side="right")
        mid = ttk.Frame(self)
        mid.pack(fill="both", expand=True)
        leftbar = tk.Frame(mid, bg="#0e3a5d", width=64)
        leftbar.pack(side="left", fill="y")
        leftbar.pack_propagate(False)
        self.content = ttk.Frame(mid, padding=8)
        self.content.pack(side="right", fill="both", expand=True)
        SidebarIcon(leftbar, "🏠", "Dashboard", self._open_dashboard).pack(pady=10)
        SidebarIcon(leftbar, "🧾", "Invoice", self._open_invoice).pack(pady=10)
        SidebarIcon(leftbar, "📝", "Register", self._open_pr).pack(pady=10)
        SidebarIcon(leftbar, "🔍", "Search", self._open_search).pack(pady=10)
        SidebarIcon(leftbar, "📊", "Reports", self._open_reports).pack(pady=10)
        SidebarIcon(leftbar, "⚙️", "Admin", self._open_admin).pack(pady=10)
        try:
            self._open_dashboard()
        except Exception as e:
            try:
                messagebox.showerror("Dashboard Error", str(e))
            except Exception:
                pass
            self._open_pr()
    def _clear_content(self):
        for w in self.content.winfo_children():
            w.destroy()
    def _open_dashboard(self):
        self._clear_content()
        Dashboard(self.content, self)
    def _open_pr(self):
        self._clear_content()
        self.pr = PatientRegistration(self.content)
    def _open_search(self):
        try:
            self.pr._open_search()
        except Exception:
            win = tk.Toplevel(self)
            win.title("Search Patients")
            frm = ttk.Frame(win, padding=8)
            frm.pack(fill="both", expand=True)
            ttk.Label(frm, text="Search By").grid(row=0, column=0, padx=4, pady=4, sticky="w")
            mode = tk.StringVar(value="Mobile")
            ttk.Combobox(frm, textvariable=mode, values=["Mobile", "Registration"], state="readonly").grid(row=0, column=1, padx=4, pady=4, sticky="w")
            ttk.Label(frm, text="Query").grid(row=1, column=0, padx=4, pady=4, sticky="w")
            query = tk.StringVar()
            ttk.Entry(frm, textvariable=query, width=30).grid(row=1, column=1, padx=4, pady=4, sticky="ew")
            tv = ttk.Treeview(frm, columns=("reg_no", "name", "mobile"), show="headings", height=10)
            tv.heading("reg_no", text="Reg No")
            tv.heading("name", text="Name")
            tv.heading("mobile", text="Mobile")
            tv.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=4, pady=8)
            frm.rowconfigure(2, weight=1)
            frm.columnconfigure(1, weight=1)
            def do_search():
                q = query.get().strip()
                tv.delete(*tv.get_children())
                if not q:
                    return
                if mode.get() == "Mobile":
                    results = search_patients_by_contact(q)
                else:
                    results = search_patients_by_reg_no(q)
                for doc in results:
                    tv.insert("", "end", values=(doc.get("reg_no",""), doc.get("name",""), doc.get("contact_number","")), iid=str(doc.get("_id","")))
            ttk.Button(frm, text="🔍 Search", command=do_search, style="Icon.TButton").grid(row=1, column=2, padx=4, pady=4, sticky="w")
    def _open_invoice(self):
        try:
            if hasattr(self, "pr"):
                self.pr._open_invoice()
                return
        except Exception:
            pass
        messagebox.showinfo("Open Patient Registration", "Open Patient Registration and select a patient, then generate invoice")
    def _open_reports(self):
        win = tk.Toplevel(self)
        win.title("Reports")
        ttk.Label(win, text="Reports", padding=12).pack()
    def _open_dynamic_module(self, key: str, label: str):
        win = tk.Toplevel(self)
        win.title(label or key)
        ttk.Label(win, text=f"Module: {label or key}", padding=12).pack()
        ttk.Label(win, text="This module is registered dynamically.", padding=6).pack()
    def _open_placeholder(self, title: str):
        win = tk.Toplevel(self)
        win.title(title)
        ttk.Label(win, text=title, padding=16).pack()
    def _open_admin(self):
        self._clear_content()
        frm = ttk.Frame(self.content, padding=12)
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text="Admin", font=("Segoe UI", 14, "bold")).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0,8))
        ttk.Label(frm, text="Users").grid(row=1, column=0, sticky="w")
        users_lb = tk.Listbox(frm, height=10)
        users_lb.grid(row=2, column=0, rowspan=6, sticky="nsw")
        ttk.Label(frm, text="Username").grid(row=2, column=1, sticky="w")
        u_name = tk.StringVar()
        ttk.Entry(frm, textvariable=u_name, width=24).grid(row=2, column=2, sticky="w")
        ttk.Label(frm, text="Password").grid(row=3, column=1, sticky="w")
        u_pwd = tk.StringVar()
        ttk.Entry(frm, textvariable=u_pwd, width=24, show="*").grid(row=3, column=2, sticky="w")
        ttk.Label(frm, text="Rights").grid(row=4, column=1, sticky="w")
        rights_lb = tk.Listbox(frm, selectmode="multiple", height=6)
        rights_lb.grid(row=4, column=2, sticky="w")
        ttk.Label(frm, text="Add Custom Right").grid(row=5, column=1, sticky="w")
        custom_right = tk.StringVar()
        ttk.Entry(frm, textvariable=custom_right, width=24).grid(row=5, column=2, sticky="w")
        btns = ttk.Frame(frm)
        btns.grid(row=8, column=0, columnspan=4, sticky="e", pady=8)
        def load_users():
            users_lb.delete(0, "end")
            try:
                for u in list_users():
                    users_lb.insert("end", u.get("username",""))
            except Exception:
                pass
        def load_rights_choices():
            rights_lb.delete(0, "end")
            base = ["patient_registration", "search", "invoice", "reports", "admin"]
            try:
                for m in list_modules():
                    k = m.get("key","")
                    if k and k not in base:
                        base.append(k)
            except Exception:
                pass
            for r in base:
                rights_lb.insert("end", r)
        def on_user_select(evt=None):
            sel = users_lb.curselection()
            if not sel:
                return
            uname = users_lb.get(sel[0])
            u_name.set(uname)
            try:
                doc = get_user(uname) or {}
            except Exception:
                doc = {}
            u_pwd.set(str(doc.get("password","")))
            rights = set(doc.get("rights") or [])
            rights_lb.selection_clear(0, "end")
            for i in range(rights_lb.size()):
                val = rights_lb.get(i)
                if val in rights:
                    rights_lb.selection_set(i)
        def do_save():
            uname = u_name.get().strip()
            pwd = u_pwd.get().strip()
            if not uname or not pwd:
                messagebox.showerror("Validation Error", "Enter username and password")
                return
            rights = [rights_lb.get(i) for i in rights_lb.curselection()]
            cr = custom_right.get().strip()
            if cr:
                rights.append(cr)
                try:
                    add_module(cr, cr)
                except Exception:
                    pass
            try:
                add_or_update_user(uname, pwd, rights)
                messagebox.showinfo("Saved", f"User {uname} updated")
                load_users()
            except Exception as e:
                messagebox.showerror("Error", str(e))
        def do_delete():
            uname = u_name.get().strip()
            if not uname:
                return
            try:
                delete_user(uname)
                messagebox.showinfo("Deleted", f"User {uname} removed")
                load_users()
                u_name.set("")
                u_pwd.set("")
                rights_lb.selection_clear(0, "end")
            except Exception as e:
                messagebox.showerror("Error", str(e))
        ttk.Button(btns, text="💾 Save", command=do_save, style="Icon.TButton").pack(side="right", padx=6)
        ttk.Button(btns, text="🗑️ Delete", command=do_delete, style="Icon.TButton").pack(side="right", padx=6)
        users_lb.bind("<<ListboxSelect>>", on_user_select)
        load_users()
        load_rights_choices()
def main():
    root = tk.Tk()
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Icon.TButton", font=("Segoe UI Emoji", 12, "bold"), padding=(10, 8))
    style.configure("Tile.TButton", font=("Segoe UI Emoji", 12, "bold"), padding=(14, 14), anchor="center")
    style.configure("Invoice.TButton", font=("Segoe UI Emoji", 12, "bold"), padding=(12, 10), foreground="white", background="#2E86C1")
    style.map("Invoice.TButton", background=[("active", "#1B4F72")])
    try:
        root.configure(bg="#f4f7fb")
    except Exception:
        pass
    dlg = LoginDialog(root)
    root.wait_window(dlg)
    if not dlg.authorized:
        root.destroy()
        return
    ERPMain(root, dlg.username or "user", dlg.rights or [])
    root.geometry("900x650")
    root.mainloop()
if __name__ == "__main__":
    main()
