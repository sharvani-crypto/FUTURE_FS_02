"""
Client Lead Management CRM System
===================================
A full-stack Flask CRM application for managing business leads.
Author: Admin
Tech: Python Flask + JSON storage
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json
import os
import uuid
from functools import wraps

app = Flask(__name__)
app.secret_key = "crm_secret_key_2025_secure"  # Change in production

# ─── Data file paths ───────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.join(BASE_DIR, "data")
LEADS_FILE = os.path.join(DATA_DIR, "leads.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
NOTES_FILE = os.path.join(DATA_DIR, "notes.json")

# ─── Valid statuses ────────────────────────────────────────────────────────────
VALID_STATUSES = ["Contacted", "Follow-up", "Qualified", "Closed/Won"]

# ─── JSON helpers ──────────────────────────────────────────────────────────────
def read_json(filepath):
    """Read and return parsed JSON from a file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def write_json(filepath, data):
    """Write data as formatted JSON to a file."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ─── Auth decorator ────────────────────────────────────────────────────────────
def login_required(f):
    """Protect routes — redirect to login if not authenticated."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "admin" not in session:
            flash("Please log in to access the admin panel.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

# ─── Helpers ──────────────────────────────────────────────────────────────────
def get_lead_by_id(lead_id):
    """Find a single lead by its ID."""
    leads = read_json(LEADS_FILE)
    return next((l for l in leads if l["id"] == lead_id), None)

def get_notes_for_lead(lead_id):
    """Return all notes belonging to a lead, newest first."""
    notes = read_json(NOTES_FILE)
    return sorted(
        [n for n in notes if n["lead_id"] == lead_id],
        key=lambda x: x["timestamp"],
        reverse=True
    )

def dashboard_stats(leads):
    """Compute summary counts for the dashboard header."""
    stats = {
        "total": len(leads),
        "contacted": 0,
        "follow_up": 0,
        "qualified": 0,
        "closed_won": 0,
    }
    for lead in leads:
        s = lead.get("status", "")
        if s == "Contacted":   stats["contacted"]  += 1
        elif s == "Follow-up": stats["follow_up"]  += 1
        elif s == "Qualified": stats["qualified"]  += 1
        elif s == "Closed/Won":stats["closed_won"] += 1
    return stats

# ══════════════════════════════════════════════════════════════════════════════
#  PUBLIC ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    """Public contact form — simulates a website enquiry form."""
    return render_template("index.html")

@app.route("/submit-lead", methods=["POST"])
def submit_lead():
    """Save a new lead submitted from the public contact form."""
    name    = request.form.get("name", "").strip()
    email   = request.form.get("email", "").strip()
    phone   = request.form.get("phone", "").strip()
    company = request.form.get("company", "").strip()
    message = request.form.get("message", "").strip()
    source  = request.form.get("source", "Website").strip()

    # Basic validation
    if not name or not email or not message:
        flash("Name, email and message are required.", "error")
        return redirect(url_for("index"))

    new_lead = {
        "id":         f"lead_{uuid.uuid4().hex[:8]}",
        "name":       name,
        "email":      email,
        "phone":      phone,
        "company":    company,
        "message":    message,
        "source":     source,
        "status":     "Contacted",          # default status
        "created_at": datetime.now().isoformat(timespec="seconds")
    }

    leads = read_json(LEADS_FILE)
    leads.insert(0, new_lead)              # newest first
    write_json(LEADS_FILE, leads)

    flash("Your message has been sent! We will get back to you soon.", "success")
    return redirect(url_for("index"))

# ══════════════════════════════════════════════════════════════════════════════
#  AUTH ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/login", methods=["GET", "POST"])
def login():
    """Admin login page."""
    if "admin" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        users = read_json(USERS_FILE)
        user  = next((u for u in users if u["username"] == username), None)

        if user and check_password_hash(user["password"], password):
            session["admin"]      = username
            session["admin_name"] = user.get("name", "Admin")
            flash(f"Welcome back, {user.get('name', 'Admin')}!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid username or password.", "error")

    return render_template("login.html")

@app.route("/logout")
def logout():
    """Clear session and redirect to login."""
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

# ══════════════════════════════════════════════════════════════════════════════
#  ADMIN ROUTES  (all protected by @login_required)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/dashboard")
@login_required
def dashboard():
    """Main admin panel — list all leads with search & filter."""
    leads  = read_json(LEADS_FILE)
    stats  = dashboard_stats(leads)
    return render_template(
        "dashboard.html",
        leads=leads,
        stats=stats,
        statuses=VALID_STATUSES
    )

@app.route("/lead/<lead_id>")
@login_required
def lead_detail(lead_id):
    """Detail view for a single lead with notes timeline."""
    lead  = get_lead_by_id(lead_id)
    if not lead:
        flash("Lead not found.", "error")
        return redirect(url_for("dashboard"))
    notes = get_notes_for_lead(lead_id)
    return render_template(
        "lead_detail.html",
        lead=lead,
        notes=notes,
        statuses=VALID_STATUSES
    )

@app.route("/lead/<lead_id>/update-status", methods=["POST"])
@login_required
def update_status(lead_id):
    """Update the status of a lead."""
    new_status = request.form.get("status", "").strip()
    if new_status not in VALID_STATUSES:
        return jsonify({"success": False, "error": "Invalid status"}), 400

    leads = read_json(LEADS_FILE)
    updated = False
    for lead in leads:
        if lead["id"] == lead_id:
            lead["status"] = new_status
            updated = True
            break

    if updated:
        write_json(LEADS_FILE, leads)
        # If AJAX request return JSON
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": True, "status": new_status})
        flash(f"Status updated to '{new_status}'.", "success")
    else:
        flash("Lead not found.", "error")

    return redirect(url_for("lead_detail", lead_id=lead_id))

@app.route("/lead/<lead_id>/add-note", methods=["POST"])
@login_required
def add_note(lead_id):
    """Append a follow-up note to a lead."""
    note_text = request.form.get("note", "").strip()
    if not note_text:
        flash("Note cannot be empty.", "error")
        return redirect(url_for("lead_detail", lead_id=lead_id))

    lead = get_lead_by_id(lead_id)
    if not lead:
        flash("Lead not found.", "error")
        return redirect(url_for("dashboard"))

    new_note = {
        "id":        f"note_{uuid.uuid4().hex[:8]}",
        "lead_id":   lead_id,
        "note":      note_text,
        "timestamp": datetime.now().isoformat(timespec="seconds")
    }

    notes = read_json(NOTES_FILE)
    notes.append(new_note)
    write_json(NOTES_FILE, notes)

    # AJAX response
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"success": True, "note": new_note})

    flash("Note added successfully.", "success")
    return redirect(url_for("lead_detail", lead_id=lead_id))

