import io
import os
import re
import secrets
from functools import wraps

import pandas as pd
import requests
from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template_string, request, session, url_for
from sqlalchemy import func
from werkzeug.security import check_password_hash, generate_password_hash

from models import Pin, Result, School, Student, db

load_dotenv()
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-me-in-production")
database_url = os.getenv("DATABASE_URL", "sqlite:///results.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

with app.app_context():
    db.create_all()

BASE = """
<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>
<title>{{ title }} - Result Checker</title><style>
body{font-family:Arial,sans-serif;max-width:1100px;margin:30px auto;padding:0 16px;background:#f5f7fb;color:#172033}nav{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:24px}a,button{color:#0757a5}a{font-weight:600}.card{background:white;padding:20px;margin:14px 0;border-radius:10px;box-shadow:0 2px 8px #0001}input,select{padding:10px;width:100%;margin:5px 0 12px;box-sizing:border-box}button{padding:10px 15px;border:0;border-radius:6px;background:#0757a5;color:#fff;cursor:pointer}.danger{color:#a00}.flash{padding:10px;background:#fff3cd;margin:8px 0}table{width:100%;border-collapse:collapse;background:#fff}td,th{padding:9px;border:1px solid #ddd;text-align:left}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:15px}.pin{font-size:2.2em;font-weight:bold;letter-spacing:4px;color:#0757a5}.muted{color:#667085}
</style></head><body><nav><a href='{{ url_for("home") }}'>Home</a>{% if session.get('school_id') %}<a href='{{ url_for("school_dashboard") }}'>School dashboard</a><a href='{{ url_for("school_logout") }}'>School logout</a>{% else %}<a href='{{ url_for("school_login") }}'>School login</a>{% endif %}{% if session.get('admin') %}<a href='{{ url_for("superadmin_dashboard") }}'>Superadmin</a><a href='{{ url_for("superadmin_logout") }}'>Admin logout</a>{% endif %}</nav>{% with messages=get_flashed_messages() %}{% for message in messages %}<div class=flash>{{ message }}</div>{% endfor %}{% endwith %}{{ body|safe }}</body></html>
"""

def page(title, body, **context):
    return render_template_string(BASE, title=title, body=render_template_string(body, **context), **context)

def school_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("school_id"):
            return redirect(url_for("school_login"))
        return view(*args, **kwargs)
    return wrapped

def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("superadmin_login"))
        return view(*args, **kwargs)
    return wrapped

def slugify(name):
    value = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "school"
    base, number = value, 2
    while School.query.filter_by(slug=value).first():
        value = f"{base}-{number}"; number += 1
    return value

def number(value):
    try: return float(value or 0)
    except (TypeError, ValueError): return 0

@app.route("/")
def home():
    schools = School.query.filter_by(is_approved=True).order_by(School.name).all()
    search = request.args.get("q", "").strip().lower()
    if search: schools = [s for s in schools if search in s.name.lower()]
    return page("Schools", """<h1>Check a school result</h1><form><input name=q value='{{ request.args.get("q", "") }}' placeholder='Search schools'><button>Search</button></form><div class=grid>{% for school in schools %}<div class=card><h2>{{ school.name }}</h2><a href='{{ url_for("school_public", slug=school.slug) }}'>Open school</a></div>{% else %}<p>No approved schools found.</p>{% endfor %}</div>""", schools=schools)

@app.route("/school/register", methods=["GET", "POST"])
def school_register():
    if request.method == "POST":
        name, email, password = request.form.get("name", "").strip(), request.form.get("email", "").strip().lower(), request.form.get("password", "")
        if not name or not email or len(password) < 6: flash("Name, email and a password of at least 6 characters are required.")
        elif School.query.filter_by(email=email).first(): flash("That email is already registered.")
        else:
            db.session.add(School(name=name, slug=slugify(name), email=email, password_hash=generate_password_hash(password)))
            db.session.commit(); flash("Registration submitted. A superadmin must approve your school."); return redirect(url_for("school_login"))
    return page("School registration", """<h1>Register school</h1><form method=post><label>Name<input name=name required></label><label>Email<input type=email name=email required></label><label>Password<input type=password name=password minlength=6 required></label><button>Register</button></form>""")

@app.route("/school/login", methods=["GET", "POST"])
def school_login():
    if request.method == "POST":
        school = School.query.filter_by(email=request.form.get("email", "").strip().lower()).first()
        if school and check_password_hash(school.password_hash, request.form.get("password", "")):
            if not school.is_approved: flash("Your school is awaiting approval.")
            else: session.clear(); session["school_id"] = school.id; return redirect(url_for("school_dashboard"))
        else: flash("Invalid email or password.")
    return page("School login", """<h1>School login</h1><form method=post><input type=email name=email placeholder=Email required><input type=password name=password placeholder=Password required><button>Login</button></form><a href='{{ url_for("school_register") }}'>Register a school</a>""")

