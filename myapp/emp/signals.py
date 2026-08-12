from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from .tasks import send_login_notification_email


@receiver(user_logged_in)
def send_login_notification(sender, request, user, **kwargs):
    send_login_notification_email.delay(user.pk)
