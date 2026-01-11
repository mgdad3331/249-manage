from flask import Flask, render_template, request, jsonify
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os
import datetime
from functools import lru_cache
import logging

# =========================
# Flask App Configuration
# =========================
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False  # دعم العربية في JSON

# إعداد نظام Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =========================
# Google Sheets Credentials
# =========================
def initialize_google_sheets():
    """تهيئة اتصال Google Sheets مع معالجة الأخطاء"""
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

# =========================
# Open Google Sheet
# =========================
SHEET_NAME = "Client_Management"
spreadsheet = client.open(SHEET_NAME)
sheet = spreadsheet.sheet1

# =========================
# Settings Sheet Management (نظام إدارة الرسوم)
# =========================
def initialize_settings_sheet():
    """تهيئة ورقة الإعدادات مع القيم الافتراضية"""
    try:
        try:
            settings_sheet = spreadsheet.worksheet("Settings")
            logger.info("✅ Settings sheet found")
        except gspread.exceptions.WorksheetNotFound:
            logger.info("⚠️ Settings sheet not found, creating new one...")
            settings_sheet = spreadsheet.add_worksheet(title="Settings", rows="20", cols="2")
            
            # القيم الافتراضية للرسوم
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
# Fee Database Functions (محسّنة مع Cache)
# =========================
@lru_cache(maxsize=1)
def get_fees_from_db_cached():
    """جلب الرسوم من Settings مع تخزين مؤقت لتحسين الأداء"""
    try:
        if settings_sheet is None:
            logger.warning("⚠️ Using default fees (Settings sheet unavailable)")
            return get_default_fees()
        
        records = settings_sheet.get_all_records()
        fees = {row["الخدمة"]: row["المبلغ"] for row in records}
        logger.info(f"✅ Loaded {len(fees)} fees from database")
        return fees
    except Exception as e:
        logger.error(f"❌ Error loading fees: {str(e)}")
        return get_default_fees()

def get_default_fees():
    """القيم الافتراضية للرسوم في حال فشل التحميل"""
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
    """مسح الـ Cache بعد تحديث الرسوم"""
    get_fees_from_db_cached.cache_clear()

# =========================
# Admin Password
# =========================
ADMIN_PASSWORD = "321"

# =========================
# Columns Definition
# =========================
SPECIAL_COLUMNS = ["رقم وطني", "توثيقات", "معادلة", "توكيل", "قبول مبدئي", "تسليم الملف", "رسوم الوافدين"]
NORMAL_TICK_COLUMNS = ["الشهادات", "استلام الملف", "ترشيح نهائي", "172$"]
TICK_COLUMNS = SPECIAL_COLUMNS + NORMAL_TICK_COLUMNS

# =========================
# Routes
# =========================

@app.route('/')
def index():
    """الصفحة الرئيسية - عرض الجدول"""
    try:
        logger.info("📊 Loading main page...")
        
        # جلب بيانات العملاء
        data = sheet.get_all_records()
        logger.info(f"✅ Loaded {len(data)} client records")
        
        # جلب الرسوم من الـ Cache
        current_fees = get_fees_from_db_cached()
        
        return render_template(
            'index.html',
            clients=data,
            tick_columns=TICK_COLUMNS,
            fees=current_fees
        )
    except Exception as e:
        logger.error(f"❌ Error loading index page: {str(e)}")
        return f"حدث خطأ في تحميل الصفحة: {str(e)}", 500

