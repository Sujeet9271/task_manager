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

function copyToClipboard(element) {
    // Get the data-url value
    const url = element.getAttribute('data-copy');

    // Create a temporary input element to hold the URL for copying
    const input = document.createElement('input');
    input.value = url;
    document.body.appendChild(input);

    // Select the input field and copy the value
    input.select();
    document.execCommand('copy');
    
    // Remove the temporary input element
    document.body.removeChild(input);

    // Optional: You can add a notification here, such as an alert or a message
    alert('URL copied to clipboard!');
  }