import logging

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


@shared_task
def send_login_notification_email(user_id):
    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return
    if not user.email:
        return

    subject = 'New Login Alert to Your Account - Django'
    message = f'Hi {user.username},\n\nWe noticed a new login to your account. If this was you, no further action is needed!'
    try:
        html_message = render_to_string('email.html', {'user': user, 'subject': subject, 'message': message})
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False, html_message=html_message)
    except Exception:
        logger.warning("Login notification email failed to send for user %s", user.username, exc_info=True)
