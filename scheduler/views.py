import json
from datetime import datetime

from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django_celery_beat.models import PeriodicTask
from django_celery_results.models import TaskResult

from .scheduling import create_dynamic_task, describe
from .tasks import email_scheduler_task


def parse_body(request):
    try:
        return json.loads(request.body or '{}'), None
    except json.JSONDecodeError:
        return None, 'invalid JSON body'


def parse_time(value):
    parsed = datetime.fromisoformat(value)
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed)
    return parsed


@csrf_exempt
def schedule_task(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    data, error = parse_body(request)
    if error:
        return JsonResponse({'errors': [error]}, status=400)

    task_name = data.get('task_name')
    if not task_name:
        return JsonResponse({'errors': ['task_name is required']}, status=400)

    try:
        task = create_dynamic_task(
            task_name,
            schedule_time=parse_time(data['schedule_time']) if data.get('schedule_time') else None,
            args=data.get('args'),
            kwargs=data.get('kwargs'),
            crontab=data.get('crontab'),
            every=data.get('every'),
            period=data.get('period', 'minutes'),
            name=data.get('name'),
            timezone_name=data.get('timezone', 'Asia/Kolkata'),
        )
    except ValueError as exc:
        return JsonResponse({'errors': [str(exc)]}, status=400)

    return JsonResponse({'scheduled': describe(task)}, status=201)


@csrf_exempt
def schedule_email(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    data, error = parse_body(request)
    if error:
        return JsonResponse({'errors': [error]}, status=400)

    missing = [f for f in ('recipient', 'subject', 'message') if not data.get(f)]
    if missing:
        return JsonResponse({'errors': [f'{f} is required' for f in missing]}, status=400)

    email_data = {k: data[k] for k in ('recipient', 'subject', 'message')}

    if data.get('schedule_time'):
        when = parse_time(data['schedule_time'])
        task = create_dynamic_task('scheduler.tasks.email_scheduler_task',
                                   schedule_time=when, args=[email_data])
        return JsonResponse({'scheduled_for': when.isoformat(), 'task': describe(task)}, status=201)

    result = email_scheduler_task.delay(email_data)
    return JsonResponse({'task_id': result.id, 'status': 'queued'}, status=202)


def scheduled_tasks(request):
    tasks = [describe(t) for t in PeriodicTask.objects.exclude(name__startswith='celery.')]
    return JsonResponse({'count': len(tasks), 'tasks': tasks})


@csrf_exempt
def cancel_task(request, task_id):
    if request.method not in ('DELETE', 'POST'):
        return JsonResponse({'error': 'DELETE required'}, status=405)

    task = PeriodicTask.objects.filter(pk=task_id).first()
    if task is None:
        return JsonResponse({'error': 'Task not found'}, status=404)

    name = task.name
    task.delete()
    return JsonResponse({'cancelled': name})


def task_history(request):
    results = TaskResult.objects.order_by('-date_done')[:50]
    return JsonResponse({
        'count': results.count(),
        'results': [{
            'task_id': r.task_id,
            'name': r.task_name,
            'status': r.status,
            'result': r.result,
            'date_done': r.date_done.isoformat() if r.date_done else None,
        } for r in results],
    })


def dashboard(request):
    return render(request, 'scheduler/dashboard.html', {
        'tasks': PeriodicTask.objects.exclude(name__startswith='celery.'),
        'results': TaskResult.objects.order_by('-date_done')[:20],
    })
