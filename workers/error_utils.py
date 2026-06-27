import traceback
from datetime import datetime

from django.conf import settings
from django.core.mail import EmailMultiAlternatives


def get_error_alert_recipients():
    recipients = getattr(settings, 'ERROR_ALERT_RECIPIENTS', None)
    if recipients:
        return recipients
    fallback = getattr(settings, 'EMAIL_HOST_USER', '')
    return [fallback] if fallback else []


def send_exception_alert(*, error_reference, request, exc):
    recipients = [email for email in get_error_alert_recipients() if email]
    if not recipients:
        return False, 'No error alert recipients configured.'

    user_display = 'Anonymous'
    if getattr(request, 'user', None) and request.user.is_authenticated:
        user_display = f'{request.user.username} ({request.user.email or "no-email"})'

    trace = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    context_lines = [
        f'Error reference: {error_reference}',
        f'Time (UTC): {datetime.utcnow().isoformat()}',
        f'Path: {request.path}',
        f'Method: {request.method}',
        f'User: {user_display}',
        f'Query string: {request.META.get("QUERY_STRING", "")}',
        f'Remote addr: {request.META.get("REMOTE_ADDR", "")}',
        '',
        'Traceback:',
        trace,
    ]
    body = '\n'.join(context_lines)
    subject = f'[Vashandi Error] {error_reference} on {request.path}'

    email = EmailMultiAlternatives(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipients,
    )
    try:
        email.send(fail_silently=False)
        return True, None
    except Exception as email_error:
        return False, str(email_error)
