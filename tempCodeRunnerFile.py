from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///complaints.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")
db = SQLAlchemy(app)

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100), nullable=True)
    location = db.Column(db.String(150), nullable=True)
    status = db.Column(db.String(20), default="Pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
# database creation
with app.app_context():
    db.create_all()

def is_admin():
    return session.get("is_admin") is True

@app.route("/")
def home():
    return redirect(url_for("submit_complaint"))

@app.route("/submit", methods=["GET", "POST"])
def submit_complaint():
    if request.method == "POST":
        data = {k: request.form.get(k, "").strip() for k in ["name", "email", "role", "title", "description", "category", "location"]}
        if not all([data["name"], data["email"], data["title"], data["description"]]):
            flash("Please fill all required fields / कृपया सभी आवश्यक विवरण भरें", "error")
            return redirect(url_for("submit_complaint"))
        db.session.add(Complaint(**data))
        db.session.commit()
        flash("Complaint submitted successfully! / शिकायत दर्ज हो गई", "success")
        return redirect(url_for("list_complaints"))
    return render_template("submit.html")

@app.route("/complaints")
def list_complaints():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    role = request.args.get("role", "")
    query = Complaint.query
    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(Complaint.title.ilike(like), Complaint.description.ilike(like), Complaint.location.ilike(like))
        )
    if status:
        query = query.filter_by(status=status)
    if role:
        query = query.filter_by(role=role)
    complaints = query.order_by(Complaint.created_at.desc()).all()
    return render_template("list.html", complaints=complaints, is_admin=is_admin())

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["is_admin"] = True
            flash("Logged in as admin", "success")
            return redirect(url_for("admin_dashboard"))
        flash("Invalid password", "error")
    return render_template("admin_login.html")

@app.route("/admin/logout")
def admin_logout():
    session.pop("is_admin", None)
    flash("Logged out", "info")
    return redirect(url_for("home"))

@app.route("/admin")
def admin_dashboard():
    if not is_admin():
        flash("Admin login required", "error")
        return redirect(url_for("admin_login"))
    complaints = Complaint.query.order_by(Complaint.created_at.desc()).all()
    return render_template("admin_dashboard.html", complaints=complaints)

@app.route("/admin/update/<int:complaint_id>", methods=["POST"])
def admin_update(complaint_id):
    if not is_admin():
        flash("Admin login required", "error")
        return redirect(url_for("admin_login"))
    c = Complaint.query.get_or_404(complaint_id)
    c.status = request.form.get("status", "Pending")
    db.session.commit()
    flash(f"Status updated to {c.status}", "success")
    return redirect(url_for("admin_dashboard"))

if __name__ == "__main__":
    app.run(debug=True)
