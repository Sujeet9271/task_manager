from collections import defaultdict
from datetime import date, datetime, timedelta
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.http import QueryDict
from django.views.decorators.http import require_POST, require_GET, require_http_methods
from django.contrib.auth.decorators import login_required
from django.core.paginator import Page
from django.db.models import QuerySet, Count, Sum, Avg, Q
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_htmx.http import HttpResponseClientRedirect
from accounts.models import Users
from board.forms import BoardCreateForm, BoardForm, CommentForm, TaskCreateForm, TaskFilterForm, TaskForm
from board.models import Attachment, Board, BoardFilter, Column, Comments, Task
from board.permissions import IsBoardMemberOrReadOnly
from board.serializers import BoardSerializer, ColumnSerializer, TaskSerializer, BoardListSerializer
from board.filters import TaskFilter
from notifications.views import get_notifications
from task_manager.logger import logger


from django_filters.rest_framework import DjangoFilterBackend

from workspace.models import Workspace

import plotly.graph_objects as go
import json
import re



def task_lists(board_id:int, user:Users):
    board_filter = BoardFilter.objects.filter(board_id=board_id, user=user).only('filter').first()
    filters = Q(column__board_id=board_id, parent_task__isnull=True)
    if board_filter.filter:
        cd = board_filter.filter
        user_filter = Q()
        if cd.get('search'):
            filters &= Q(title__icontains=cd['search']) | Q(description__icontains=cd['search'])
        if cd.get('priority'):
            filters &= Q(priority=cd['priority'])
        if cd.get('is_complete') in ['true', 'false']:
            filters &= Q(is_complete=(cd['is_complete'] == 'true'))
        elif cd.get('is_complete')!='all':
            filters &= Q(is_complete=False)
        if cd.get('due_after'):
            filters &= Q(due_date__gte=cd['due_after'])
        if cd.get('due_before'):
            filters &= Q(due_date__lte=cd['due_before'])
        if cd.get('assigned_to'):
            user_filter &= Q(assigned_to__in=cd['assigned_to'])
        if cd.get('tags'):
            filters &= Q(tags__in=cd['tags'])
        logger.debug(f'{filters=}')
        if user_filter:
            logger.debug(f'{user_filter=}')
            tasks = Task.objects.prefetch_related('tags','assigned_to').filter(filters, user_filter).distinct()
        elif user.is_staff:
            tasks = Task.objects.prefetch_related('tags','assigned_to').filter(filters).distinct()
        else:
            tasks = user.assigned_tasks.prefetch_related('tags','assigned_to').filter(filters)
    elif user.is_staff:
        tasks = Task.objects.prefetch_related('tags','assigned_to').filter(filters).exclude(is_complete=True)
    else:
        logger.debug(f'{filters=}')
        tasks = user.assigned_tasks.prefetch_related('tags','assigned_to').filter(filters).exclude(is_complete=True)
    return tasks

def normalize_querydict(querydict: QueryDict) -> dict:
    """
    Converts a QueryDict to a standard dict:
    - Flattens single-item lists
    - Preserves multi-item lists
    """
    return {
        key: values if len(values) > 1 else values[0]
        for key, values in querydict.lists()
    }


@login_required
def search_boards(request):
    q = request.GET.get("board_search", "")
    boards:list[Board] = []
    if q:
        ids= Column.objects.select_related('board').filter(board__name__icontains=q, board__members=request.user).exclude(draft_column=True).values_list('board_id',flat=True)
        logger.debug(f'{ids=}')
        boards = request.user.board_memberships.select_related("workspace").filter(id__in=set(ids))
    return render(request, "boards/components/board_card_list.html", {"boards": boards})

@login_required
def load_columns(request, board_id):
    columns = Column.objects.filter(board_id=board_id).exclude(draft_column=True)
    return render(request, "boards/components/column_dropdown.html", {"columns": columns})