@app.route("/school/logout")
def school_logout(): session.clear(); return redirect(url_for("home"))

@app.route("/school/dashboard", methods=["GET", "POST"])
@school_required
def school_dashboard():
    school = db.session.get(School, session["school_id"])
    if request.method == "POST":
        action = request.form.get("action")
        if action == "student":
            reg, name, cls = request.form.get("reg_number", "").strip(), request.form.get("full_name", "").strip(), request.form.get("class_name", "").strip()
            if reg and name and cls and not Student.query.filter_by(school_id=school.id, reg_number=reg).first(): db.session.add(Student(school_id=school.id, reg_number=reg, full_name=name, class_name=cls)); db.session.commit(); flash("Student added.")
            else: flash("Complete all fields and use a unique registration number.")
        elif action == "excel":
            file = request.files.get("file")
            if not file or not file.filename: flash("Choose an Excel file.")
            else:
                try:
                    frame = pd.read_excel(io.BytesIO(file.read())); frame.columns = [str(c).strip().lower() for c in frame.columns]
                    required = {"reg_number","full_name","class_name","subject","ca1","ca2","exam"}
                    if not required.issubset(frame.columns): raise ValueError("Required columns: " + ", ".join(sorted(required)))
                    for row in frame.to_dict("records"):
                        reg = str(row["reg_number"]).strip(); student = Student.query.filter_by(school_id=school.id, reg_number=reg).first()
                        if not student: student = Student(school_id=school.id, reg_number=reg, full_name=str(row["full_name"]).strip(), class_name=str(row["class_name"]).strip()); db.session.add(student); db.session.flush()
                        ca1, ca2, exam = number(row["ca1"]), number(row["ca2"]), number(row["exam"]); db.session.add(Result(student_id=student.id, subject=str(row["subject"]).strip(), ca1=ca1, ca2=ca2, exam=exam, total=ca1+ca2+exam))
                    db.session.commit(); flash("Excel results uploaded.")
                except Exception as exc: db.session.rollback(); flash(f"Upload failed: {exc}")
    students = Student.query.filter_by(school_id=school.id).order_by(Student.full_name).all(); sold = Pin.query.filter_by(school_id=school.id, is_paid=True).count()
    return page("School dashboard", """<h1>{{ school.name }}</h1><p>Balance owed: ₦{{ school.balance }} | Paid PINs sold: {{ sold }}</p><div class=grid><div class=card><h2>Add student</h2><form method=post><input type=hidden name=action value=student><input name=reg_number placeholder='Registration number' required><input name=full_name placeholder='Full name' required><input name=class_name placeholder='Class' required><button>Add</button></form></div><div class=card><h2>Upload Excel</h2><p class=muted>reg_number, full_name, class_name, subject, ca1, ca2, exam</p><form method=post enctype=multipart/form-data><input type=hidden name=action value=excel><input type=file name=file accept='.xlsx,.xls' required><button>Upload</button></form></div></div><h2>Students and results</h2><table><tr><th>Reg. no.</th><th>Name</th><th>Class</th><th>Results</th></tr>{% for student in students %}<tr><td>{{ student.reg_number }}</td><td>{{ student.full_name }}</td><td>{{ student.class_name }}</td><td>{% for result in student.results %}{{ result.subject }}: {{ result.total }}{% if not loop.last %}, {% endif %}{% endfor %}</td></tr>{% endfor %}</table>""", school=school, students=students, sold=sold)

@app.route("/s/<slug>")
def school_public(slug):
    school = School.query.filter_by(slug=slug, is_approved=True).first_or_404()
    return page(school.name, """<div class=card><h1>{{ school.name }}</h1><p><a href='{{ url_for("buy_pin", slug=school.slug) }}'><button>Buy PIN - ₦500</button></a></p><p><a href='{{ url_for("check_result", slug=school.slug) }}'>Check result</a></p></div>""", school=school)

@app.route("/s/<slug>/buy-pin")
def buy_pin(slug):
    school = School.query.filter_by(slug=slug, is_approved=True).first_or_404()
    return page("Buy PIN", """<h1>Buy a result PIN for {{ school.name }}</h1><p>Amount: ₦500</p><button onclick='pay()'>Pay with Paystack</button><script src='https://js.paystack.co/v1/inline.js'></script><script>function pay(){PaystackPop.setup({key:{{ public_key|tojson }},email:prompt('Parent email'),amount:50000,ref:'result-'+Date.now()+'-'+Math.random().toString(36).slice(2),callback:function(r){location='{{ url_for("verify_payment", reference="REFERENCE") }}'.replace('REFERENCE',r.reference)+'?school_id={{ school.id }}';}}).openIframe();}</script>""", school=school, public_key=os.getenv("PAYSTACK_PUBLIC_KEY", ""))

