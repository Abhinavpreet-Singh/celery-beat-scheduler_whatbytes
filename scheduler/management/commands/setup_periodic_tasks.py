from django.core.management.base import BaseCommand
from django_celery_beat.models import CrontabSchedule, IntervalSchedule, PeriodicTask

TIMEZONE = 'Asia/Kolkata'

CRON_TASKS = [
    ('Daily report', 'scheduler.tasks.daily_report_task', {'minute': '0', 'hour': '9'}),
    ('Weekly cleanup', 'scheduler.tasks.weekly_cleanup_task',
     {'minute': '0', 'hour': '2', 'day_of_week': '1'}),
    ('Weekday birthday emails', 'scheduler.tasks.send_occasion_emails',
     {'minute': '30', 'hour': '10', 'day_of_week': '1-5'}),
]


class Command(BaseCommand):
    help = 'Create the standing periodic tasks'

    def handle(self, *args, **options):
        for name, task, crontab in CRON_TASKS:
            schedule, _ = CrontabSchedule.objects.get_or_create(timezone=TIMEZONE, **crontab)
            obj, created = PeriodicTask.objects.get_or_create(
                name=name, defaults={'task': task, 'crontab': schedule}
            )
            self.stdout.write(f'{"created" if created else "exists "}  {name}  ({schedule})')

        hourly, _ = IntervalSchedule.objects.get_or_create(every=1, period=IntervalSchedule.HOURS)
        obj, created = PeriodicTask.objects.get_or_create(
            name='Hourly status check',
            defaults={'task': 'scheduler.tasks.hourly_status_check_task', 'interval': hourly},
        )
        self.stdout.write(f'{"created" if created else "exists "}  Hourly status check  (every hour)')
