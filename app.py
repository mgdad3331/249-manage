from flask import Flask, render_template, request, jsonify
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os
import datetime

# =========================
# Flask App
# =========================
app = Flask(__name__)

# =========================
# Google Sheets Credentials (FROM RENDER SECRET)
# =========================
creds_json = os.environ.get("GOOGLE_CREDS_JSON")
if not creds_json:
    raise Exception("GOOGLE_CREDS_JSON environment variable not found")

creds_dict = json.loads(creds_json)

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# =========================
# Open Google Sheet
# =========================
SHEET_NAME = "Client_Management"
sheet = client.open(SHEET_NAME).sheet1

# =========================
# Admin Password
# =========================
ADMIN_PASSWORD = "Miqdad123"

# =========================
# Columns Definition
# =========================
STATIC_COLUMNS = [
    "Name", "Email", "University", "Address", "Phone", "Start Date"
]

TICK_COLUMNS = [
    "Secondary Cert",
    "Bachelor Cert",
    "Master Cert",
    "Equivalency Cert",
    "Internship Cert",
    "Documents",
    "National ID",
    "Power of Attorney",
    "Preliminary Accept",
    "Data Completion",
    "Foreign Fees",
    "Final Selection"
]

ALL_COLUMNS = STATIC_COLUMNS + TICK_COLUMNS

# =========================
# Ensure headers exist
# =========================
headers = sheet.row_values(1)
if not headers:
    sheet.append_row(ALL_COLUMNS)

# =========================
# Routes
# =========================

@app.route('/')
def index():
    data = sheet.get_all_records()
    return render_template(
        'index.html',
        clients=data,
        tick_columns=TICK_COLUMNS
    )

# =========================
# Save All Changes (Bulk Save)
# =========================
@app.route('/save', methods=['POST'])
def save():
    data = request.get_json()

    password = data.get("password")
    if password != ADMIN_PASSWORD:
        return jsonify({"status": "failed", "message": "Wrong password"})

    updates_by_row = data.get("updates", {})
    headers = sheet.row_values(1)

    for row_index, updates in updates_by_row.items():
        sheet_row = int(row_index) + 2  # sheet starts from row 2
        for col_name, value in updates.items():
            if col_name in headers:
                col_index = headers.index(col_name) + 1
                sheet.update_cell(sheet_row, col_index, value)

    return jsonify({"status": "success"})

# =========================
# Add New Client
# =========================
@app.route('/add_client', methods=['POST'])
def add_client():
    data = request.get_json()
    if data.get("password") != ADMIN_PASSWORD:
        return jsonify({"status": "failed", "message": "Wrong password"})

    name = data.get("name", "عميل جديد")
    email = data.get("email", "")
    uni = data.get("uni", "")
    phone = data.get("phone", "")
    
    # بناء الصف الجديد بالترتيب الصحيح للأعمدة
    new_row = [name, email, uni, "السودان", phone, datetime.datetime.now().strftime("%Y-%m-%d")]
    new_row += ["FALSE"] * len(TICK_COLUMNS) # الصاحات تبدأ كلها خطأ

    sheet.append_row(new_row)
    return jsonify({"status": "success"})
    
# =========================
# Run Local (Render uses Gunicorn)
# =========================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