@login_required
def board_view(request, board_id):
    context:dict = {}
    board:Board = get_object_or_404(Board, pk=board_id, members=request.user)
    board_filter, _ = BoardFilter.objects.get_or_create(board=board, user=request.user)
    context['active_board'] = board
    context['board_filter'] = board_filter
    context['columns'] = board.columns.all()
    if request.htmx:
        context['board'] = board
        context['task_form'] = TaskForm(workspace=board.workspace, user=request.user,)
        triggers = {}
        triggers["boardLoaded"] = {"board_id":  board_id, "level": "info"}
        if request.method=='POST':
            logger.debug(f'{request.POST=}')
            if not request.POST.get('clear'):
                filter_form = TaskFilterForm(board=board, data=request.POST)
                q = QueryDict('', mutable=True)
                q.update(filter_form.data)
                logger.debug(f'{q=}')
                data = normalize_querydict(q)

                logger.debug(f'{data=}')
                board_filter.filter = data
                triggers["showToast"] = {"message":"Task Filtered", "level":"success"}
            else:
                board_filter.filter = {}
                board_filter.filter.pop('csrfmiddlewaretoken',None)
                triggers["showToast"] = {"message":"Task Filter Cleared", "level":"danger"}
            
            board_filter.save()
            triggers["filterSubmitted"] = {"board_id":  board_id, "level": "info"}
            triggers["closeModal"] = {"modal_id": "close_filterBoard", "level": "info"}
        context['filter_form'] = TaskFilterForm(board=board, initial=board_filter.filter)
        tasks = task_lists(board_id=board_id, user=request.user)
        column_map:dict[Column,list[Task]] = {column:[] for column in board.columns.all()}
        for task in tasks:
            if task.column not in column_map:
                column_map[task.column]=[]
            column_map[task.column].append(task)
        logger.debug(f'{column_map=}')
        context['column_map'] = column_map
        context['tasks'] = tasks
        response = render(request, 'boards/components/board.html', context)
        response['HX-Trigger'] = json.dumps(triggers)
    else:
        context['active_board'] = board
        context['boards'] = [board]
        context['workspace_id'] = board.workspace_id
        context['users'] = board.members.all()
        context['unread_notification_count'] = request.user.notifications.filter(read=False).count()
        context:dict = get_notifications(user=request.user, page_number=1, context=context)
        context['view_name'] = 'Board'
        context['board_create_form'] = BoardCreateForm(user=request.user)
        logger.debug(context)
        response = render(request, 'boards/index.html', context)
    return response

@login_required
def board_change_view(request, board_id, view):
    board:Board = get_object_or_404(Board, pk=board_id, members=request.user)
    board_filter = BoardFilter.objects.filter(user=request.user, board=board).first()
    board_filter.board_view = view
    board_filter.save(update_fields=['board_view'])
    return redirect('board:board-view',board_id=board_id)


@login_required
def board_reports(request, board_id):
    context:dict = {}
    board:Board = get_object_or_404(Board, pk=board_id, members=request.user)
    context['active_board'] = board
    logger.debug(board.created_at)
    context['boards'] = Board.objects.filter(workspace=board.workspace).only('id','name')
    
    board_tasks = Task.objects.filter(column__board=board, parent_task__isnull=True)
    # board_tasks = Task.objects.filter(column__board=board)
    tasks_by_priority = list(board_tasks.values('priority').annotate(count=Count('id')))
    tasks_by_column = list(board_tasks.values('column__name').annotate(count=Count('id')))
    
    aggregates = board_tasks.aggregate(
        total_tasks=Count('id'),
        completed_tasks=Count('id', filter=Q(is_complete=True)),
        incomplete_tasks=Count('id', filter=Q(is_complete=False)),
        overdue_tasks=Count('id', filter=Q(is_complete=False, due_date__lt=date.today())),
        high_priority_tasks=Count('id', filter=Q(priority='High')),
    )
    assigned_tasks = board_tasks.filter(assigned_to__isnull=False).distinct().count()
    task_summary = { **aggregates, 'assigned_tasks': assigned_tasks}
    logger.debug(f'{task_summary=}')
    context['task_summary'] = task_summary
    # Process data for Plotly
    priority_labels = [item["priority"] for item in tasks_by_priority]
    priority_values = [item["count"] for item in tasks_by_priority]

    column_labels = [item["column__name"] for item in tasks_by_column]
    column_values = [item["count"] for item in tasks_by_column]
    tasks = board_tasks.values(
        "title", "created_at", "updated_at", "priority", "column__name", "is_complete","due_date"
    )

    logger.debug(tasks)
    task_list:list[dict] = []
    today_date = date.today()

    for task in tasks:
        created: datetime = task["created_at"]
        updated: datetime = task["updated_at"]
        due_date: date = task.get("due_date")

        created_str = created.strftime("%Y-%m-%d")
        updated_str = updated.strftime("%Y-%m-%d")
        
        task_title = task["title"]
        column = task["column__name"]
        priority = task["priority"]

        if task["is_complete"]:
            # Segment 1: Active work time
            days = (updated.date() - created.date()).days
            task_list.append({
                "Task": task_title,
                "Start": created_str,
                "Finish": updated_str,
                "Resource": priority,
                "Column": column,
                "days": days,
            })

            if due_date:
                due_str = due_date.strftime("%Y-%m-%d")
                updated_date = updated.date()

                if updated_date < due_date:
                    # Segment 2: Unused time (Completed early)
                    days = (due_date - updated_date).days
                    task_list.append({
                        "Task": task_title,
                        "Start": updated_str,
                        "Finish": due_str,
                        "Resource": "Unused",
                        "Column": column,
                        "days": days
                    })

                elif updated_date > due_date:
                    # Segment 2: Late time (Completed after due)
                    days = (updated_date - due_date).days
                    task_list.append({
                        "Task": task_title,
                        "Start": due_str,
                        "Finish": updated_str,
                        "Resource": "Late",
                        "Column": column,
                        "days": days
                    })

        else:
            # Task is incomplete
            if due_date:
                due_str = due_date.strftime("%Y-%m-%d")
                today_str = today_date.strftime("%Y-%m-%d")

                if today_date < due_date:
                    # Segment 1: Work so far (Created to Today)
                    days = (today_date - created.date()).days
                    task_list.append({
                        "Task": task_title,
                        "Start": created_str,
                        "Finish": today_str,
                        "Resource": priority,
                        "Column": column,
                        "days": days
                    })

                    # Segment 2: Time remaining (Today to Due)
                    days = (due_date - today_date).days
                    task_list.append({
                        "Task": task_title,
                        "Start": today_str,
                        "Finish": due_str,
                        "Resource": "Remaining",
                        "Column": column,
                        "days": days
                    })

                elif today_date > due_date:
                    # Segment 1: Expected duration (Created to Due)
                    days = (due_date - created.date()).days
                    task_list.append({
                        "Task": task_title,
                        "Start": created_str,
                        "Finish": due_str,
                        "Resource": priority,
                        "Column": column,
                        "days": days
                    })

                    # Segment 2: Overdue duration
                    days = (today_date - due_date).days
                    task_list.append({
                        "Task": task_title,
                        "Start": due_str,
                        "Finish": today_str,
                        "Resource": "Overdue",
                        "Column": column,
                        "days": days
                    })

                else:
                    # Due today
                    days = (due_date - created.date()).days
                    task_list.append({
                        "Task": task_title,
                        "Start": created_str,
                        "Finish": due_str,
                        "Resource": priority,
                        "Column": column,
                        "days": days
                    })

            else:
                # No due date — only one segment
                days = (updated.date() - created.date()).days
                task_list.append({
                    "Task": task_title,
                    "Start": created_str,
                    "Finish": updated_str,
                    "Resource": priority,
                    "Column": column,
                    "days": days
                })
    # Define the sprint range manually or dynamically
    sprint_start:date = board.created_at.date()
    sprint_end:date = (board.created_at + timedelta(days=board.sprint_days)).date()

    # Get all tasks created within the sprint
    tasks = board_tasks.filter(created_at__date__lte=sprint_end)

    total_tasks = tasks.count()

    # Pre-fetch necessary fields
    task_data = tasks.values("is_complete", "updated_at")

    # Prepare task updated dates per day
    updated_count_by_day = defaultdict(int)
    incomplete_count = 0

    for task in task_data:
        if not task["is_complete"]:
            incomplete_count += 1
        updated_date = task["updated_at"].date()
        updated_count_by_day[updated_date] += 1

    # Precompute remaining tasks per date in reverse
    date_range = [sprint_start + timedelta(days=i) for i in range((sprint_end - sprint_start).days + 1)]
    remaining_tasks = []
    current_remaining = incomplete_count + sum(updated_count_by_day.values())

    for current_date in date_range:
        current_remaining -= updated_count_by_day.get(current_date, 0)
        remaining_tasks.append({
            "date": current_date.strftime("%Y-%m-%d"),
            "remaining": current_remaining
        })
    
    context.update({
        "priority_labels": json.dumps(priority_labels),
        "priority_values": json.dumps(priority_values),
        "column_labels": json.dumps(column_labels),
        "column_values": json.dumps(column_values),
        "tasks": json.dumps(task_list),
        "data": json.dumps(remaining_tasks),
        "total_tasks": total_tasks,
        "sprint_start": sprint_start,
        "sprint_end": sprint_end
    })
    return render(request,'boards/reports.html', context)



