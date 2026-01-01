from flask import Flask, render_template, request, jsonify
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os

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
# Auto-create headers if missing
# =========================
headers = sheet.row_values(1)
if not headers:
    sheet.append_row(ALL_COLUMNS)

    # Add demo client (optional – useful for first run)
    demo_client = [
        "Ahmed Ali",
        "ahmed@example.com",
        "Cairo University",
        "Cairo, Egypt",
        "0100000000",
        "2026-01-01"
    ] + ["FALSE"] * len(TICK_COLUMNS)

    sheet.append_row(demo_client)

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

@app.route('/update', methods=['POST'])
def update():
    row_index = int(request.form['row_index']) + 2
    column_name = request.form['column_name']
    value = request.form['value']

    headers = sheet.row_values(1)
    col_index = headers.index(column_name) + 1

    sheet.update_cell(row_index, col_index, value)
    return jsonify({"status": "success"})

@app.route('/edit', methods=['POST'])
def edit():
    password = request.form['password']
    if password != ADMIN_PASSWORD:
        return jsonify({"status": "failed", "message": "Wrong password"})

    row_index = int(request.form['row_index']) + 2
    updates = json.loads(request.form['updates'])

    headers = sheet.row_values(1)

    for key, value in updates.items():
        col_index = headers.index(key) + 1
        sheet.update_cell(row_index, col_index, value)

    return jsonify({"status": "success"})

# =========================
# Run Local (Render uses Gunicorn)
# =========================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
