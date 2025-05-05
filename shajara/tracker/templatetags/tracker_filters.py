from django import template

register = template.Library()

@register.filter
def sum_list(value):
    if isinstance(value, list):
        return sum(value)
    return 0