# =========================
# Save All Changes (Bulk Save)
# =========================
@app.route('/save', methods=['POST'])
def save():
    """حفظ جميع التعديلات (بيانات + رسوم)"""
    try:
        data = request.get_json()
        password = data.get("password")
        
        # التحقق من كلمة السر
        if password != ADMIN_PASSWORD:
            logger.warning("⚠️ Failed save attempt - incorrect password")
            return jsonify({"status": "failed", "message": "كلمة السر خاطئة"})

        updates_by_row = data.get("updates", {})
        new_fees = data.get("fees")
        
        logger.info(f"💾 Starting save operation for {len(updates_by_row)} rows...")

        # الحصول على العناوين
        headers = sheet.row_values(1)
        
        # 1. تحديث بيانات العملاء
        if updates_by_row:
            all_data = sheet.get_all_values()
            
            for row_index_str, updates in updates_by_row.items():
                row_idx = int(row_index_str) + 1  # +1 لأن الصف الأول هو العناوين
                
                for col_name, value in updates.items():
                    if col_name in headers:
                        col_idx = headers.index(col_name)
                        all_data[row_idx][col_idx] = value
            
            # تحديث الـ Sheet دفعة واحدة (أسرع من التحديث صف بصف)
            sheet.update('A1', all_data)
            logger.info(f"✅ Updated {len(updates_by_row)} client records")

        # 2. تحديث الرسوم في Settings
        if new_fees and settings_sheet:
            fees_data = [["الخدمة", "المبلغ"]]
            for service_name, amount in new_fees.items():
                fees_data.append([service_name, amount])
            
            settings_sheet.update('A1', fees_data)
            clear_fees_cache()  # مسح الـ Cache
            logger.info(f"✅ Updated {len(new_fees)} fee records")
        
        return jsonify({"status": "success"})
        
    except Exception as e:
        logger.error(f"❌ Save operation failed: {str(e)}")
        return jsonify({"status": "failed", "message": f"خطأ في الحفظ: {str(e)}"})

# =========================
# Add New Client
# =========================
@app.route('/add_client', methods=['POST'])
def add_client():
    """إضافة عميل جديد"""
    try:
        data = request.get_json()
        
        # التحقق من كلمة السر
        if data.get("password") != ADMIN_PASSWORD:
            logger.warning("⚠️ Failed add attempt - incorrect password")
            return jsonify({"status": "failed", "message": "كلمة السر خاطئة"})

        # استخراج البيانات مع قيم افتراضية
        name = data.get("name", "عميل جديد")
        email = data.get("email", "")
        uni = data.get("uni", "")
        phone = data.get("phone", "")
        
        # التحقق من صحة البيانات
        if not name or name.strip() == "":
            return jsonify({"status": "failed", "message": "الاسم مطلوب!"})
        
        # إنشاء الصف الجديد
        now = datetime.datetime.now().strftime("%Y-%m-%d")
        new_row = [
            name.strip(),  # الاسم
            email.strip(), # البريد
            uni.strip(),   # الجامعة
            "لم يحدد",     # الرغبة
            "",            # العنوان
            phone.strip(), # الرقم
            now            # تاريخ البدء
        ]
        
        # إضافة القيم الافتراضية للـ Tick Columns
        new_row += ["FALSE"] * len(TICK_COLUMNS)
        
        # إضافة الصف
        sheet.append_row(new_row)
        logger.info(f"✅ Added new client: {name}")
        
        return jsonify({"status": "success"})
        
    except Exception as e:
        logger.error(f"❌ Add client failed: {str(e)}")
        return jsonify({"status": "failed", "message": f"خطأ في الإضافة: {str(e)}"})

# =========================
# Health Check Endpoint
# =========================
@app.route('/health')
def health():
    """نقطة نهاية لفحص صحة الخادم"""
    try:
        # اختبار الاتصال بـ Google Sheets
        spreadsheet.fetch_sheet_metadata()
        return jsonify({
            "status": "healthy",
            "sheet_name": SHEET_NAME,
            "timestamp": datetime.datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"❌ Health check failed: {str(e)}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500

# =========================
# Error Handlers
# =========================
@app.errorhandler(404)
def not_found(e):
    return jsonify({"status": "error", "message": "الصفحة غير موجودة"}), 404

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"❌ Internal server error: {str(e)}")
    return jsonify({"status": "error", "message": "حدث خطأ في الخادم"}), 500

# =========================
# Run Application
# =========================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"🚀 Starting server on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=False)
