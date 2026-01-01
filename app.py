from flask import Flask, render_template, request, jsonify
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# إعداد Flask
app = Flask(__name__)

# إعداد Google Sheets API
scope = ["https://spreadsheets.google.com/feeds",'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)

# فتح الشيت
sheet = client.open("Client_Management").sheet1

# كلمة سر Admin
ADMIN_PASSWORD = "Miqdad123"  # ممكن تغيّرها

# أسماء الأعمدة للـ check ticks
tick_columns = [
    "Secondary Cert", "Bachelor Cert", "Master Cert", "Equivalency Cert",
    "Internship Cert", "Documents", "National ID", "Power of Attorney",
    "Preliminary Accept", "Data Completion", "Foreign Fees", "Final Selection"
]

# جميع الأعمدة
all_columns = [
    "Name", "Email", "University", "Address", "Phone", "Start Date"
] + tick_columns

# === التحقق من الأعمدة وإضافتها إذا الشيت فارغ ===
worksheet = sheet
existing_headers = worksheet.row_values(1)
if not existing_headers:
    worksheet.append_row(all_columns)
    print("Headers added to the sheet successfully!")

    # إضافة عميل تجريبي واحد (اختياري)
    demo_client = ["Ahmed Ali", "ahmed@example.com", "Cairo University", "Cairo, Egypt", "0100000000", "2026-01-01"] + ["FALSE"]*len(tick_columns)
    worksheet.append_row(demo_client)
    print("Demo client added for testing.")

# الصفحة الرئيسية
@app.route('/')
def index():
    data = sheet.get_all_records()
    return render_template('index.html', clients=data, tick_columns=tick_columns)

# تحديث Check Tick أو التفاصيل مباشرة
@app.route('/update', methods=['POST'])
def update():
    row_index = int(request.form['row_index']) + 2
    column_name = request.form['column_name']
    value = request.form['value']

    all_headers = sheet.row_values(1)
    col_index = all_headers.index(column_name) + 1
    sheet.update_cell(row_index, col_index, value)
    return jsonify({"status": "success"})

# تعديل البيانات الثابتة بعد كلمة سر
@app.route('/edit', methods=['POST'])
def edit():
    password = request.form['password']
    if password != ADMIN_PASSWORD:
        return jsonify({"status": "failed", "message": "Wrong password"})

    row_index = int(request.form['row_index']) + 2
    updates = json.loads(request.form.get('updates'))

    all_headers = sheet.row_values(1)
    for key, val in updates.items():
        col_index = all_headers.index(key) + 1
        sheet.update_cell(row_index, col_index, val)

    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(debug=True)
