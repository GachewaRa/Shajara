# tracker/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Task(models.Model):
    """Model for tasks in the Eisenhower Matrix"""
    QUADRANT_CHOICES = [
        ('IU', 'Important & Urgent'),
        ('IN', 'Important & Not Urgent'),
        ('NI', 'Not Important & Urgent'),
        ('NN', 'Not Important & Not Urgent'),
    ]
    
    STATUS_CHOICES = [
        ('P', 'Pending'),
        ('IP', 'In Progress'),
        ('C', 'Completed'),
        ('D', 'Deleted'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    quadrant = models.CharField(max_length=2, choices=QUADRANT_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    deadline = models.DateTimeField(blank=True, null=True)
    estimated_time = models.IntegerField(help_text="Estimated time in minutes", blank=True, null=True)
    actual_time = models.IntegerField(help_text="Actual time spent in minutes", blank=True, null=True)
    status = models.CharField(max_length=2, choices=STATUS_CHOICES, default='P')

    def __str__(self):
        return self.title


class Activity(models.Model):
    """Model for tracking time spent on activities"""
    CATEGORY_CHOICES = [
        ('WORK', 'Work'),
        ('PERSONAL', 'Personal'),
        ('LEARNING', 'Learning'),
        ('HEALTH', 'Health & Fitness'),
        ('LEISURE', 'Leisure'),
        ('OTHER', 'Other'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    date = models.DateField(default=timezone.now)
    start_time = models.TimeField()
    end_time = models.TimeField()
    duration_minutes = models.IntegerField(help_text="Duration in minutes", blank=True, null=True)
    task = models.ForeignKey(Task, on_delete=models.SET_NULL, blank=True, null=True, related_name='activities')
    
    def save(self, *args, **kwargs):
        """Calculate duration in minutes before saving"""
        if self.start_time and self.end_time:
            # Convert times to datetime for easier calculation
            start_dt = timezone.datetime.combine(timezone.now().date(), self.start_time)
            end_dt = timezone.datetime.combine(timezone.now().date(), self.end_time)
            
            # Handle activities that span midnight
            if end_dt < start_dt:
                end_dt += timezone.timedelta(days=1)
            
            # Calculate duration in minutes
            duration = (end_dt - start_dt).total_seconds() / 60
            self.duration_minutes = int(duration)
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.date})"


class DailyPlan(models.Model):
    """Model for daily planning"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='daily_plans')
    date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    tasks = models.ManyToManyField(Task, related_name='daily_plans')
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        unique_together = ['user', 'date']
    
    def __str__(self):
        return f"Plan for {self.date}"


class ProductivityScore(models.Model):
    """Model for tracking daily productivity scores"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='productivity_scores')
    date = models.DateField(default=timezone.now)
    score = models.IntegerField(help_text="Productivity score (0-100)")
    planned_tasks = models.IntegerField(default=0)
    completed_tasks = models.IntegerField(default=0)
    reflection = models.TextField(blank=True, null=True, help_text="Daily reflection on productivity")
    
    class Meta:
        unique_together = ['user', 'date']
    
    def __str__(self):
        return f"Score for {self.date}: {self.score}"


class LearningEntry(models.Model):
    """Model for 'What I Learned Today' journal entries"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='learning_entries')
    date = models.DateField(default=timezone.now)
    content = models.TextField()
    tags = models.CharField(max_length=200, blank=True, null=True, help_text="Comma-separated tags")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Learning entry for {self.date}"