@app.route("/lead/<lead_id>/delete", methods=["POST"])
@login_required
def delete_lead(lead_id):
    """Permanently delete a lead and its notes."""
    leads = read_json(LEADS_FILE)
    leads = [l for l in leads if l["id"] != lead_id]
    write_json(LEADS_FILE, leads)

    notes = read_json(NOTES_FILE)
    notes = [n for n in notes if n["lead_id"] != lead_id]
    write_json(NOTES_FILE, notes)

    flash("Lead deleted.", "info")
    return redirect(url_for("dashboard"))

@app.route("/analytics")
@login_required
def analytics():
    """Analytics page with Chart.js data."""
    leads = read_json(LEADS_FILE)

    # ── Status breakdown ──────────────────────────────────────────────────────
    status_counts = {s: 0 for s in VALID_STATUSES}
    for lead in leads:
        s = lead.get("status", "")
        if s in status_counts:
            status_counts[s] += 1

    # ── Source breakdown ──────────────────────────────────────────────────────
    source_counts = {}
    for lead in leads:
        src = lead.get("source", "Other")
        source_counts[src] = source_counts.get(src, 0) + 1

    # ── Leads per day (last 14 days) ─────────────────────────────────────────
    from collections import defaultdict, OrderedDict
    day_counts = defaultdict(int)
    for lead in leads:
        day = lead.get("created_at", "")[:10]   # YYYY-MM-DD
        if day:
            day_counts[day] += 1

    sorted_days  = sorted(day_counts.keys())[-14:]
    timeline_labels = sorted_days
    timeline_data   = [day_counts[d] for d in sorted_days]

    # ── Conversion rate ───────────────────────────────────────────────────────
    total      = len(leads)
    closed_won = status_counts.get("Closed/Won", 0)
    conversion = round((closed_won / total * 100) if total else 0, 1)

    stats = dashboard_stats(leads)

    return render_template(
        "analytics.html",
        stats=stats,
        status_labels=list(status_counts.keys()),
        status_data=list(status_counts.values()),
        source_labels=list(source_counts.keys()),
        source_data=list(source_counts.values()),
        timeline_labels=timeline_labels,
        timeline_data=timeline_data,
        conversion=conversion
    )

# ── API endpoint for real-time dashboard filtering ───────────────────────────
@app.route("/api/leads")
@login_required
def api_leads():
    """Return leads as JSON for client-side search/filter."""
    leads = read_json(LEADS_FILE)
    return jsonify(leads)

# ══════════════════════════════════════════════════════════════════════════════
#  SETUP HELPER  — run once to hash the default admin password
# ══════════════════════════════════════════════════════════════════════════════
def init_admin():
    """Create admin user with properly hashed password if not set."""
    users = read_json(USERS_FILE)
    for user in users:
        pw = user.get("password", "")
        # Re-hash if stored password looks like a placeholder
        if not pw.startswith("pbkdf2") and not pw.startswith("scrypt"):
            user["password"] = generate_password_hash("admin123")
    write_json(USERS_FILE, users)

# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    init_admin()   # Ensure password is hashed on first run
    print("\n✅  Client Lead Management CRM")
    print("   Running at: http://127.0.0.1:5000")
    print("   Admin panel: http://127.0.0.1:5000/login")
    print("   Login → username: admin | password: admin123\n")
    app.run(debug=True)