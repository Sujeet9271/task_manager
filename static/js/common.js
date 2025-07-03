// Function to toggle the selection of other checkboxes based on "Select All" checkbox
function toggleCheckboxes(divId) {
    const selectAllCheckbox = document.getElementById(`select_all_${divId}_input`);
    const selectAllSpan = document.getElementById(`select_all_${divId}`);
    const closestDiv = document.getElementById(divId);
    const itemCheckboxes = closestDiv.querySelectorAll('input[type="checkbox"]');
    itemCheckboxes.forEach((checkbox) => {
        checkbox.checked = selectAllCheckbox.checked;
    });
    if (selectAllCheckbox.checked) {
        selectAllSpan.innerHTML = 'Unselect All'
    } else {
        selectAllSpan.innerHTML = 'Select All'
    }
}


function selectBoxes() {
    document.querySelectorAll('.select-boxes').forEach(function (box) {
        var id = box.getAttribute('id');
        var checkboxes = box.querySelectorAll('input[type="checkbox"]');

        if (checkboxes.length > 0) {
            document.querySelectorAll('.btn-select-all').forEach(function (btn) {
                btn.classList.remove('d-none');
            });
        } else {
            var closestSelectAllBtn = box.closest('.forFindClosestClass')?.querySelector('.btn-select-all');

            if (closestSelectAllBtn) {
                var label = closestSelectAllBtn.dataset.label;
                box.innerHTML = '<span style="color:gray; font-size:12px">No ' + label + ' Found!</span>';
                closestSelectAllBtn.classList.add('d-none');
            } else {
                if (closestSelectAllBtn) {
                    closestSelectAllBtn.classList.remove('d-none');
                }
            }
        }
    });

}

function initializeSearch(divId) {

    const searchInputBox = document.getElementById("searchInput" + divId);
    const userLabels = Array.from(document.querySelectorAll(`#${divId} label`));

    const users = userLabels.map((label) => ({
        id: label.getAttribute("for"),
        email: label.innerText.trim()
    }));

    const showAllUsers = () => {
        users.forEach((user) => {
            const userElement = document.getElementById(user.id)?.parentElement;
            if (userElement) userElement.style.display = "block";
        });
    };

    const delay = (fn, ms) => {
        let timer = 0;
        return function (...args) {
            clearTimeout(timer);
            timer = setTimeout(() => fn.apply(this, args), ms);
        };
    };

    const searchHandler = delay(() => {
        const searchValue = searchInputBox.value.toLowerCase();

        if (searchValue === "") {
            showAllUsers();
            return;
        }

        users.forEach((user) => {
            const userElement = document.getElementById(user.id)?.parentElement;
            if (!userElement) return;

            const userEmail = user.email.toLowerCase();
            userElement.style.display = userEmail.includes(searchValue) ? "block" : "none";
        });
    }, 300);

    // Attach event listener
    searchInputBox.addEventListener("input", searchHandler);

    // Initial call to show all users
    showAllUsers();
}

htmx.on("notificationRead", function (evt) {
    console.debug(evt)
    try {
        unread_counts = document.getElementById('unread_notification_count').innerHTML
        count = parseInt(unread_counts) - 1
        if (count) {
            document.getElementById('unread_notification_count').innerHTML = count
        } else {
            document.getElementById('unread_notification_count').remove()
        }
    } catch (error) {
        console.error(error)
    }

});

htmx.on('htmx:afterSwap', (evt) => {
    selectBoxes()
})

window.onload = function () {
    setTimeout(function () {
        document.getElementById("loader").classList.add("gif_loader");
    }, 100);

    selectBoxes()
    notification_list = document.querySelector('.notifications-btn')
    if (notification_list) {
        notification_list.addEventListener('click', function () {
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


const MAX_TOASTS = 3;
const TOAST_DELAY = 2000; // 5 seconds

htmx.on("htmx:responseError", function (event) {
    if (event.detail.xhr.status >= 400) {
        const responseText = event.detail.xhr.responseText;

        // Optional: Try to parse as JSON
        try {
            const data = JSON.parse(responseText);
            console.debug('responseError: ', data)
            showToast(data.message || "Something went wrong!");
        } catch (error) {
            console.error(error)
            showToast(responseText);
        }
    }
});



function showToast(message, level = 'danger') {
    const container = document.getElementById('htmx-toast-container');

    // Remove oldest toast if too many
    while (container.children.length >= MAX_TOASTS) {
        container.children[0].remove();
    }

    // Create unique ID
    const toastId = 'toast-' + Date.now();

    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-bg-${level} border-0 mb-2`;
    toast.role = 'alert';
    toast.ariaLive = 'assertive';
    toast.ariaAtomic = 'true';
    toast.id = toastId;
    toast.setAttribute('data-bs-delay', TOAST_DELAY);
    toast.setAttribute('data-bs-autohide', 'true');

    toast.innerHTML = `
			<div class="d-flex">
				<div class="toast-body">${message}</div>
				<button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
			</div>
			`;

    // Append and show
    container.appendChild(toast);
    const toastInstance = new bootstrap.Toast(toast);
    toastInstance.show();

    // Auto-remove after hidden
    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });
}

htmx.on("showToast", function (evt) {
    showToast(evt.detail.message, evt.detail.level)
})



function toggleDarkmode(){
    document.body.classList.toggle("dark-mode");

    // Optional: Save preference to localStorage
    if (document.body.classList.contains("dark-mode")) {
    localStorage.setItem("theme", "dark");
    } else {
    localStorage.setItem("theme", "light");
    }

}

// Load saved theme
window.addEventListener("DOMContentLoaded", () => {
    if (localStorage.getItem("theme") === "dark") {
    toggleDarkmode()
    }
});