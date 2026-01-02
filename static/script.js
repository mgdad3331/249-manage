$(document).ready(function() {
    let adminPass = "";

    // 1. نظام البحث السريع
    $("#searchInput").on("keyup", function() {
        var value = $(this).val().toLowerCase();
        $("#client-table tbody tr").filter(function() {
            $(this).toggle($(this).text().toLowerCase().indexOf(value) > -1)
        });
    });

    // 2. زر فتح التعديل العام (يفتح كل الـ Ticks مرة واحدة)
    $('#enable-all-edit').click(function() {
        let pwd = prompt("أدخل كلمة سر الأدمن لفتح التعديل للجميع:");
        if (pwd === "Miqdad123") {
            adminPass = pwd;
            $('.tick-input').prop('disabled', false); // تفعيل كل الصاحات في الجدول
            $(this).removeClass('btn-info').addClass('btn-success').text('🔓 وضع التعديل نشط');
            $('#client-table').addClass('table-active'); 
            alert("يمكنك الآن تعديل الصاحات لجميع العملاء.");
        } else {
            alert("كلمة السر خاطئة!");
        }
    });

    // 3. الضغط على زر إضافة عميل (فتح المودال)
    $('#add-client-btn').click(function() {
        let pwd = prompt("أدخل كلمة سر الأدمن:");
        if (pwd === "Miqdad123") {
            adminPass = pwd;
            var myModal = new bootstrap.Modal(document.getElementById('addClientModal'));
            myModal.show();
        } else {
            alert("كلمة السر خاطئة!");
        }
    });

    // 4. تأكيد إضافة العميل من داخل المودال
    $('#confirm-add-btn').click(function() {
        const data = {
            password: adminPass,
            name: $('#newName').val(),
            email: $('#newEmail').val(),
            uni: $('#newUni').val(),
            phone: $('#newPhone').val()
        };

        $.ajax({
            url: '/add_client',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(data),
            success: function(res) {
                if (res.status === 'success') {
                    location.reload();
                } else {
                    alert("خطأ: " + res.message);
                }
            }
        });
    });

    // 5. حفظ كافة التغييرات (الـ Ticks المعدلة)
    $('#save-all-btn').click(function() {
        if (!adminPass) {
            adminPass = prompt("يرجى إدخال كلمة السر للتأكيد قبل الحفظ:");
        }
        if (!adminPass) return;

        let updates = {};
        $('#client-table tbody tr').each(function() {
            let rowIndex = $(this).data('row');
            updates[rowIndex] = {};
            $(this).find('.tick-input').each(function() {
                updates[rowIndex][$(this).data('col')] = $(this).is(':checked') ? "TRUE" : "FALSE";
            });
        });

        $.ajax({
            url: '/save',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ password: adminPass, updates: updates }),
            success: function(res) {
                if (res.status === 'success') {
                    alert("تم حفظ جميع التغييرات في Google Sheets ✅");
                    location.reload();
                } else {
                    alert("فشل الحفظ: " + res.message);
                }
            }
        });
    });
});
