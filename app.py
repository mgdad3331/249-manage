from flask import Flask, render_template, request, jsonify
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os
import datetime
from functools import lru_cache
import logging
import hashlib
import secrets
import re

# =========================
# Flask App Configuration
# =========================
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', secrets.token_hex(32))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =========================
# Security Configuration
# =========================
class SecurityManager:
    @staticmethod
    def get_admin_password():
        password = os.environ.get("ADMIN_PASSWORD")
        if not password:
            logger.warning("⚠️ ADMIN_PASSWORD not set, using default (INSECURE!)")
            return "321"
        return password

    @staticmethod
    def verify_password(provided_password):
        return provided_password == SecurityManager.get_admin_password()

    @staticmethod
    def log_action(action, user_ip, success=True):
        status = "✅ SUCCESS" if success else "❌ FAILED"
        logger.info(f"{status} | Action: {action} | IP: {user_ip}")

# =========================
# Google Sheets Credentials
# =========================
def initialize_google_sheets():
    try:
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
        logger.info("✅ Google Sheets connection initialized successfully")
        return client
    except Exception as e:
        logger.error(f"❌ Failed to initialize Google Sheets: {str(e)}")
        raise

client = initialize_google_sheets()

SHEET_NAME = os.environ.get("SHEET_NAME", "Client_Management")
spreadsheet = client.open(SHEET_NAME)
sheet = spreadsheet.sheet1

# =========================
# ✅ جديد: الأعمدة التي لها ملاحظات إجراءات منفصلة
# اسم عمود الملاحظة = "ملاحظات_" + اسم العمود الأصلي
# =========================
PROCEDURE_NOTE_COLUMNS = ["استلام الملف", "توثيقات", "معادلة"]

def get_procedure_note_col_name(col):
    """اسم عمود الملاحظة في الشيت"""
    return f"ملاحظات_{col}"

# =========================
# Settings Sheet Management
# =========================
def initialize_settings_sheet():
    try:
        try:
            settings_sheet = spreadsheet.worksheet("Settings")
            logger.info("✅ Settings sheet found")
        except gspread.exceptions.WorksheetNotFound:
            logger.info("⚠️ Settings sheet not found, creating new one...")
            settings_sheet = spreadsheet.add_worksheet(title="Settings", rows="20", cols="2")
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
            logger.info("✅ Settings sheet created with default values")
        return settings_sheet
    except Exception as e:
        logger.error(f"❌ Settings sheet initialization error: {str(e)}")
        return None

settings_sheet = initialize_settings_sheet()

# =========================
# Fee Database Functions
# =========================
@lru_cache(maxsize=1)
def get_fees_from_db_cached():
    try:
        if settings_sheet is None:
            return get_default_fees()
        records = settings_sheet.get_all_records()
        fees = {row["الخدمة"]: row["المبلغ"] for row in records}
        return fees
    except Exception as e:
        logger.error(f"❌ Error loading fees: {str(e)}")
        return get_default_fees()

def get_default_fees():
    return {
        "رقم وطني": 3500,
        "توثيقات": 5500,
        "معادلة": 0,
        "توكيل": 3500,
        "قبول مبدئي": 0,
        "تسليم الملف": 0,
        "رسوم الوافدين": 0
    }

def clear_fees_cache():
    get_fees_from_db_cached.cache_clear()

# =========================
# Columns Definition
# =========================
SPECIAL_COLUMNS = ["رقم وطني", "توثيقات", "معادلة", "توكيل", "قبول مبدئي", "تسليم الملف", "رسوم الوافدين"]
NORMAL_TICK_COLUMNS = ["الشهادات", "استلام الملف", "ترشيح نهائي", "172$"]
TICK_COLUMNS = SPECIAL_COLUMNS + NORMAL_TICK_COLUMNS

DOLLAR_RATE = 50

# =========================
# ✅ جديد: دالة لضمان وجود أعمدة الملاحظات في الشيت
# =========================
def ensure_procedure_note_columns(headers, all_data):
    """
    تفحص أعمدة ملاحظات الإجراءات وتضيفها إذا لم تكن موجودة.
    تُضاف بجانب عمودها الأصلي مباشرة.
    """
    modified = False
    for proc_col in PROCEDURE_NOTE_COLUMNS:
        note_col = get_procedure_note_col_name(proc_col)
        if note_col not in headers:
            # إيجاد موقع العمود الأصلي وإضافة عمود الملاحظة بعده
            if proc_col in headers:
                insert_idx = headers.index(proc_col) + 1
            else:
                insert_idx = len(headers)

            headers.insert(insert_idx, note_col)
            # إضافة خلية فارغة لكل صف
            for row in all_data[1:]:
                row.insert(insert_idx, "")
            
            logger.info(f"✅ أضفت عمود: {note_col}")
            modified = True
    return modified

