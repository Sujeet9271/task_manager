function toggleCheckboxes(divId) {
	var selectAllCheckbox = document.getElementById('select_all' + divId)
	var closestDiv = document.getElementById(divId) // Find the closest ancestor div
	var itemCheckboxes = closestDiv.getElementsByClassName('form-check-label')
	for (var i = 0; i < itemCheckboxes.length; i++) {
		itemCheckboxes[i].checked = selectAllCheckbox.checked
	}
}


window.onload = function() {
    setTimeout(function(){
        document.getElementById("loader").classList.add("gif_loader");
    }, 100);
	
	notification_list = document.querySelector('.notifications')
	if (notification_list){
		notification_list.addEventListener('click', function() {
			const dropdown = document.getElementById('notification-div');
			dropdown.classList.toggle('show');
		});
	}
}

