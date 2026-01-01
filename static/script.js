let clients = JSON.parse('{{ clients|tojson|safe }}');
let tick_columns = JSON.parse('{{ tick_columns|tojson|safe }}');

// عرض قائمة العملاء + زر إضافة عميل
function renderClientList() {
    let html = '';
    clients.forEach((client, index) => {
        html += `<li class="client-item" data-index="${index}">${client['Name']}</li>`;
    });

    // زر إضافة عميل جديد تحت آخر عميل
    html += `<li class="client-item add-client-item" onclick="addClient()">إضافة عميل جديد</li>`;

    $('#client-ul').html(html);
}

// عرض تفاصيل العميل
function renderClientDetails(index){
    let client = clients[index];
    let html = `<h4>${client['Name']}</h4>
                <p><b>Email:</b> ${client['Email']}</p>
                <p><b>University:</b> ${client['University']}</p>
                <p><b>Address:</b> ${client['Address']}</p>
                <p><b>Phone:</b> ${client['Phone']}</p>
                <p><b>Start Date:</b> ${client['Start Date']}</p>
                <hr>
                <h4>Procedures</h4>`;

    tick_columns.forEach(function(col){
        let checked = client[col] === 'TRUE';
        html += `<div class="form-check">
                    <span class="tick">${checked ? '✔' : '⬜'}</span> ${col}
                 </div>`;
    });

    $('#details').html(html);
}

// اختيار العميل
$(document).on('click', '.client-item', function(){
    let index = $(this).data('index');
    if(index !== undefined){
        renderClientDetails(index);
    }
});

// زر إضافة العميل الجديد (حاليا واجهة فقط)
function addClient(){
    alert("فقط الأدمن يمكنه إضافة عميل جديد بعد إدخال كلمة السر.");
}

// بدء التطبيق
$(document).ready(function(){
    renderClientList();
});
