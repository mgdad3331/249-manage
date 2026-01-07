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
# Google Sheets Credentials
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
spreadsheet = client.open(SHEET_NAME)
sheet = spreadsheet.sheet1

# =========================
# نظام حفظ مبالغ الترس (Settings)
# =========================
try:
    # محاولة فتح ورقة الإعدادات، إذا لم توجد سيتم إنشاؤها تلقائياً
    try:
        settings_sheet = spreadsheet.worksheet("Settings")
    except gspread.exceptions.WorksheetNotFound:
        settings_sheet = spreadsheet.add_worksheet(title="Settings", rows="20", cols="2")
        # إدخال القيم الافتراضية لأول مرة فقط
        default_fees = [
            ["الخدمة", "المبلغ"],
            ["رقم وطني", 3500],
            ["توثيقات", 5500],
            ["معادلة", 0],
            ["توكيل", 3500],
            ["قبول مبدئي", 0],
            ["تسليم الملف", 0],
            ["رسوم الوافدين", 0]
        ]
        settings_sheet.update('A1', default_fees)

    def get_fees_from_db():
        """جلب الرسوم من ورقة Settings وتحويلها لقاموس"""
        records = settings_sheet.get_all_records()
        return {row["الخدمة"]: row["المبلغ"] for row in records}

except Exception as e:
    print(f"Settings Initialization Error: {e}")
    # في حال حدوث خطأ، نستخدم قيم افتراضية لكي لا يتوقف النظام
    def get_fees_from_db():
        return {"رقم وطني": 3500, "توثيقات": 5500, "معادلة": 0, "توكيل": 3500, "قبول مبدئي": 0, "تسليم الملف": 0, "رسوم الوافدين": 0}

# =========================
# Admin Password
# =========================
ADMIN_PASSWORD = "321"

# =========================
# Columns Definition (العربية المظبوطة)
# =========================
SPECIAL_COLUMNS = ["رقم وطني", "توثيقات", "معادلة", "توكيل", "قبول مبدئي", "تسليم الملف", "رسوم الوافدين"]
NORMAL_TICK_COLUMNS = ["الشهادات", "استلام الملف", "ترشيح نهائي", "172$"]
TICK_COLUMNS = SPECIAL_COLUMNS + NORMAL_TICK_COLUMNS

# =========================
# Routes
# =========================

@app.route('/')
def index():
    try:
        data = sheet.get_all_records()
        # جلب المبالغ الحقيقية من صفحة Settings بدلاً من الكود الثابت
        current_fees = get_fees_from_db()
        
        return render_template(
            'index.html',
            clients=data,
            tick_columns=TICK_COLUMNS,
            fees=current_fees  # نرسل الرسوم لملف HTML
        )
    except Exception as e:
        return f"Error: {str(e)}"

# =========================
# Save All Changes (Bulk Save)
# =========================
@app.route('/save', methods=['POST'])
def save():
    data = request.get_json()
    password = data.get("password")
    if password != ADMIN_PASSWORD:
        return jsonify({"status": "failed", "message": "كلمة السر خاطئة"})

    updates_by_row = data.get("updates", {})
    new_fees = data.get("fees") # استقبال مبالغ الترس الجديدة من المتصفح
    headers = sheet.row_values(1)

    try:
        # 1. تحديث بيانات العملاء في Sheet1
        all_data = sheet.get_all_values() 
        
        for row_index_str, updates in updates_by_row.items():
            row_idx = int(row_index_str) + 1 
            
            for col_name, value in updates.items():
                if col_name in headers:
                    col_idx = headers.index(col_name)
                    all_data[row_idx][col_idx] = value
        
        sheet.update('A1', all_data)

        # 2. تحديث مبالغ الترس في ورقة Settings (هنا يتم الحفظ الدائم)
        if new_fees:
            fees_data = [["الخدمة", "المبلغ"]]
            for service_name, amount in new_fees.items():
                fees_data.append([service_name, amount])
            settings_sheet.update('A1', fees_data)
        
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "failed", "message": f"خطأ في الحفظ: {str(e)}"})

# =========================
# Add New Client
# =========================
@app.route('/add_client', methods=['POST'])
def add_client():
    data = request.get_json()
    if data.get("password") != ADMIN_PASSWORD:
        return jsonify({"status": "failed", "message": "كلمة السر خاطئة"})

    name = data.get("name", "عميل جديد")
    email = data.get("email", "")
    uni = data.get("uni", "")
    phone = data.get("phone", "")
    
    now = datetime.datetime.now().strftime("%Y-%m-%d")
    new_row = [
        name,      # خانة الاسم
        email,     # خانة البريد
        uni,       # خانة الجامعة
        "لم يحدد", # خانة الرغبة
        "",        # خانة العنوان
        phone,     # خانة الرقم
        now        # خانة البدء
    ]
    
    new_row += ["FALSE"] * len(TICK_COLUMNS)

    try:
        sheet.append_row(new_row)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "failed", "message": str(e)})

# =========================
# Run Local
# =========================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
