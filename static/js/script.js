// ==================== متغيرات عامة ====================
let activePass = "";
let currentNoteInput = null;
let feeDatabase = {};
let activeFeeCol = "";

// ==================== نظام الإشعارات المحسّن ====================
const ToastManager = {
    container: null,
    
    init() {
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.className = 'toast-container';
            document.body.appendChild(this.container);
        }
    },
    
    show(message, type = 'info', duration = 3000) {
        this.init();
        
        const icons = {
            success: '✅',
            error: '❌',
            warning: '⚠️',
            info: 'ℹ️'
        };
        
        const toast = document.createElement('div');
        toast.className = `custom-toast toast-${type} p-3 mb-2 shadow-lg`;
        toast.innerHTML = `
            <div class="d-flex align-items-center gap-2">
                <span style="font-size: 1.5rem;">${icons[type] || icons.info}</span>
                <div class="flex-grow-1">
                    <strong>${message}</strong>
                </div>
                <button type="button" class="btn-close btn-close-white" onclick="this.parentElement.parentElement.remove()"></button>
            </div>
        `;
        
        this.container.appendChild(toast);
        
        setTimeout(() => {
            toast.style.animation = 'toastSlideIn 0.4s ease reverse';
            setTimeout(() => toast.remove(), 400);
        }, duration);
    },
    
    success(message, duration) { this.show(message, 'success', duration); },
    error(message, duration) { this.show(message, 'error', duration); },
    warning(message, duration) { this.show(message, 'warning', duration); },
    info(message, duration) { this.show(message, 'info', duration); }
};

// ==================== نظام Loading المحسّن ====================
const LoadingManager = {
    overlay: null,
    
    init() {
        if (!this.overlay) {
            this.overlay = document.createElement('div');
            this.overlay.className = 'loading-overlay';
            this.overlay.innerHTML = `
                <div class="text-center">
                    <div class="loader"></div>
                    <div class="loader-text" id="loader-text">جاري التحميل...</div>
                </div>
            `;
            document.body.appendChild(this.overlay);
        }
    },
    
    show(message = 'جاري التحميل...') {
        this.init();
        document.getElementById('loader-text').textContent = message;
        this.overlay.classList.add('active');
    },
    
    hide() {
        if (this.overlay) {
            this.overlay.classList.remove('active');
        }
    }
};

// ==================== الحسابات المالية ====================
function calculateFinances() {
    $('#client-table tbody tr').each(function() {
        let row = $(this);
        let baseFees = 26000;
        let additionals = 0;
        
        // حساب الخدمات المفعّلة
        row.find('.tick-input, .tri-state-toggle').each(function() {
            let colName = $(this).data('col').toString().trim();
            let status = $(this).hasClass('tri-state-toggle') 
                ? $(this).attr('data-value') 
                : ($(this).is(':checked') ? "TRUE" : "FALSE");
            
            if (status === "PAID" || status === "TRUE") {
                additionals += (feeDatabase[colName] || 0);
            }
        });

        // استخراج المبالغ الإضافية من الملاحظات
        let noteContent = row.find('.note-data').val() || "";
        let extraMatch = noteContent.match(/EXTRA:(-?\d+)/);
        if(extraMatch) {
            additionals += parseFloat(extraMatch[1]);
        }

        let received = parseFloat(row.find('.received-amount-input').val()) || 0;
        let totalRequired = baseFees + additionals;
        let remaining = totalRequired - received;
        
        row.find('.total-required').text(totalRequired.toLocaleString('ar-EG'));
        row.find('.total-remaining').text(remaining.toLocaleString('ar-EG'));
        row.find('.total-remaining').css('color', remaining > 0 ? '#dc3545' : '#198754');
    });
}

// ==================== فتح/إغلاق التعديل العام ====================
function toggleGlobalEdit() {
    if ($('body').hasClass('edit-active')) {
        // إذا كان التعديل مفعّل، نطلب تأكيد الإغلاق
        if (confirm('هل تريد إغلاق وضع التعديل؟ تأكد من حفظ التغييرات أولاً!')) {
            closeEditMode();
        }
    } else {
        // فتح وضع التعديل
        let pwd = prompt("أدخل كلمة السر لفتح التعديل:");
        if (pwd === "321") {
            activePass = pwd;
            openEditMode();
            ToastManager.success('تم فتح وضع التعديل بنجاح! يمكنك الآن تعديل البيانات', 2500);
        } else if (pwd !== null) {
            ToastManager.error('كلمة السر غير صحيحة!', 3000);
        }
    }
}

