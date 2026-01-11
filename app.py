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

# =========================
# Flask App Configuration
# =========================
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', secrets.token_hex(32))

# إعداد نظام Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =========================
# Security Configuration
# =========================
class SecurityManager:
    """نظام الأمان المحسّن"""
    
    @staticmethod
    def get_admin_password():
        """جلب كلمة السر من Environment Variable"""
        password = os.environ.get("ADMIN_PASSWORD")
        if not password:
            logger.warning("⚠️ ADMIN_PASSWORD not set, using default (INSECURE!)")
            return "321"  # قيمة افتراضية للتطوير فقط
        return password
    
    @staticmethod
    def hash_password(password):
        """تشفير كلمة السر (للاستخدام المستقبلي)"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    @staticmethod
    def verify_password(provided_password):
        """التحقق من كلمة السر"""
        admin_pass = SecurityManager.get_admin_password()
        return provided_password == admin_pass
    
    @staticmethod
    def log_action(action, user_ip, success=True):
        """تسجيل العمليات الحساسة"""
        status = "✅ SUCCESS" if success else "❌ FAILED"
        logger.info(f"{status} | Action: {action} | IP: {user_ip}")

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
SHEET_NAME = os.environ.get("SHEET_NAME", "Client_Management")
spreadsheet = client.open(SHEET_NAME)
sheet = spreadsheet.sheet1

# =========================
# Settings Sheet Management
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
    """جلب الرسوم من Settings مع تخزين مؤقت"""
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
    """القيم الافتراضية للرسوم"""
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
        
        data = sheet.get_all_records()
        logger.info(f"✅ Loaded {len(data)} client records")
        
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
# NEW: Verify Password API
# =========================
@app.route('/verify_password', methods=['POST'])
def verify_password():
    """API للتحقق من كلمة السر قبل فتح التعديل"""
    try:
        data = request.get_json()
        password = data.get("password")
        user_ip = request.remote_addr
        
        if SecurityManager.verify_password(password):
            SecurityManager.log_action("PASSWORD_VERIFY_SUCCESS", user_ip, success=True)
            logger.info(f"✅ Password verified successfully from IP: {user_ip}")
            return jsonify({
                "status": "success",
                "message": "كلمة السر صحيحة"
            })
        else:
            SecurityManager.log_action("PASSWORD_VERIFY_FAILED", user_ip, success=False)
            logger.warning(f"⚠️ Failed password verification from IP: {user_ip}")
            return jsonify({
                "status": "failed",
                "message": "كلمة السر خاطئة"
            })
    except Exception as e:
        logger.error(f"❌ Error verifying password: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

# =========================
# Get Client Names API
# =========================
@app.route('/get_clients', methods=['GET'])
def get_clients():
    """API لجلب أسماء العملاء فقط"""
    try:
        data = sheet.get_all_records()
        # استخراج الأسماء فقط
        client_names = [client.get('الاسم', '') for client in data if client.get('الاسم')]
        
        logger.info(f"✅ Retrieved {len(client_names)} client names")
        return jsonify({
            "status": "success",
            "clients": client_names
        })
    except Exception as e:
        logger.error(f"❌ Error retrieving clients: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

# =========================
# Load Custom Fees API
# =========================
@app.route('/get_custom_fees', methods=['GET'])
def get_custom_fees():
    """API لجلب الرسوم المخصصة المحفوظة"""
    try:
        try:
            custom_fees_sheet = spreadsheet.worksheet("CustomFees")
            records = custom_fees_sheet.get_all_records()
            
            # تحويل البيانات لصيغة JavaScript
            custom_fees = {}
            for row in records:
                service = row.get('الخدمة', '')
                client = row.get('العميل', '')
                amount = row.get('المبلغ', 0)
                
                if service and client:
                    if service not in custom_fees:
                        custom_fees[service] = {}
                    custom_fees[service][client] = amount
            
            logger.info(f"✅ Loaded custom fees for {len(records)} entries")
            return jsonify({
                "status": "success",
                "customFees": custom_fees
            })
        except gspread.exceptions.WorksheetNotFound:
            logger.info("⚠️ CustomFees sheet not found, returning empty")
            return jsonify({
                "status": "success",
                "customFees": {}
            })
    except Exception as e:
        logger.error(f"❌ Error loading custom fees: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

# =========================
# Save All Changes
# =========================
@app.route('/save', methods=['POST'])
def save():
    """حفظ جميع التعديلات مع نظام أمان محسّن"""
    try:
        data = request.get_json()
        password = data.get("password")
        user_ip = request.remote_addr
        
        # التحقق من كلمة السر باستخدام SecurityManager
        if not SecurityManager.verify_password(password):
            SecurityManager.log_action("SAVE_ATTEMPT", user_ip, success=False)
            logger.warning(f"⚠️ Failed save attempt from IP: {user_ip}")
            return jsonify({"status": "failed", "message": "كلمة السر خاطئة"})

        SecurityManager.log_action("SAVE_DATA", user_ip, success=True)
        
        updates_by_row = data.get("updates", {})
        new_fees = data.get("fees")
        custom_fees = data.get("customFees", {})
        
        logger.info(f"💾 Starting save operation for {len(updates_by_row)} rows...")

        headers = sheet.row_values(1)
        
        # 1. تحديث بيانات العملاء
        if updates_by_row:
            all_data = sheet.get_all_values()
            
            for row_index_str, updates in updates_by_row.items():
                row_idx = int(row_index_str) + 1
                
                for col_name, value in updates.items():
                    if col_name in headers:
                        col_idx = headers.index(col_name)
                        all_data[row_idx][col_idx] = value
            
            sheet.update('A1', all_data)
            logger.info(f"✅ Updated {len(updates_by_row)} client records")

        # 2. تحديث الرسوم العامة
        if new_fees and settings_sheet:
            fees_data = [["الخدمة", "المبلغ"]]
            for service_name, amount in new_fees.items():
                fees_data.append([service_name, amount])
            
            settings_sheet.update('A1', fees_data)
            clear_fees_cache()
            logger.info(f"✅ Updated {len(new_fees)} fee records")
        
        # 3. حفظ الرسوم المخصصة
        if custom_fees:
            try:
                try:
                    custom_fees_sheet = spreadsheet.worksheet("CustomFees")
                except gspread.exceptions.WorksheetNotFound:
                    custom_fees_sheet = spreadsheet.add_worksheet(title="CustomFees", rows="100", cols="3")
                
                custom_data = [["الخدمة", "العميل", "المبلغ"]]
                for service, clients in custom_fees.items():
                    for client_name, amount in clients.items():
                        custom_data.append([service, client_name, amount])
                
                custom_fees_sheet.clear()
                custom_fees_sheet.update('A1', custom_data)
                logger.info(f"✅ Saved custom fees")
            except Exception as e:
                logger.warning(f"⚠️ Failed to save custom fees: {str(e)}")
        
        return jsonify({"status": "success"})
        
    except Exception as e:
        logger.error(f"❌ Save operation failed: {str(e)}")
        return jsonify({"status": "failed", "message": f"خطأ في الحفظ: {str(e)}"})

# =========================
# Add New Client
# =========================
@app.route('/add_client', methods=['POST'])
def add_client():
    """إضافة عميل جديد مع نظام أمان محسّن"""
    try:
        data = request.get_json()
        user_ip = request.remote_addr
        
        # التحقق من كلمة السر
        if not SecurityManager.verify_password(data.get("password")):
            SecurityManager.log_action("ADD_CLIENT_ATTEMPT", user_ip, success=False)
            logger.warning(f"⚠️ Failed add attempt from IP: {user_ip}")
            return jsonify({"status": "failed", "message": "كلمة السر خاطئة"})

        SecurityManager.log_action("ADD_CLIENT", user_ip, success=True)
        
        name = data.get("name", "عميل جديد")
        email = data.get("email", "")
        uni = data.get("uni", "")
        phone = data.get("phone", "")
        
        if not name or name.strip() == "":
            return jsonify({"status": "failed", "message": "الاسم مطلوب!"})
        
        now = datetime.datetime.now().strftime("%Y-%m-%d")
        new_row = [
            name.strip(),
            email.strip(),
            uni.strip(),
            "لم يحدد",
            "",
            phone.strip(),
            now
        ]
        
        new_row += ["FALSE"] * len(TICK_COLUMNS)
        
        sheet.append_row(new_row)
        logger.info(f"✅ Added new client: {name} from IP: {user_ip}")
        
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
        spreadsheet.fetch_sheet_metadata()
        return jsonify({
            "status": "healthy",
            "sheet_name": SHEET_NAME,
            "timestamp": datetime.datetime.now().isoformat(),
            "security": "enabled" if os.environ.get("ADMIN_PASSWORD") else "default"
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
    logger.info(f"🔐 Security: {'ENABLED (Custom Password)' if os.environ.get('ADMIN_PASSWORD') else 'DEFAULT (321)'}")
    app.run(host='0.0.0.0', port=port, debug=False)