@require_http_methods(['POST'])
@login_required
def create_board(request):
    logger.info(request.session.get('workspace'))

    form = BoardCreateForm(data=request.POST, user=request.user)
    board = None
    if form.is_valid():
        board:Board = form.save(commit=False)
        board.created_by = form.user
        if request.POST.get('workspace_id'):
            board.workspace=Workspace.objects.filter(id=request.POST['workspace_id']).first()
            board.save()
            if not board.private:
                board.members.add(*board.workspace.members.all())
            else:
                board.members.add(request.user)
        else:
            board = form.save()
            board.members.add(request.user)
        response = render(request,'boards/components/board_list_item.html',{'board':board})
        if request.htmx:
            board_url = reverse('board:board-view',kwargs={'board_id':board.id}) 
            triggers = {"boardCreated":{"message":board_url,"level":"info"}}
            triggers["showToast"] = {"message":"New Board Created", "level":"success"}
            response['HX-Trigger']=json.dumps(triggers)
    else:
        logger.error(f'{form.errors.as_json()}')
        response = JsonResponse(form.errors.as_json(),safe=False)
        response['HX-Reswap'] = 'none'
    return response



@require_http_methods(['DELETE'])
@login_required
def delete_board(request, board_id,):
    board = get_object_or_404(Board, pk=board_id, created_by=request.user)
    board.delete()
    return HttpResponse(content='Board Deleted', status=200)  # Renders nothing for removal



@login_required
def board_invite_view(request, board_uuid):
    try:
        board = Board.objects.get(uuid=board_uuid)
        user = request.user

        if user not in board.workspace.members.all():
            return redirect('workspace:index')
        
        if user in board.members.all():
            # Already a member, redirect to board index
            return redirect('board:board-view', board_id=board.id)

        if request.method == 'POST':
            # User confirms joining
            board.members.add(user)
            return redirect('board:board-view', board_id=board.id)

        # Show confirmation page
        return render(request, 'boards/invite_confirmation.html', {
            'board': board
        })
    except Board.DoesNotExist:
        return redirect('board:index')



