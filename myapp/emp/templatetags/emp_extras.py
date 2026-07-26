from django import template

register = template.Library()

STATUS_TONES = {
    'PRESENT': 'success',
    'APPROVED': 'success',
    'ABSENT': 'danger',
    'REJECTED': 'danger',
    'HALF_DAY': 'warning',
    'PENDING': 'warning',
    'ON_LEAVE': 'accent',
    'CANCELLED': 'neutral',
}


@register.filter
def status_tone(status):
    return STATUS_TONES.get(status, 'neutral')
