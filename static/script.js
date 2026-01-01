let clients = JSON.parse('{{ clients|tojson|safe }}');
let tick_columns = JSON.parse('{{ tick_columns|tojson|safe }}');

function renderClientDetails(index){
    let client = clients[index];
    let html = `<h5>${client['Name']}</h5>
                <p>Email: ${client['Email']}</p>
                <p>University: ${client['University']}</p>
                <p>Address: ${client['Address']}</p>
                <p>Phone: ${client['Phone']}</p>
                <p>Start Date: ${client['Start Date']}</p>
                <hr>
                <h5>Procedures</h5>`;

    tick_columns.forEach(function(col){
        let checked = client[col] ? 'checked' : '';
        html += `<div class="form-check">
                    <input type="checkbox" class="form-check-input tick" data-index="${index}" data-col="${col}" ${checked}>
                    <label class="form-check-label">${col}</label>
                 </div>`;
    });

    html += `<button class="btn btn-warning btn-edit" data-index="${index}">Edit (Admin)</button>`;
    $('#details').html(html);
}

// اختيار العميل
$(document).on('click', '.client-item', function(){
    let index = $(this).data('index');
    renderClientDetails(index);
});

// تحديث Check Tick مباشرة
$(document).on('change', '.tick', function(){
    let index = $(this).data('index');
    let col = $(this).data('col');
    let value = $(this).is(':checked') ? 'TRUE' : 'FALSE';

    $.post('/update', {row_index:index, column_name:col, value:value}, function(res){
        if(res.status === 'success'){
            clients[index][col] = value === 'TRUE';
        }
    });
});

// تعديل Admin
$(document).on('click', '.btn-edit', function(){
    let index = $(this).data('index');
    let password = prompt("Enter Admin Password:");
    if(!password) return;

    let updates = {};
    let newName = prompt("Edit Name:", clients[index]['Name']);
    if(newName) updates['Name'] = newName;

    $.post('/edit', {row_index:index, password:password, updates:JSON.stringify(updates)}, function(res){
        if(res.status === 'success'){
            alert('Updated!');
            clients[index]['Name'] = updates['Name'];
            renderClientDetails(index);
        } else {
            alert(res.message);
        }
    });
});

// فلترة العملاء
$('#search').on('keyup', function(){
    let val = $(this).val().toLowerCase();
    $('#client-ul li').filter(function(){
        $(this).toggle($(this).text().toLowerCase().indexOf(val) > -1)
    });
});