# =========================
# Routes
# =========================

@app.route('/')
def index():
    try:
        logger.info("📊 Loading main page...")
        data = sheet.get_all_records()
        logger.info(f"✅ Loaded {len(data)} client records")
        current_fees = get_fees_from_db_cached()
        return render_template(
            'index.html',
            clients=data,
            tick_columns=TICK_COLUMNS,
            fees=current_fees,
            procedure_note_columns=PROCEDURE_NOTE_COLUMNS  # ✅ جديد: نمررها للـ template
        )
    except Exception as e:
        logger.error(f"❌ Error loading index page: {str(e)}")
        return f"حدث خطأ في تحميل الصفحة: {str(e)}", 500


@app.route('/verify_password', methods=['POST'])
def verify_password():
    try:
        data = request.get_json()
        password = data.get("password")
        user_ip = request.remote_addr
        if SecurityManager.verify_password(password):
            SecurityManager.log_action("PASSWORD_VERIFY_SUCCESS", user_ip, success=True)
            return jsonify({"status": "success", "message": "كلمة السر صحيحة"})
        else:
            SecurityManager.log_action("PASSWORD_VERIFY_FAILED", user_ip, success=False)
            return jsonify({"status": "failed", "message": "كلمة السر خاطئة"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/get_clients', methods=['GET'])
def get_clients():
    try:
        data = sheet.get_all_records()
        client_names = [c.get('الاسم', '') for c in data if c.get('الاسم')]
        return jsonify({"status": "success", "clients": client_names})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/get_custom_fees', methods=['GET'])
def get_custom_fees():
    try:
        try:
            custom_fees_sheet = spreadsheet.worksheet("CustomFees")
            records = custom_fees_sheet.get_all_records()
            custom_fees = {}
            for row in records:
                service = row.get('الخدمة', '')
                c = row.get('العميل', '')
                amount = row.get('المبلغ', 0)
                if service and c:
                    if service not in custom_fees:
                        custom_fees[service] = {}
                    custom_fees[service][c] = amount
            return jsonify({"status": "success", "customFees": custom_fees})
        except gspread.exceptions.WorksheetNotFound:
            return jsonify({"status": "success", "customFees": {}})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# =========================
# ✅ جديد: جلب ملاحظة إجراء محدد لعميل محدد
# =========================
@app.route('/get_procedure_note', methods=['POST'])
def get_procedure_note():
    """
    جلب ملاحظة إجراء محدد (استلام الملف / توثيقات / معادلة) لعميل بعينه
    Input: { row_index: 0, col_name: "استلام الملف" }
    Output: { status: "success", note: "النص المحفوظ" }
    """
    try:
        data = request.get_json()
        row_index = int(data.get("row_index", 0))
        col_name = data.get("col_name", "")

        if col_name not in PROCEDURE_NOTE_COLUMNS:
            return jsonify({"status": "error", "message": "عمود غير مسموح"})

        note_col_name = get_procedure_note_col_name(col_name)
        
        all_data = sheet.get_all_values()
        headers = all_data[0]

        if note_col_name not in headers:
            # العمود غير موجود بعد، يعني الملاحظة فارغة
            return jsonify({"status": "success", "note": ""})

        col_idx = headers.index(note_col_name)
        data_row_idx = row_index + 1  # +1 للهيدر

        if data_row_idx >= len(all_data):
            return jsonify({"status": "success", "note": ""})

        row_data = all_data[data_row_idx]
        note = row_data[col_idx] if col_idx < len(row_data) else ""

        logger.info(f"✅ جلب ملاحظة [{note_col_name}] للصف {row_index}")
        return jsonify({"status": "success", "note": note})

    except Exception as e:
        logger.error(f"❌ get_procedure_note error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


# =========================
# ✅ جديد: حفظ ملاحظة إجراء محدد لعميل محدد
# =========================
@app.route('/save_procedure_note', methods=['POST'])
def save_procedure_note():
    """
    حفظ ملاحظة إجراء في عمود مخصص في الشيت
    Input: { password: "...", row_index: 0, col_name: "استلام الملف", note: "النص" }
    """
    try:
        data = request.get_json()
        password = data.get("password", "")
        row_index = int(data.get("row_index", 0))
        col_name = data.get("col_name", "")
        note_text = data.get("note", "")
        user_ip = request.remote_addr

        # التحقق من كلمة السر
        if not SecurityManager.verify_password(password):
            SecurityManager.log_action("SAVE_PROCEDURE_NOTE_FAILED_AUTH", user_ip, success=False)
            return jsonify({"status": "failed", "message": "كلمة السر خاطئة"})

        if col_name not in PROCEDURE_NOTE_COLUMNS:
            return jsonify({"status": "error", "message": "عمود غير مسموح"})

        note_col_name = get_procedure_note_col_name(col_name)

        # جلب كل البيانات
        all_data = sheet.get_all_values()
        headers = list(all_data[0])

        # ضمان وجود العمود
        if note_col_name not in headers:
            # أضف العمود بجانب عمود الإجراء
            if col_name in headers:
                insert_idx = headers.index(col_name) + 1
            else:
                insert_idx = len(headers)

            headers.insert(insert_idx, note_col_name)
            for i in range(1, len(all_data)):
                all_data[i] = list(all_data[i])
                all_data[i].insert(insert_idx, "")
            
            # تحديث الهيدر في الشيت أولاً
            all_data[0] = headers
            sheet.update('A1', all_data)
            logger.info(f"✅ أنشأت عمود جديد: {note_col_name}")
            # إعادة جلب البيانات بعد الإنشاء
            all_data = sheet.get_all_values()
            headers = list(all_data[0])

        col_idx = headers.index(note_col_name)
        data_row_idx = row_index + 1  # +1 للهيدر

        # تحويل رقم العمود لحرف الشيت (A=1, B=2, ...)
        col_letter = col_index_to_letter(col_idx + 1)
        sheet_row = data_row_idx + 1  # gspread يبدأ من 1
        cell_ref = f"{col_letter}{sheet_row}"

        sheet.update(cell_ref, [[note_text]])

        SecurityManager.log_action(f"SAVE_PROCEDURE_NOTE [{col_name}] row={row_index}", user_ip, success=True)
        logger.info(f"✅ حُفظت ملاحظة [{note_col_name}] في {cell_ref}")
        return jsonify({"status": "success"})

    except Exception as e:
        logger.error(f"❌ save_procedure_note error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


def col_index_to_letter(n):
    """تحويل رقم العمود (1-based) لحرف الشيت"""
    result = ""
    while n > 0:
        n -= 1
        result = chr(65 + n % 26) + result
        n //= 26
    return result


# =========================
# Save All Changes
# =========================
@app.route('/save', methods=['POST'])
def save():
    try:
        data = request.get_json()
        password = data.get("password")
        user_ip = request.remote_addr

        if not SecurityManager.verify_password(password):
            return jsonify({"status": "failed", "message": "كلمة السر خاطئة"})

        updates_by_row = data.get("updates", {})
        new_fees = data.get("fees")
        custom_fees = data.get("customFees", {})

        all_data = sheet.get_all_values()
        headers = list(all_data[0])
        for i in range(1, len(all_data)):
            all_data[i] = list(all_data[i])

        # ضمان أعمدة الحسابات
        for col_name in ["إجمالي دولار ($)", "جملة المطلوب", "جملة المتبقي"]:
            if col_name not in headers:
                headers.append(col_name)
                for r in all_data[1:]:
                    r.append("0")

        # ضمان أعمدة ملاحظات الإجراءات
        ensure_procedure_note_columns(headers, all_data)
        all_data[0] = headers

        BASE_FEES = 28500

        if updates_by_row:
            for row_index_str, updates in updates_by_row.items():
                row_idx = int(row_index_str) + 1
                if row_idx < len(all_data):
                    # امتداد الصف إذا لزم
                    while len(all_data[row_idx]) < len(headers):
                        all_data[row_idx].append("")
                    for col_name, value in updates.items():
                        if col_name in headers:
                            col_idx = headers.index(col_name)
                            all_data[row_idx][col_idx] = value

        for i in range(1, len(all_data)):
            while len(all_data[i]) < len(headers):
                all_data[i].append("")
            row_dict = dict(zip(headers, all_data[i]))
            client_name = row_dict.get('الاسم', '')

            dollar_total = 0.0
            additionals = 0.0

            for col in TICK_COLUMNS:
                status = str(row_dict.get(col, '')).upper()
                if status in ["TRUE", "PAID"]:
                    fee = custom_fees.get(col, {}).get(client_name)
                    if fee is None:
                        fee = new_fees.get(col, 0) if new_fees else 0
                    if isinstance(fee, str) and '$' in fee:
                        dollar_total += float(fee.replace('$', '').strip() or 0)
                    else:
                        additionals += float(fee or 0)

            notes = row_dict.get('الملاحظات', '')
            extra_match = re.search(r'EXTRA:(-?\d+)', notes)
            if extra_match:
                additionals += float(extra_match.group(1))

            received = float(row_dict.get('جملة المستلم', 0) or 0)
            total_required = BASE_FEES + additionals
            total_remaining = total_required - received

            all_data[i][headers.index("إجمالي دولار ($)")] = f"{dollar_total:.2f} $"
            all_data[i][headers.index("جملة المطلوب")] = int(total_required)
            all_data[i][headers.index("جملة المتبقي")] = int(total_remaining)

        sheet.update('A1', all_data)

        if new_fees and settings_sheet:
            fees_data = [["الخدمة", "المبلغ"]]
            for s, a in new_fees.items():
                fees_data.append([s, a])
            settings_sheet.update('A1', fees_data)
            clear_fees_cache()

        if custom_fees:
            try:
            try:
                cf_sheet = spreadsheet.worksheet("CustomFees")
            except gspread.exceptions.WorksheetNotFound:
                cf_sheet = spreadsheet.add_worksheet(title="CustomFees", rows="100", cols="3")
            custom_data = [["الخدمة", "العميل", "المبلغ"]]
            for s, clients in custom_fees.items():
                for c_name, amt in clients.items():
                    if amt is not None and str(amt).strip() != "":
                        custom_data.append([s, c_name, amt])
            cf_sheet.clear()
            cf_sheet.update('A1', custom_data)
        except Exception as e:
            logger.error(f"CustomFees save error: {e}")

        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"Save error: {str(e)}")
        return jsonify({"status": "failed", "message": str(e)})


# =========================
# Delete Client
# =========================
@app.route('/delete_client', methods=['POST'])
def delete_client():
    try:
        data = request.get_json()
        row_index = data.get("row_index")
        password = data.get("password")
        if not SecurityManager.verify_password(password):
            return jsonify({"status": "failed", "message": "كلمة السر خاطئة"})
        sheet.delete_rows(int(row_index) + 2)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "failed", "message": str(e)})


# =========================
# Add New Client
# =========================
@app.route('/add_client', methods=['POST'])
def add_client():
    try:
        data = request.get_json()
        user_ip = request.remote_addr
        if not SecurityManager.verify_password(data.get("password")):
            SecurityManager.log_action("ADD_CLIENT_ATTEMPT", user_ip, success=False)
            return jsonify({"status": "failed", "message": "كلمة السر خاطئة"})

        SecurityManager.log_action("ADD_CLIENT", user_ip, success=True)
        name = data.get("name", "عميل جديد").strip()
        email = data.get("email", "").strip()
        uni = data.get("uni", "").strip()
        phone = data.get("phone", "").strip()

        if not name:
            return jsonify({"status": "failed", "message": "الاسم مطلوب!"})

        now = datetime.datetime.now().strftime("%Y-%m-%d")
        new_row = [name, email, uni, "لم يحدد", "", phone, now]
        new_row += ["FALSE"] * len(TICK_COLUMNS)
        sheet.append_row(new_row)
        logger.info(f"✅ Added new client: {name}")
        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"❌ Add client failed: {str(e)}")
        return jsonify({"status": "failed", "message": str(e)})


# =========================
# Health Check
# =========================
@app.route('/health')
def health():
    try:
        spreadsheet.fetch_sheet_metadata()
        return jsonify({
            "status": "healthy",
            "sheet_name": SHEET_NAME,
            "timestamp": datetime.datetime.now().isoformat(),
            "procedure_note_columns": PROCEDURE_NOTE_COLUMNS
        })
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500


@app.errorhandler(404)
def not_found(e):
    return jsonify({"status": "error", "message": "الصفحة غير موجودة"}), 404

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"❌ Internal server error: {str(e)}")
    return jsonify({"status": "error", "message": "حدث خطأ في الخادم"}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"🚀 Starting server on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=False)
