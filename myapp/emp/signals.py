from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver


@receiver(user_logged_in)
def send_login_notification(sender, request, user, **kwargs):
    if user.email:
        subject = 'New Login Alert to Your Account - Django'
        message = f'Hi {user.username},\n\nWe noticed a new login to your account. If this was you, no further action is needed!'
        try:
            html_message = render_to_string('email.html', {'user': user, 'subject': subject, 'message': message})
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False, html_message=html_message)
        except Exception as e:
            print(f"Login email failed to send: {e}")
