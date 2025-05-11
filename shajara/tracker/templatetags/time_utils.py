from django import template
from django.utils import timezone
from datetime import timedelta

register = template.Library()

@register.filter
def time_until_deadline(deadline):
    now = timezone.now()
    diff = deadline - now
    total_seconds = abs(int(diff.total_seconds()))

    days = total_seconds // (3600 * 24)
    remainder_seconds = total_seconds % (3600 * 24)
    hours = remainder_seconds // 3600
    minutes = (remainder_seconds % 3600) // 60

    sign = '-' if diff < timedelta(0) else ''
    return f"{sign}{days:02d} days {hours:02d} hrs {minutes:02d} min"