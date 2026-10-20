import json
import uuid

from django_celery_beat.models import ClockedSchedule, CrontabSchedule, IntervalSchedule, PeriodicTask


def unique_name(prefix):
    return f'{prefix}-{uuid.uuid4().hex[:8]}'


def create_dynamic_task(task_name, schedule_time=None, args=None, kwargs=None, crontab=None,
                        every=None, period='minutes', name=None, timezone_name='Asia/Kolkata'):
    name = name or unique_name(task_name.split('.')[-1])
    options = {
        'task': task_name,
        'args': json.dumps(args or []),
        'kwargs': json.dumps(kwargs or {}),
    }

    if schedule_time is not None:
        clocked, _ = ClockedSchedule.objects.get_or_create(clocked_time=schedule_time)
        options.update(clocked=clocked, one_off=True)
    elif crontab is not None:
        schedule, _ = CrontabSchedule.objects.get_or_create(timezone=timezone_name, **crontab)
        options.update(crontab=schedule)
    elif every is not None:
        schedule, _ = IntervalSchedule.objects.get_or_create(
            every=every, period=getattr(IntervalSchedule, period.upper())
        )
        options.update(interval=schedule)
    else:
        raise ValueError('pass schedule_time, crontab or every')

    return PeriodicTask.objects.create(name=name, **options)


def describe(task):
    return {
        'id': task.id,
        'name': task.name,
        'task': task.task,
        'schedule': str(task.crontab or task.interval or task.clocked),
        'args': task.args,
        'kwargs': task.kwargs,
        'enabled': task.enabled,
        'one_off': task.one_off,
        'last_run_at': task.last_run_at.isoformat() if task.last_run_at else None,
        'total_run_count': task.total_run_count,
    }
