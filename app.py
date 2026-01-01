from flask import Flask, render_template, request, jsonify
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# إعداد Flask
app = Flask(__name__)

# إعداد Google Sheets API
scope = ["https://spreadsheets.google.com/feeds",'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)

sheet = client.open("Client_Management").sheet1

# كلمة سر Admin
ADMIN_PASSWORD = "Miqdad123"  # ممكن تغيّرها

# أسماء الأعمدة للـ check ticks
tick_columns = [
    "Secondary Cert", "Bachelor Cert", "Master Cert", "Equivalency Cert",
    "Internship Cert", "Documents", "National ID", "Power of Attorney",
    "Preliminary Accept", "Data Completion", "Foreign Fees", "Final Selection"
]

# الصفحة الرئيسية
@app.route('/')
def index():
    data = sheet.get_all_records()
    return render_template('index.html', clients=data, tick_columns=tick_columns)

# تحديث Check Tick أو التفاصيل
@app.route('/update', methods=['POST'])
def update():
    row_index = int(request.form['row_index']) + 2  # +2 بسبب 0-index و header
    column_name = request.form['column_name']
    value = request.form['value']

    # البحث عن رقم العمود في Sheet
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
    updates = request.form.get('updates')  # dict JSON
    import json
    updates = json.loads(updates)

    all_headers = sheet.row_values(1)
    for key, val in updates.items():
        col_index = all_headers.index(key) + 1
        sheet.update_cell(row_index, col_index, val)

    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(debug=True)
