from django import template

register = template.Library()

@register.filter
def progress_color(value):
    """Returns a color based on the score value"""
    if value is None:
        return 'rgba(108, 117, 125, 0.8)'  # Gray for no score
    
    if value >= 90:
        return 'rgba(40, 167, 69, 0.8)'    # Green for excellent
    elif value >= 70:
        return 'rgba(23, 162, 184, 0.8)'   # Blue for good
    elif value >= 50:
        return 'rgba(255, 193, 7, 0.8)'    # Yellow for average
    elif value >= 30:
        return 'rgba(255, 128, 0, 0.8)'    # Orange for below average
    else:
        return 'rgba(220, 53, 69, 0.8)'    # Red for poor