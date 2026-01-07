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
sheet = client.open(SHEET_NAME).sheet1

# =========================
# Admin Password
# =========================
ADMIN_PASSWORD = "321"

# =========================
# Columns Definition (العربية المظبوطة)
# =========================
# الأعمدة ذات المرحلتين (دفع ثم اكتمال)
SPECIAL_COLUMNS = ["رقم وطني", "توثيقات", "معادلة", "توكيل", "قبول مبدئي", "تسليم الملف", "رسوم الوافدين"]

# بقية الأعمدة التي تظل "صح" عادية (مرحلة واحدة)
NORMAL_TICK_COLUMNS = ["الشهادات", "استلام الملف", "ترشيح نهائي", "172$"]

TICK_COLUMNS = SPECIAL_COLUMNS + NORMAL_TICK_COLUMNS

# =========================
# Routes
# =========================

@app.route('/')
def index():
    try:
        data = sheet.get_all_records()
        # نرسل TICK_COLUMNS لكي يعرف الـ HTML أي أعمدة يحولها لصاحات
        return render_template(
            'index.html',
            clients=data,
            tick_columns=TICK_COLUMNS
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
    headers = sheet.row_values(1)

    try:
        # نجلب كل البيانات الحالية مرة واحدة لتعديلها في الذاكرة
        all_data = sheet.get_all_values() 
        
        for row_index_str, updates in updates_by_row.items():
            row_idx = int(row_index_str) + 1 # +1 لأن المصفوفة تبدأ من 0 والعناوين في 0
            
            for col_name, value in updates.items():
                if col_name in headers:
                    col_idx = headers.index(col_name)
                    all_data[row_idx][col_idx] = value
        
        # نحدث الشيت بالكامل بطلب واحد فقط! (هذا يحمي من خطأ Quota 429)
        sheet.update('A1', all_data)
        
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
    
    # بناء الصف الجديد حسب ترتيب قوقل شيت لديك
    # ترتيبك: الاسم، البريد، الجامعة، الرغبة، العنوان، الرقم، تاريخ البدء
    now = datetime.datetime.now().strftime("%Y-%m-%d")
    new_row = [
    name,         # خانة الاسم
    email,        # خانة البريد
    uni,          # خانة الجامعة
    "لم يحدد",    # خانة الرغبة
    "",           # خانة العنوان (تركناها فارغة بدلاً من السودان)
    phone,        # خانة الرقم (الهاتف) - هنا سيصل الرقم صحيحاً
    now           # خانة البدء
]
    
    # إضافة القيم الافتراضية للصاحات (كلها FALSE في البداية)
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