@require_http_methods(['GET', 'POST'])
@login_required
def create_column(request, board_id):
    board = get_object_or_404(Board, pk=board_id, members=request.user)
    if request.method == 'POST':
        column = Column.objects.create(name=request.POST.get('name'), board=board, created_by=request.user)
        response = render(request,'boards/components/column_list_item.html',{'column':column,'board_id':board_id})
        if request.htmx:
            board_url = reverse('board:board-view',kwargs={'board_id':board_id}) 
            triggers = {"columnCreated":{"message":board_url,"level":"info"}}
            triggers["showToast"] = {"message":"New Column Added", "level":"success"}
            response['HX-Trigger']=json.dumps(triggers)
        return response
    return render(request, 'boards/components/column_create.html', {'board': board,})

@require_http_methods(['POST'])
@login_required
def update_column_name(request, board_id, column_id):
    column = get_object_or_404(Column, pk=column_id, board_id=board_id, board__members=request.user)
    name = request.POST.get('column_name')
    if name:
        column.name = name
        column.updated_by = request.user
        column.save(update_fields=['name','updated_by','updated_at'])
    response = HttpResponse(content='Column Name Updated', status=200)  # Renders nothing for removal
    if request.htmx:
        triggers = {"columnUpdated": {"level": "info","column_id":column_id,"board_id":board_id, "column_name": column.name}}
        triggers['showToast'] = {'message':'Column name updated', 'level':'success'}
        response['HX-Trigger'] = json.dumps(triggers)
    return response


@require_http_methods(['DELETE'])
@login_required
def delete_column(request, board_id, column_id):
    column = get_object_or_404(Column, pk=column_id, board_id=board_id, created_by=request.user)
    column.delete()    
    response = HttpResponse(content='Column Deleted', status=200)  # Renders nothing for removal
    if request.htmx:
        triggers = {"columnDeleted": {"level": "info","create_column_url":reverse('board:column-create',kwargs={'board_id':board_id}), "column_list_item": f"board_{board_id}_column_{column_id}"}}
        triggers['showToast'] = {'message':'Column Deleted', 'level':'danger'}
        response['HX-Trigger'] = json.dumps(triggers)
    return response


@require_GET
@login_required
def get_task_lists(request, board_id, column_id):
    column = get_object_or_404(Column, pk=column_id, board_id=board_id, board__members=request.user)
    board_filter = BoardFilter.objects.filter(board_id=board_id, user=request.user).first()
    logger.debug(f'{board_filter=}')
    if board_filter:
        cd = board_filter.filter
        if cd.get('search'):
            filters &= Q(title__icontains=cd['search']) | Q(description__icontains=cd['search'])
        if cd.get('priority'):
            filters &= Q(priority=cd['priority'])
        if cd.get('is_complete') in ['true', 'false']:
            filters &= Q(is_complete=(cd['is_complete'] == 'true'))
        if cd.get('due_after'):
            filters &= Q(due_date__gte=cd['due_after'])
        if cd.get('due_before'):
            filters &= Q(due_date__lte=cd['due_before'])
        if cd.get('assigned_to'):
            filters &= Q(assigned_to__in=cd['assigned_to'])
        if cd.get('tags'):
            filters &= Q(tags__in=cd['tags'])
        logger.debug(f'{filters=}')
        tasks = Task.objects.prefetch_related('tags',).filter(filters, column_id=column_id,).distinct()
        # tasks = column.tasks.filter(assigned_to=request.user, parent_task__isnull=True) if not request.user.is_staff else column.tasks.filter(parent_task__isnull=True)
    else:
        tasks = column.tasks.filter(assigned_to=request.user, parent_task__isnull=True) if not request.user.is_staff else column.tasks.filter(parent_task__isnull=True)
    return render(request, 'boards/components/column.html', {'column': column,'tasks':tasks})



def sub_task_list(user:Users,task:Task,context:dict=dict):
    context['task'] = task
    context['sub_tasks'] = task.sub_tasks.filter(assigned_to=user) if not user.is_staff else task.sub_tasks.all()
    return context



@require_GET
@login_required
def get_sub_task_lists(request, board_id, column_id, task_id):
    context={'board_id':board_id, 'column_id':column_id, 'task_id':task_id}
    task:Task = get_object_or_404(Task, pk=task_id, column_id=column_id, column__board_id=board_id, column__board__members=request.user, assigned_to=request.user)
    context = sub_task_list(user=request.user,task=task, context=context)
    return render(request, 'boards/components/sub_task_list.html', context)