function openEditMode() {
    $('body').addClass('edit-active').removeClass('edit-locked');
    $('.tick-input').prop('disabled', false);
    $('.view-text').addClass('d-none');
    $('.edit-input').removeClass('d-none');
    $('#main-edit-btn')
        .removeClass('btn-dark-blue')
        .addClass('btn-success')
        .html('🔓 التعديل نشط');
    $('#customFeeHint').removeClass('d-none');
    calculateFinances();
}

function closeEditMode() {
    $('body').removeClass('edit-active').addClass('edit-locked');
    $('.tick-input').prop('disabled', true);
    $('.view-text').removeClass('d-none');
    $('.edit-input').addClass('d-none');
    $('#main-edit-btn')
        .removeClass('btn-success')
        .addClass('btn-dark-blue')
        .html('🔓 فتح التعديل العام');
    activePass = "";
}

// ==================== إعدادات الرسوم ====================
function openFeeModal(col) {
    activeFeeCol = col;
    $('#currentFeeCol').text(col);
    $('#newFeeAmount').val(feeDatabase[col] || 0);
    new bootstrap.Modal(document.getElementById('feeSettingsModal')).show();
}

function applySmartFee() {
    const newAmount = parseFloat($('#newFeeAmount').val()) || 0;
    feeDatabase[activeFeeCol] = newAmount;
    
    bootstrap.Modal.getInstance(document.getElementById('feeSettingsModal')).hide();
    calculateFinances();
    
    ToastManager.info(`تم تحديث رسوم "${activeFeeCol}" إلى ${newAmount.toLocaleString('ar-EG')} جنيه`, 2500);
}

// ==================== نظام الحالات الثلاثية ====================
function toggleTriState(el) {
    if (activePass !== "321") {
        ToastManager.warning('يجب فتح وضع التعديل أولاً!', 2000);
        return;
    }
    
    let val = $(el).attr('data-value');
    let newVal = (val === "PAID") ? "TRUE" : (val === "TRUE" ? "FALSE" : "PAID");
    
    $(el).attr('data-value', newVal)
        .removeClass('state-paid state-done')
        .addClass(newVal === "PAID" ? "state-paid" : (newVal === "TRUE" ? "state-done" : ""));
    
    calculateFinances();
}

// ==================== إدارة الملاحظات ====================
function showNote(btn) {
    currentNoteInput = $(btn).siblings('.note-data');
    $('#noteTextArea').val(currentNoteInput.val());
    
    if (activePass === "321") {
        $('#noteTextArea').prop('readonly', false);
        $('#saveNoteBtn, #customFeeHint').removeClass('d-none');
    } else {
        $('#noteTextArea').prop('readonly', true);
        $('#saveNoteBtn, #customFeeHint').addClass('d-none');
    }
    
    new bootstrap.Modal(document.getElementById('noteModal')).show();
}

function updateNoteFromModal() {
    currentNoteInput.val($('#noteTextArea').val());
    bootstrap.Modal.getInstance(document.getElementById('noteModal')).hide();
    calculateFinances();
    ToastManager.success('تم حفظ الملاحظة بنجاح', 2000);
}

// ==================== إضافة عميل جديد ====================
function openAddModal() {
    const pwd = prompt("أدخل كلمة السر للإضافة:");
    if (pwd === "321") {
        activePass = "321";
        // تفريغ الحقول
        $('#newName, #newEmail, #newUni, #newPhone').val('');
        new bootstrap.Modal(document.getElementById('addClientModal')).show();
    } else if (pwd !== null) {
        ToastManager.error('كلمة السر غير صحيحة!', 2500);
    }
}

function executeAdd() {
    const name = $('#newName').val().trim();
    const email = $('#newEmail').val().trim();
    const uni = $('#newUni').val().trim();
    const phone = $('#newPhone').val().trim();
    
    // Validation
    if (!name) {
        ToastManager.warning('يرجى إدخال اسم العميل!', 2500);
        return;
    }
    
    LoadingManager.show('جاري إضافة العميل...');
    
    const data = { 
        password: activePass, 
        name: name, 
        email: email, 
        uni: uni, 
        phone: phone 
    };
    
    fetch('/add_client', { 
        method: 'POST', 
        headers: {'Content-Type': 'application/json'}, 
        body: JSON.stringify(data) 
    })
    .then(res => res.json())
    .then(res => {
        LoadingManager.hide();
        
        if(res.status === "success") {
            ToastManager.success('تم إضافة العميل بنجاح! جاري تحديث الصفحة...', 2000);
            setTimeout(() => location.reload(), 1500);
        } else {
            ToastManager.error("فشل الإضافة: " + res.message, 3500);
        }
    })
    .catch(err => {
        LoadingManager.hide();
        ToastManager.error('حدث خطأ في الاتصال بالخادم!', 3000);
        console.error('Error:', err);
    });
}

