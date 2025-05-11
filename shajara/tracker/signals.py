# tracker/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Activity, Task
from django.db.models import Sum

@receiver(post_save, sender=Activity)
@receiver(post_delete, sender=Activity)
def update_task_actual_time(sender, instance, **kwargs):
    task = instance.task
    if task:
        total_actual_time = Activity.objects.filter(task=task).aggregate(Sum('duration_minutes'))['duration_minutes__sum'] or 0
        task.actual_time = total_actual_time
        task.save()