@require_http_methods(['POST'])
@login_required
def create_sub_task(request, board_id, column_id, task_id):
    task: Task = get_object_or_404(
        Task,
        pk=task_id,
        column_id=column_id,
        column__board_id=board_id,
        column__board__members=request.user,
        assigned_to=request.user
    )

    # Prevent creating a sub-task of a sub-task
    if task.parent_task:
        return HttpResponseForbidden("Cannot create a sub-task of a sub-task.")

    form = TaskCreateForm(data=request.POST)
    context = {
        'task_id': task_id,
        'column_id': column_id,
        'board_id': board_id
    }

    if form.is_valid():
        instance: Task = form.save(commit=False)
        instance.parent_task = task
        instance.column = task.column
        instance.created_by = request.user
        instance.save()

        # Assign to creator and parent task creator
        assigned_users = {instance.created_by, task.created_by}
        instance.assigned_to.add(*assigned_users)

        context['sub_task'] = instance
        response = render(request, 'boards/components/sub_task_card.html', context)
        triggers = {
            'subTaskCreated': {
                "level": "info",
                "column_id": column_id,
                "board_id": board_id,
                "task_id": task_id
            }
        }
        triggers["showToast"] = {"message":"Sub Task Added", "level":"success"}
        response['HX-Trigger'] = json.dumps(triggers)
        return response

    # If form is invalid
    context['form'] = form
    response = render(request, 'boards/components/sub_task_create.html', context)
    triggers = {
        'subTaskCreateFailed': {
            "level": "info",
            "column_id": column_id,
            "board_id": board_id,
            "task_id": task_id
        }
    }
    triggers["showToast"] = {"message":"Failed to add Sub Task", "level":"danger"}
    response['HX-Trigger'] = json.dumps(triggers)
    return response


@require_POST
@login_required
def create_task(request, board_id,):
    column = get_object_or_404(Column, board_id=board_id, board__members=request.user, draft_column=True)
    form = TaskForm(workspace=column.board.workspace,user=request.user,data=request.POST)
    if form.is_valid():
        instance:Task = form.save(commit=False)
        instance.column = column
        instance.created_by = request.user
        instance.save()
        form.save_m2m()

        assigned_to = [instance.created_by]
        if instance.parent_task:
            assigned_to.append(instance.parent_task.created_by)
        instance.assigned_to.add(*assigned_to)

        board_filter  = BoardFilter.objects.filter(user=request.user, board=column.board).first()
        if not board_filter:
            board_filter = BoardFilter(user=request.user, board_id=board_id).save()

        if board_filter.board_view=='table':
            response = render(request, 'boards/components/task_row.html', {'board_id': board_id, 'task': instance, 'columns':board_filter.board.columns.all()})
            response['HX-Reswap'] = "afterbegin"
            response['HX-Retarget'] = '#task_table'
        else:
            response = render(request, 'boards/components/task_card_new.html', {'board_id': board_id, 'task': instance})
            response['HX-Reswap'] = "beforeend"
            response['HX-Retarget'] = '#draft_tasks_list'
    
        triggers = {}
        triggers["reloadTaskList"] = {"get_task_lists": reverse('board:get_task_lists', kwargs={'board_id': board_id,'column_id':column.id}),'column_id':column.id,'board_id':board_id, "level": "info"}
        triggers["closeModal"] = {"modal_id": "close_addTaskModal", "level": "info"}
        triggers["showToast"] = {"message":"New Task Created", "level":"success"}
        response['HX-Trigger'] = json.dumps(triggers)
        return response
    response = render(request,'boards/components/create.html',{'board_id':board_id,'column_id':column.id, 'form':form})
    triggers = {}
    triggers["showToast"] = {"message":"Failed to create New Task", "level":"danger"}
    response['HX-Trigger'] = json.dumps(triggers)
    return response


@require_http_methods(['GET','POST'])
@login_required
def detail_task(request, board_id, column_id, task_id):
    task = Task.objects.prefetch_related('tags','assigned_to','comments').filter(pk=task_id, column_id=column_id, column__board_id=board_id, column__board__members=request.user,).first()
    if not task:
        response = HttpResponse(content='Something went wrong',status=404)
        triggers = {}
        triggers["showToast"] = {"message":"No Task Found", "level":"warning"}
        response['HX-Trigger'] = json.dumps(triggers)
        return response
    context = {'task':task,'board_id':board_id,'column_id':column_id}
    context['mentionable_users'] = ",".join(task.assigned_to.all().values_list('username',flat=True))
    return render(request,'boards/components/task_detail.html',context)

