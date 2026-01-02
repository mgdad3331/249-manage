$(document).ready(function(){

    // الضغط على زر إضافة عميل جديد
    $('.add-client-btn').click(function(){
        let password = prompt("أدخل كلمة سر الأدمن:");
        if(!password) return;

        $.post('/add_client', {password: password}, function(res){
            if(res.status === 'success'){
                alert("تم إضافة العميل الجديد ✅");
                location.reload();
            } else {
                alert("فشل الإضافة: " + res.message);
            }
        });
    });

});