@app.route("/verify-payment/<reference>")
def verify_payment(reference):
    school = db.session.get(School, request.args.get("school_id", type=int))
    if not school: return "Invalid school", 400
    existing = Pin.query.filter_by(payment_reference=reference).first()
    if existing: return page("Your PIN", "<div class=card><h1>Your PIN is <span class=pin>{{ pin }}</span></h1><p>Copy it and check result now.</p></div>", pin=existing.code)
    response = requests.get(f"https://api.paystack.co/transaction/verify/{reference}", headers={"Authorization": f"Bearer {os.getenv('PAYSTACK_SECRET_KEY', '')}"}, timeout=20)
    data = response.json() if response.ok else {}
    if not data.get("status") or data.get("data", {}).get("status") != "success": return page("Payment", "<div class=card><h1>Payment could not be verified.</h1><a href='{{ url_for("school_public", slug=school.slug) }}'>Try again</a></div>", school=school), 400
    code = secrets.token_hex(4).upper(); pin = Pin(code=code, school_id=school.id, is_paid=True, is_used=False, payment_reference=reference); school.balance += 200; db.session.add(pin); db.session.commit()
    return page("Your PIN", "<div class=card><h1>Your PIN is <span class=pin>{{ pin.code }}</span></h1><p>Copy it and check result now.</p><a href='{{ url_for("check_result", slug=school.slug) }}'>Check result</a></div>", pin=pin, school=school)

@app.route("/s/<slug>/check", methods=["GET", "POST"])
def check_result(slug):
    school = School.query.filter_by(slug=slug, is_approved=True).first_or_404(); student = None
    if request.method == "POST":
        code, reg = request.form.get("pin", "").strip().upper(), request.form.get("reg_number", "").strip()
        pin = Pin.query.filter_by(code=code, school_id=school.id, is_used=False).first()
        if not pin: flash("Invalid PIN for this school.")
        else:
            student = Student.query.filter_by(reg_number=reg, school_id=school.id).first()
            if not student: flash("Student not found for this school.")
            else: pin.is_used = True; db.session.commit(); return page("Result", "<h1>{{ student.full_name }}</h1><p>{{ student.reg_number }} | {{ student.class_name }}</p><table><tr><th>Subject</th><th>CA1</th><th>CA2</th><th>Exam</th><th>Total</th></tr>{% for r in student.results %}<tr><td>{{ r.subject }}</td><td>{{ r.ca1 }}</td><td>{{ r.ca2 }}</td><td>{{ r.exam }}</td><td>{{ r.total }}</td></tr>{% endfor %}</table>", student=student)
    return page("Check result", "<h1>Check {{ school.name }} result</h1><form method=post><input name=reg_number placeholder='Registration number' required><input name=pin placeholder='PIN' required><button>Check result</button></form>", school=school)

@app.route("/superadmin/login", methods=["GET", "POST"])
def superadmin_login():
    if request.method == "POST" and request.form.get("email", "").strip().lower() == os.getenv("ADMIN_EMAIL", "").lower() and request.form.get("password", "") == os.getenv("ADMIN_PASSWORD", ""):
        session.clear(); session["admin"] = True; return redirect(url_for("superadmin_dashboard"))
    if request.method == "POST": flash("Invalid admin credentials.")
    return page("Superadmin login", "<h1>Superadmin login</h1><form method=post><input type=email name=email required><input type=password name=password required><button>Login</button></form>")

@app.route("/superadmin/logout")
def superadmin_logout(): session.clear(); return redirect(url_for("home"))

@app.route("/superadmin/dashboard", methods=["GET", "POST"])
@admin_required
def superadmin_dashboard():
    if request.method == "POST":
        school = db.session.get(School, request.form.get("school_id", type=int))
        if school:
            if request.form.get("action") == "approve": school.is_approved = True
            elif request.form.get("action") == "paid": school.balance = 0
            db.session.commit()
    schools = School.query.order_by(School.created_at.desc()).all()
    return page("Superadmin", "<h1>Schools</h1><table><tr><th>Name</th><th>Email</th><th>Approved</th><th>Balance owed</th><th>PINs sold</th><th>Actions</th></tr>{% for s in schools %}<tr><td>{{ s.name }}</td><td>{{ s.email }}</td><td>{{ s.is_approved }}</td><td>₦{{ s.balance }}</td><td>{{ s.pins|selectattr('is_paid')|list|length }}</td><td><form method=post style='display:inline'><input type=hidden name=school_id value={{ s.id }}><button name=action value=approve>Approve</button></form><form method=post style='display:inline'><input type=hidden name=school_id value={{ s.id }}><button name=action value=paid>Mark as Paid</button></form></td></tr>{% endfor %}</table>", schools=schools)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=os.getenv("RENDER", "false").lower() != "true")