@require_http_methods(['GET','POST'])
@login_required
def task_move(request, board_id, column_id, task_id):
    task = Task.objects.select_related('column','column__board').prefetch_related('tags','assigned_to','comments').filter(pk=task_id, column_id=column_id, column__board_id=board_id, column__board__members=request.user, created_by=request.user).first()
    if not task:
        response = HttpResponse(content='Something went wrong',status=404)
        triggers = {}
        triggers["showToast"] = {"message":"No Task Found", "level":"warning"}
        response['HX-Trigger'] = json.dumps(triggers)
        return response
    
    triggers = {}
    if request.method=='POST':
        new_board_id = request.POST.get("board")
        new_column_id = request.POST.get("column")
        convert = request.POST.get("convert_to_main_task")

        if new_board_id and new_column_id:
            old_column = task.column
            task.column_id = new_column_id
            if task.parent_task and convert == "on":
                task.parent_task.total_sub_tasks -= 1
                if task.parent_task.completed_sub_tasks>0:
                    task.parent_task.completed_sub_tasks -= 1
                task.parent_task.save()
                task.parent_task = None
            task.save()
            if task.column.board == old_column.board:
                board_filter = BoardFilter.objects.filter(user=request.user, board_id=board_id).first()
                if not board_filter:
                    board_filter = BoardFilter(user=request.user, board_id=board_id).save()
                    
                if board_filter.board_view == 'card':
                    response = render(request,'boards/components/task_card_new.html',{'task':task,'board_id':board_id})
                    response['HX-Retarget'] = f'#tasks_list_{new_column_id}'
                    response['HX-Reswap'] = 'beforeend'
                else:
                    response = render(request,'boards/components/task_row.html',{'task':task,'board_id':board_id, 'columns':board_filter.board.columns.all()})

                triggers["closeModal"] = {"modal_id": "close_editTaskModal", "level": "info"}
                triggers["showToast"] = {"message":"Task Moved", "level":"success"}
                triggers["taskEdited"] = {"message": reverse('board:board-view', kwargs={'board_id': board_id}), "level": "info"}
                response['HX-Trigger'] = json.dumps(triggers)
                return response
            if task.column.board.workspace_id:
                url = f"{reverse('workspace:get_workspace_boards', kwargs={'workspace_id':task.column.board.workspace_id})}?active_board={new_board_id}"
            else:
                url = reverse('board:board-view', kwargs={'board_id':new_board_id})
            return HttpResponseClientRedirect(url)
        triggers["showToast"] = {"message":"Couldn't move task", "level":"danger"}
    context = {'task':task,'board_id':board_id,'column_id':column_id}
    context['boards'] = request.user.board_memberships.all().order_by('workspace')
    context['columns'] = task.column.board.columns.all().exclude(draft_column=True)
    response = render(request,'boards/components/task_move.html',context)
    if triggers:
        response['HX-Trigger'] = json.dumps(triggers)
    return response




@require_http_methods(['GET'])
@login_required
def history_task(request, board_id, column_id, task_id):
    task = Task.objects.prefetch_related('tags','assigned_to','comments').filter(pk=task_id, column_id=column_id, column__board_id=board_id, column__board__members=request.user,).first()
    if not task:
        response = HttpResponse(content='Something went wrong',status=404)
        triggers = {}
        triggers["showToast"] = {"message":"No Task Found", "level":"warning"}
        response['HX-Trigger'] = json.dumps(triggers)
        return response
    context = {'task':task, 'histories':task.history.all(),'board_id':board_id,'column_id':column_id}
    context['mentionable_users'] = ",".join(task.assigned_to.all().values_list('username',flat=True))
    return render(request,'boards/components/task_history.html',context)


@require_http_methods(['GET','POST'])
@login_required
def edit_task(request, board_id, column_id, task_id):
    task:Task = get_object_or_404(Task, pk=task_id, column_id=column_id, column__board_id=board_id, column__board__members=request.user,)
    context = {'task':task,'board_id':board_id,'column_id':column_id}
    if task.created_by!=request.user and not task.assigned_to.filter(id=request.user.id).exists():
        response = render(request,'boards/components/task_detail.html', context)
        triggers = {}
        triggers["showToast"] = {"message":"You've no access to edit this task", "level":"danger"}
        response['HX-Trigger'] = json.dumps(triggers)
        return response
    form = TaskForm(workspace=task.column.board.workspace, user=request.user,instance=task, data=request.POST or None)
    context['mentionable_users'] = ",".join(task.assigned_to.all().values_list('username',flat=True))
    if request.method=='POST':
        if form.is_valid():
            assigned_to = form.cleaned_data.get('assigned_to')
            tags = form.cleaned_data.get('tags')
            assigned_to_list = list(assigned_to)

            assigned_to_list.extend([task.created_by,request.user])
            if task.parent_task:
                assigned_to_list.append(task.parent_task.created_by)

            task:Task = form.save(commit=False)
            task.updated_by = request.user

            task.save()

            task.assigned_to.set(assigned_to_list)
            task.tags.set(tags)

            files = request.FILES.getlist('attachments')
            urls = request.POST.getlist('urls')
            url_names = request.POST.getlist('url_names')
            attachment_list = []
            # Upload files
            for file in files:
                attachment_list.append(
                Attachment(
                    workspace=form.workspace,
                    task=task,
                    file=file,
                    type='file',
                    file_type=file.content_type,
                    uploaded_by=request.user
                ))

            # Store links
            for url, name in zip(urls, url_names):
                if url.strip():  # skip blanks
                    attachment_list.append(
                    Attachment(
                        workspace=form.workspace,
                        task=task,
                        type='url',
                        url=url.strip(),
                        name=name.strip() or None,
                        uploaded_by=request.user
                    ))

            if attachment_list:
                Attachment.objects.bulk_create(attachment_list)
            if request.htmx:
                context['form'] = form
                response = render(request,'boards/components/task_detail.html',context)
                triggers = {"taskEdited": {"message": reverse('board:board-view', kwargs={'board_id': board_id}), "level": "info"}}
                triggers["showToast"] = {"message":"Sub Task Saved", "level":"success"}
                if not task.parent_task:
                    # triggers["closeModal"] = {"modal_id": "close_editTaskModal", "level": "info"}
                    triggers["showToast"] = {"message":"Task Saved", "level":"success"}
                response['HX-Trigger'] = json.dumps(triggers)
                response['HX-Reswap'] = 'innerHTML'
                response['HX-Retarget'] ='#edit_task_modal'
                return response
    
        logger.info(f'{form.errors.as_json()=}')
        if request.htmx:
            context['form'] = form
            response = render(request,'boards/components/edit_form.html',context)
            return response

    comments = Comments.objects.select_related('added_by').filter(task=task).order_by('created_at')
    comment_form = CommentForm()
    context['form'] = form
    context['comments'] = comments
    context['comment_form'] = comment_form
    if not task.parent_task:
        context = sub_task_list(user=request.user, task=task, context=context)
    return render(request,'boards/components/task_edit.html',context)
    
    