// ==================== حفظ كل التغييرات ====================
function saveAll() {
    if (activePass !== "321") {
        activePass = prompt("أدخل كلمة السر للحفظ:");
    }
    
    if (activePass !== "321") {
        ToastManager.error('فشل الحفظ: كلمة السر غير صحيحة', 3000);
        return;
    }

    LoadingManager.show('جاري حفظ التغييرات في Google Sheets...');
    
    $('#save-text').text('جاري الحفظ...');
    $('#save-spinner').removeClass('d-none');
    $('#save-all-btn').prop('disabled', true);

    let updates = {};
    
    // جمع كل التعديلات
    $('#client-table tbody tr').each(function() {
        let rowIdx = $(this).data('row');
        updates[rowIdx] = {};
        
        $(this).find('.tick-input, .edit-input, .tri-state-toggle, .received-amount-input').each(function() {
            let col = $(this).data('col');
            if (col) {
                let val = $(this).hasClass('tri-state-toggle') 
                    ? $(this).attr('data-value') 
                    : ($(this).is(':checkbox') 
                        ? ($(this).is(':checked') ? "TRUE" : "FALSE") 
                        : $(this).val());
                updates[rowIdx][col] = val;
            }
        });
    });

    // إرسال البيانات
    fetch('/save', { 
        method: 'POST', 
        headers: {'Content-Type': 'application/json'}, 
        body: JSON.stringify({ 
            password: activePass, 
            updates: updates,
            fees: feeDatabase
        }) 
    })
    .then(response => response.json())
    .then(res => {
        LoadingManager.hide();
        
        if(res.status === "success") {
            ToastManager.success('تم حفظ جميع التغييرات بنجاح! ✅', 2500);
            setTimeout(() => location.reload(), 2000);
        } else {
            ToastManager.error("فشل الحفظ: " + res.message, 4000);
            resetSaveButton();
        }
    })
    .catch(err => {
        LoadingManager.hide();
        ToastManager.error('فشل الاتصال بالخادم! تحقق من الاتصال بالإنترنت', 4000);
        console.error('Save Error:', err);
        resetSaveButton();
    });
}

function resetSaveButton() {
    $('#save-text').text('💾 حفظ التغييرات');
    $('#save-spinner').addClass('d-none');
    $('#save-all-btn').prop('disabled', false);
}

// ==================== البحث والفلترة ====================
function initSearch() {
    $("#searchInput").on("keyup", function() {
        const searchValue = $(this).val().toLowerCase().trim();
        
        $("#client-table tbody tr").filter(function() {
            const rowText = $(this).text().toLowerCase();
            const match = rowText.indexOf(searchValue) > -1;
            $(this).toggle(match);
        });
        
        // عرض رسالة إذا لم توجد نتائج
        const visibleRows = $("#client-table tbody tr:visible").length;
        if (visibleRows === 0 && searchValue !== "") {
            if (!$('#no-results-message').length) {
                $('#client-table tbody').append(`
                    <tr id="no-results-message">
                        <td colspan="100%" class="text-center py-5">
                            <div class="text-muted">
                                <i class="fs-1">🔍</i>
                                <h5 class="mt-3">لا توجد نتائج مطابقة للبحث</h5>
                                <p>جرّب كلمات مفتاحية أخرى</p>
                            </div>
                        </td>
                    </tr>
                `);
            }
        } else {
            $('#no-results-message').remove();
        }
    });
}

// ==================== التهيئة عند تحميل الصفحة ====================
$(document).ready(function() {
    // تهيئة الأنظمة
    ToastManager.init();
    LoadingManager.init();
    initSearch();
    
    // حساب المبالغ المالية
    calculateFinances();
    
    // مراقبة التغييرات على الحقول المالية
    $(document).on('change input', '.received-amount-input, .tick-input', calculateFinances);
    
    // إضافة تأثير Fade-in للجدول
    $('#client-table').addClass('fade-in');
    
    // رسالة ترحيب (اختياري)
    console.log('%c🎉 نظام إدارة العملاء المالي v2.0', 'color: #f59e0b; font-size: 16px; font-weight: bold;');
    console.log('%cتم تحميل النظام بنجاح!', 'color: #10b981; font-size: 14px;');
});
