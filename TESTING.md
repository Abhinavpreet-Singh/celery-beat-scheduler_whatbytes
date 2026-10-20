# Testing

Everything below was run against the live setup: Redis on 6379, a worker, beat,
and the dev server on port 8003.

## Standing periodic tasks

```bash
python manage.py setup_periodic_tasks
```

```
created  Daily report              0 9 * * * (m/h/dM/MY/d) Asia/Kolkata
created  Weekly cleanup            0 2 * * 1 (m/h/dM/MY/d) Asia/Kolkata
created  Weekday birthday emails   30 10 * * 1-5 (m/h/dM/MY/d) Asia/Kolkata
created  Hourly status check       every hour
```

Daily at 9, Monday at 2, weekdays at 10:30, and an hourly interval. All stored in
the django-celery-beat tables, so they can be edited in the admin while beat runs.

## List scheduled tasks

```bash
curl localhost:8003/api/scheduled-tasks/
```

```
[1] Daily report              0 9 * * * (m/h/dM/MY/d) Asia/Kolkata
[2] Weekly cleanup            0 2 * * 1 (m/h/dM/MY/d) Asia/Kolkata
[3] Weekday birthday emails   30 10 * * 1-5 (m/h/dM/MY/d) Asia/Kolkata
[4] Hourly status check       every hour
```

## Create a task dynamically

Recurring, every 2 minutes:

```bash
curl -X POST localhost:8003/api/schedule-task/ -H "Content-Type: application/json" \
  -d '{"task_name":"scheduler.tasks.hourly_status_check_task","every":2,"period":"minutes"}'
```

```json
{"scheduled": {"id": 6, "name": "hourly_status_check_task-ece7d80e",
 "schedule": "every 2 minutes", "one_off": false}}
```

The name is generated with a uuid suffix so repeated calls never collide.

With a crontab instead, weekdays at 10:30:

```bash
curl -X POST localhost:8003/api/schedule-task/ -H "Content-Type: application/json" \
  -d '{"task_name":"scheduler.tasks.daily_report_task","crontab":{"minute":"30","hour":"10","day_of_week":"1-5"},"name":"Weekday 10:30 report"}'
```

```json
{"scheduled": {"id": 7, "schedule": "30 10 * * 1-5 (m/h/dM/MY/d) Asia/Kolkata"}}
```

## Send an email now

```bash
curl -X POST localhost:8003/api/schedule-email/ -H "Content-Type: application/json" \
  -d '{"recipient":"someone@gmail.com","subject":"Scheduler test","message":"Sent right away."}'
```

```json
{"task_id": "80eff2b6-98d2-4b20-abe3-083655d228b6", "status": "queued"}
```

Delivered, confirmed in the history as
`{"sent_to": "aroraabhinavpreetsingh@gmail.com"}`.

## Send an email later

Passing `schedule_time` creates a one-off ClockedSchedule instead of queueing now:

```bash
curl -X POST localhost:8003/api/schedule-email/ -H "Content-Type: application/json" \
  -d '{"recipient":"someone@gmail.com","subject":"Delayed email","message":"Scheduled.","schedule_time":"2026-10-20T17:07:09"}'
```

```json
{"scheduled_for": "2026-10-20T17:07:09+05:30",
 "task": {"name": "email_scheduler_task-0ac3341d", "one_off": true}}
```

Beat picked it up at the exact second:

```
[2026-10-20 17:07:09,018: INFO/MainProcess] Scheduler: Sending due task
email_scheduler_task-0ac3341d (scheduler.tasks.email_scheduler_task)
```

A naive datetime is made aware with the project timezone, which is why the response
comes back as +05:30.

## Birthday emails and timezones

Three users with different timezones, two with today's date as their birthday:

```
riya | Asia/Kolkata    | birthday today
john | America/New_York| birthday 1995-03-14
mei  | Asia/Tokyo      | birthday today
```

```python
send_occasion_emails.delay('birthday')
# {'occasion': 'birthday', 'queued': 2}
```

Only the two matching today were queued, and each message carries the time rendered
in that person's own timezone.

## Campaigns

```python
campaign_task.delay({'subject': 'October campaign', 'message': 'Campaign body text.'})
# {'campaign': 'October campaign', 'queued': 3}
```

Goes to everyone with `wants_campaigns` set.

## Retry with exponential backoff

Sending to a malformed address:

```
ERROR] Email to not a valid address failed (attempt 1): Invalid address ...
INFO]  Task ...email_scheduler_task[dbbd5c71] retry: Retry in 180s
```

`retry_backoff=True` doubles the wait each attempt (180s, 360s, then capped at 600
by `retry_backoff_max`), up to `max_retries=3`.

## Cancel a task

```bash
curl -X DELETE localhost:8003/api/cancel-task/6/
```

```json
{"cancelled": "hourly_status_check_task-ece7d80e"}
```

A missing id gives 404 `{"error": "Task not found"}`.

## History

```bash
curl localhost:8003/api/task-history/
```

```
email_scheduler_task   SUCCESS  {"sent_to": "aroraabhinavpreetsingh@gmail.com"...
email_scheduler_task   SUCCESS  {"sent_to": "mei@example.com", "subject": "Oct...
campaign_task          SUCCESS  {"campaign": "October campaign", "queued": 3}
send_occasion_emails   SUCCESS  {"occasion": "birthday", "queued": 2}
```

Read from the django-celery-results table, so the same rows show in the admin under
Task Results.

## Validation

| Request | Response |
|---------|----------|
| `schedule-email` with `{}` | 400, recipient, subject and message required |
| `schedule-task` with no schedule | 400, pass schedule_time, crontab or every |
| `cancel-task/999/` | 404 Task not found |
| GET on a POST endpoint | 405 POST required |
| malformed JSON | 400 invalid JSON body |