@require_http_methods(['POST'])
@login_required
def add_comment(request, task_id):
    task = get_object_or_404(Task, pk=task_id, column__board__members=request.user, assigned_to=request.user)
    form = CommentForm(data=request.POST)
    if form.is_valid():
        comment:Comments = form.save(commit=False)
        comment.added_by = request.user
        comment.task = task
        comment.save()
        mentions = re.findall(r'@([a-zA-Z0-9_]+)', comment.comment)
        if mentions:
            mentioned_users = Users.objects.filter(username__in=mentions)
            comment.mentioned_users.set(mentioned_users)
        response = render(request,'boards/components/comment.html',{'comment':comment})
        triggers = {
                        'commentAdded': {
                            "level": "info",
                            "message": 'Comment Added',
                        }
                    }
        response['HX-Trigger'] = json.dumps(triggers)
        return response
    return HttpResponse(content=form.errors.as_json(), status=400)


@require_http_methods(['POST'])
@login_required
def task_status_toggle(request, board_id, column_id, task_id):
    task:Task = Task.objects.filter(pk=task_id, column_id=column_id, column__board_id=board_id,).first()
    triggers = {}
    if task.created_by != request.user and not task.assigned_to.filter(id=request.user.id).exists():
        triggers["showToast"] = {"message":"You have no permission to complete this task", "level":"danger"}
        response = HttpResponse(content='Access Denied',status=403)
        response['HX-Trigger'] = json.dumps(triggers)
        return response
    
    if task.is_complete:
        task.is_complete = False
    else:
        task.is_complete = True
    task.save(update_fields=['is_complete','updated_at'])
    if task.parent_task:
        if task.is_complete:
            task.parent_task.completed_sub_tasks += 1
        elif task.parent_task.completed_sub_tasks > 0:
            task.parent_task.completed_sub_tasks -= 1
        task.parent_task.save(update_fields=['completed_sub_tasks'])
        response = render(request,'boards/components/sub_task_card.html',{'sub_task':task,"board_id":board_id,"column_id":column_id})
        triggers["showToast"] = {"message":"Sub-Task marked as complete" if task.is_complete else "Sub-Task marked as incomplete", "level":"success" if task.is_complete else "danger"}
    else:
        board_filter = BoardFilter.objects.filter(user=request.user, board_id=board_id).first()
        if not board_filter:
            board_filter = BoardFilter(user=request.user, board_id=board_id).save()
        
        if board_filter.board_view == 'card':
            response = render(request,'boards/components/task_card_new.html',{'task':task,"board_id":board_id,"column_id":column_id})
        else:
            response = render(request,'boards/components/task_row.html',{'task':task,"board_id":board_id,"column_id":column_id, 'columns':board_filter.board.columns.all()})

        triggers["showToast"] = {"message":"Task marked as complete" if task.is_complete else "Task marked as incomplete", "level":"success" if task.is_complete else "danger"}
    response['HX-Trigger'] = json.dumps(triggers)
    if not task.is_complete:
        response['HX-Reswap'] = 'outerHTML'
    return response

@require_http_methods(['DELETE'])
@login_required
def delete_task(request, board_id, column_id, task_id):
    task:Task = Task.objects.filter(pk=task_id, column_id=column_id, column__board_id=board_id,).first()
    triggers = {}
    if task.created_by != request.user and not task.assigned_to.filter(id=request.user.id).exists():
        triggers["showToast"] = {"message":"You have no permission to delete this task", "level":"danger"}
        response = HttpResponse(content='Access Denied',status=403)
        response['HX-Trigger'] = json.dumps(triggers)
        return response
    
    task.delete()
    triggers = {}
    triggers["showToast"] = {"message":"Task Deleted", "level":"success"}
    if request.GET.get('from') and request.GET['from'] == 'task_detail':
        triggers["closeModal"] = {"modal_id": "close_editTaskModal", "level": "info"}

    response = HttpResponse(content='Task Deleted',status=200)  # Renders nothing for removal
    response['HX-Trigger'] = json.dumps(triggers)
    return response

