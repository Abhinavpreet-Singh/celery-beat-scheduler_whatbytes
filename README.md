# Celery Beat Scheduler

Periodic tasks, dynamically created schedules and an email scheduler, built on
Celery Beat with Redis and django-celery-beat.

## Setup

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py setup_periodic_tasks
```

Copy `.env.example` to `.env` and add your Gmail address and app password.

## Running

```bash
docker run -d -p 6379:6379 redis:7-alpine
celery -A celery_scheduler worker -l info --pool=solo
celery -A celery_scheduler beat -l info
python manage.py runserver 8003
```

Dashboard at http://localhost:8003/, admin at /admin/.

## Periodic tasks

| Task | Schedule |
|------|----------|
| `daily_report_task` | every day at 9 AM |
| `weekly_cleanup_task` | Mondays at 2 AM |
| `hourly_status_check_task` | every hour |
| `send_occasion_emails` | weekdays at 10:30 AM |

Schedules live in the database, so they can be changed in the admin under Periodic
Tasks without restarting beat. All crontabs are stored with the Asia/Kolkata timezone.

## API

| Endpoint | Does |
|----------|------|
| POST `/api/schedule-task/` | create a schedule, one-off or recurring |
| POST `/api/schedule-email/` | send now, or later with `schedule_time` |
| GET `/api/scheduled-tasks/` | list everything scheduled |
| DELETE `/api/cancel-task/<id>/` | remove a schedule |
| GET `/api/task-history/` | recent task results |

Schedule a task three ways — `schedule_time` for a one-off, `crontab` for a cron
expression, or `every` plus `period` for an interval:

```bash
curl -X POST localhost:8003/api/schedule-task/ -H "Content-Type: application/json" \
  -d '{"task_name":"scheduler.tasks.daily_report_task","crontab":{"minute":"30","hour":"10","day_of_week":"1-5"}}'
```

Names get a uuid suffix when not given, so repeated calls do not collide.

Schedule an email for later:

```bash
curl -X POST localhost:8003/api/schedule-email/ -H "Content-Type: application/json" \
  -d '{"recipient":"someone@gmail.com","subject":"Hi","message":"Later","schedule_time":"2026-10-20T17:07:09"}'
```

## Timezones

Each user has an `EmailPreference` row holding their timezone, birthday and whether
they want campaigns. `send_occasion_emails` matches on today's month and day, then
renders the time in that person's own timezone before queueing the mail. Naive
datetimes coming in through the API are made aware with the project timezone.

## Retries

`email_scheduler_task` uses `retry_backoff=True` with `max_retries=3` and
`retry_backoff_max=600`, so a failing send waits 180s, then 360s, then caps at 600s.

## Monitoring

The dashboard at `/` lists every schedule and the twenty most recent results.
The same data is in the admin under Periodic Tasks and Task Results.

See TESTING.md for the full run with real output.

## Layout

```
celery_scheduler/celery.py    celery app
scheduler/
  models.py       EmailPreference
  tasks.py        periodic, email, campaign tasks
  scheduling.py   create_dynamic_task and friends
  views.py        api endpoints and dashboard
  templates/scheduler/dashboard.html
  management/commands/setup_periodic_tasks.py
```
