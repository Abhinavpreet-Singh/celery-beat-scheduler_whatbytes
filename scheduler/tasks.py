import logging
import zoneinfo
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import EmailPreference

logger = logging.getLogger(__name__)


@shared_task
def daily_report_task():
    now = timezone.localtime()
    count = EmailPreference.objects.count()
    logger.info('Daily report at %s for %s users', now, count)
    return {'ran_at': now.isoformat(), 'users': count}


@shared_task
def weekly_cleanup_task():
    from django_celery_results.models import TaskResult

    cutoff = timezone.now() - timedelta(days=7)
    removed, _ = TaskResult.objects.filter(date_done__lt=cutoff).delete()
    logger.info('Weekly cleanup removed %s old results', removed)
    return {'removed': removed}


@shared_task
def hourly_status_check_task():
    now = timezone.localtime()
    logger.info('Status check at %s', now)
    return {'status': 'ok', 'checked_at': now.isoformat()}


@shared_task(bind=True, max_retries=3, retry_backoff=True, retry_backoff_max=600, retry_jitter=False)
def email_scheduler_task(self, email_data):
    recipient = email_data['recipient']

    try:
        send_mail(
            email_data['subject'],
            email_data['message'],
            settings.DEFAULT_FROM_EMAIL,
            [recipient],
        )
    except Exception as exc:
        logger.error('Email to %s failed (attempt %s): %s', recipient, self.request.retries + 1, exc)
        raise self.retry(exc=exc)

    logger.info('Email sent to %s', recipient)
    return {'sent_to': recipient, 'subject': email_data['subject']}


def zone_for(name):
    try:
        return zoneinfo.ZoneInfo(name)
    except Exception:
        return timezone.get_current_timezone()


@shared_task
def send_occasion_emails(occasion='birthday'):
    today = timezone.localtime().date()
    field = 'birthday' if occasion == 'birthday' else 'anniversary'

    matches = EmailPreference.objects.filter(
        **{f'{field}__month': today.month, f'{field}__day': today.day}
    )

    for preference in matches:
        local_now = timezone.localtime(timezone=zone_for(preference.timezone))
        email_scheduler_task.delay({
            'recipient': preference.email,
            'subject': f'Happy {occasion}, {preference.user.username}',
            'message': f'Sent at {local_now:%Y-%m-%d %H:%M} in your timezone ({preference.timezone}).',
        })

    logger.info('%s emails queued for %s people', occasion, matches.count())
    return {'occasion': occasion, 'queued': matches.count()}


@shared_task
def campaign_task(campaign):
    recipients = EmailPreference.objects.filter(wants_campaigns=True)

    for preference in recipients:
        email_scheduler_task.delay({
            'recipient': preference.email,
            'subject': campaign['subject'],
            'message': campaign['message'],
        })

    return {'campaign': campaign['subject'], 'queued': recipients.count()}