@require_POST
@login_required
def move_task(request, task_id):
    new_column_id = request.POST.get('column_id')
    try:
        task = Task.objects.get(id=task_id,)
        triggers = {}
        logger.debug(f'{task.created_by=}')
        logger.debug(f'{request.user=}')
        logger.debug(f'{task.assigned_to.filter(id=request.user.id)=}')
        if task.created_by != request.user and not task.assigned_to.filter(id=request.user.id).exists():
            response = HttpResponse(status=403)
            triggers["showToast"] = {"message":"You have no access to move this task", "level":"danger"}
            response['HX-Trigger'] = json.dumps(triggers)
            return response
        
        column = Column.objects.get(id=new_column_id)
        kwargs = {
            'board_id':column.board_id,
            'column_id':column.id,
            'task_id':task_id
        }
        urls = {
            f'task_toggle_{task_id}':{'post':reverse('board:task-status-toggle', kwargs=kwargs)},
            f'task_title_{task_id}':{'get':reverse('board:task-detail', kwargs=kwargs)},
            f'task_delete_{task_id}':{'delete':reverse('board:task-delete', kwargs=kwargs)},
        }
        if task.column == column:
            return JsonResponse({'success': True,'urls':urls})
        
        task.column = column
        task.save()

        if task.total_sub_tasks > 0:
            task.sub_tasks.all().update(column=task.column)


        board_filter = BoardFilter.objects.filter(user=request.user, board_id=column.board_id).first()
        if not board_filter:
            board_filter = BoardFilter(user=request.user, board=column.board).save()

        if board_filter.board_view == 'table':
            response = render(request, 'boards/components/task_row.html', {'board_id': column.board_id, 'task': task, 'columns':board_filter.board.columns.all()})
            response['HX-Reswap'] = "outerHTML"
            response['HX-Retarget'] = f'#task_{task_id}'
        else:
            response = JsonResponse({'success': True,'urls':urls})
        
        triggers["showToast"] = {"message":"Task moved successfully", "level":"success"}
        response['HX-Trigger'] = json.dumps(triggers)
        # triggers = {"reloadTaskList": {"get_task_lists": reverse('board:get_task_lists', kwargs={'board_id': column.board_id,'column_id':old_column_id}),'column_id':old_column_id,'board_id':column.board_id, "level": "info"}}
        # response['HX-Trigger'] = json.dumps(triggers)
        return response
    except (Task.DoesNotExist, Column.DoesNotExist):
        response = JsonResponse({'success': False}, status=400)
        triggers = {}
        triggers["showToast"] = {"message":"Something went wrong", "level":"success"}
        response['HX-Trigger'] = json.dumps(triggers)
        return response



class BoardViewSet(viewsets.ModelViewSet):
    queryset = Board.objects.all()
    serializer_class = BoardSerializer
    permission_classes = [IsBoardMemberOrReadOnly]
    

    @action(detail=True, methods=['get'])
    def tasks(self, request, pk=None):
        board = self.get_object()
        tasks = Task.objects.filter(column__board=board)
        serializer = TaskSerializer(tasks, many=True)
        return Response(serializer.data)
    
    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        instance.members.add(self.request.user)  # Add the creator as a member of the board

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save(update_fields=['is_deleted', 'deleted_at'])

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = BoardListSerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        logger.info(f'{kwargs=}')
        instance = self.get_object()
        logger.info(f'{instance=}')

        if not instance:
            return Response({"detail": "Board not found"}, status=404)

        # Return the column details using the serializer
        serializer = BoardSerializer(instance)
        return Response(serializer.data)
    
    


class ColumnViewSet(viewsets.ModelViewSet):
    queryset = Column.objects.all()
    serializer_class = ColumnSerializer

    def get_queryset(self):
        """
        Return columns for the specified board.
        """
        board_id = self.kwargs.get('board_id')
        if board_id:
            return Column.objects.filter(board_id=board_id)
        return super().get_queryset()
    

    def perform_create(self, serializer):
        board_id = self.kwargs.get('board_id')
        board = Board.objects.get(id=board_id)
        serializer.save(board=board, created_by=self.request.user)

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save(update_fields=['is_deleted', 'deleted_at'])

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    

class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['column', 'assigned_to']
    search_fields = ['title', 'description']
    ordering_fields = ['due_date', 'priority', 'created_at']

    def get_queryset(self):
        """
        Return columns for the specified board.
        """
        board_id = self.kwargs.get('board_id')
        if board_id:
            column_id = self.kwargs.get('column_id')
            if column_id:
                return Task.objects.filter(column__board_id=board_id,column_id=column_id)
            return Task.objects.filter(column__board_id=board_id)
        return super().get_queryset()
    

    def perform_create(self, serializer):
        board_id = self.kwargs.get('board_id')
        column_id = self.kwargs.get('column_id')
        column = Column.objects.get(id=column_id, board_id=board_id)
        instance:Task = serializer.save(column=column, created_by=self.request.user)
        instance.assigned_to.add(self.request.user)


    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save(update_fields=['is_deleted', 'deleted_at'])


    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)



