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
		document.getElementById("close_createBoardModal").click();
		board_url = evt.detail.message;
		htmx.ajax("GET", board_url, { target: "#main-content", swap: "innerHTML" });
	});
	htmx.on("reloadBoard", function (evt) {
		document.getElementById("close_createColumnModal").click();
		board_url = evt.detail.message;
		htmx.ajax("GET", board_url, { target: "#main-content", swap: "innerHTML" });
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
		document.getElementById("close_editTaskModal").click();
	});

	htmx.on("taskCreated", function (evt) {
		document.getElementById(`create_task_form_${column_id}`).reset();
		board_id = evt.detail.board_id;
		column_id = evt.detail.column_id;
		get_task_lists = evt.detail.get_task_lists;
		
		//htmx.ajax("GET", get_task_lists, { target: `#tasks_list_${column_id}`, swap: "innerHTML" });
		
		no_task = document.getElementById(`column_${column_id}_no_task`);
		if (no_task) {
			no_task.remove();
		}

	});