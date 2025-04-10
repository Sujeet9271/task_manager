const editTaskModal = document.getElementById("editTaskModal");
	editTaskModal.addEventListener("hidden.bs.modal", (event) => {
		event.target.querySelector(".modal-body").innerHTML = "";
	});

	htmx.on("columnDeleted", function (evt) {
		column_list_item = evt.detail.column_list_item;
		document.getElementById(column_list_item).remove();
		columns = document.getElementById("columns").children;
		setTimeout(() => {
			if (columns.length == 0) {
				content = `<div class="col-md-12 text-center">
								<p>No columns available. Please create a column.</p>
								<button class="btn btn-primary" 
								hx-get="${evt.detail.create_column_url}"
								hx-target="#modal-column-body"
								hx-swap="innerHTML"
								data-bs-toggle="modal" 
								data-bs-target="#createColumnModal" 
								id="createColumnButton"
								>Create Column</button>
							</div>`
				document.getElementById("columns").innerHTML = content;
				htmx.process(document.getElementById("columns"));
			}
		}, 1000);
	});

	htmx.on("boardCreated", function (evt) {
		document.getElementById("create_board_form").reset();
		board_url = evt.detail.message;
		document.getElementById('close_createBoardModal').click()
		htmx.ajax("GET", board_url, { target: "#main-content", swap: "innerHTML" });
	});

	htmx.on("reloadBoard", function (evt) {
		board_url = evt.detail.message;
		htmx.ajax("GET", board_url, { target: "#main-content", swap: "innerHTML" });
	});
	
	htmx.on("columnCreated", function (evt) {
		board_url = evt.detail.message;
		document.getElementById('close_createColumnModal').click()
		htmx.ajax("GET", board_url, { target: "#main-content", swap: "innerHTML" });
	});


	htmx.on("commentAdded", function (evt) {
		document.getElementById("comment_form").reset();
	});


	htmx.on("notificationRead", function (evt) {
		try{
			unread_counts = document.getElementById('unread_notification_count').innerHTML
			count = parseInt(unread_counts) - 1
			if (count){
				document.getElementById('unread_notification_count').innerHTML = count
			}else{
				document.getElementById('unread_notification_count').remove()
			}
		}catch(error){
			console.log(error)
		}

	});

	htmx.on("columnUpdated", function (evt) {
		board_id = evt.detail.board_id;
		column_id = evt.detail.column_id;
		column_name = evt.detail.column_name;
		id=`board_${board_id}_column_${column_id}`
		document.getElementById(id).innerHTML = ` - ${column_name}`
		document.getElementById(`column_name_${column_id}`).value = column_name
	});

	htmx.on("boardLoaded", function (evt) {
		let previous_board = document.querySelector(".active_board")
		if (previous_board) {
			previous_board.classList.remove("active_board");
		}
		let current_board = document.getElementById(`board-${evt.detail.board_id}`)
		current_board.classList.add("active_board");
	});

	htmx.on("taskEdited", function (evt) {
		board_url = evt.detail.message;
		htmx.ajax("GET", board_url, { target: "#main-content", swap: "innerHTML" });
	});

	htmx.on("closeModal", function (evt) {
		document.getElementById(evt.detail.modal_id).click()
	});

	htmx.on("reloadTaskList", function (evt) {
		board_id = evt.detail.board_id;
		column_id = evt.detail.column_id;
		document.getElementById(`create_task_form_${column_id}`).reset();
		get_task_lists = evt.detail.get_task_lists;
		
		//htmx.ajax("GET", get_task_lists, { target: `#tasks_list_${column_id}`, swap: "innerHTML" });
	});

	htmx.on("subTaskCreated", function (evt) {
		board_id = evt.detail.board_id;
		column_id = evt.detail.column_id;
		task_id = evt.detail.task_id
		document.getElementById(`create_sub_task_form`).reset();
		get_task_lists = evt.detail.get_task_lists;
		
		//htmx.ajax("GET", get_task_lists, { target: `#tasks_list_${column_id}`, swap: "innerHTML" });
	});


	function addUrlInput() {
        const wrapper = document.getElementById('link-wrapper');
        const div = document.createElement('div');
        div.classList.add('url-input', 'mb-2', 'd-flex', 'gap-2', 'align-items-start');
        div.innerHTML = `
            <div class="flex-grow-1">
                <input type="url" class="form-control mb-1" name="urls" placeholder="https://example.com">
                <input type="text" class="form-control" name="url_names" placeholder="Optional name">
            </div>
            <button type="button" class="btn btn-sm btn-outline-danger" onclick="removeUrlInput(this)">❌</button>
        `;
        wrapper.appendChild(div);
    }

    function removeUrlInput(btn) {
        btn.closest('.url-input').remove();
    }