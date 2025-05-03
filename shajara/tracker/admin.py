# tracker/admin.py
from django.contrib import admin
from .models import Task, Activity, DailyPlan, ProductivityScore, LearningEntry

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'quadrant', 'deadline', 'status', 'created_at')
    list_filter = ('user', 'quadrant', 'status')
    search_fields = ('title', 'description')
    date_hierarchy = 'created_at'

@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'category', 'date', 'start_time', 'end_time', 'duration_minutes')
    list_filter = ('user', 'category', 'date')
    search_fields = ('name', 'description')
    date_hierarchy = 'date'

@admin.register(DailyPlan)
class DailyPlanAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'created_at')
    list_filter = ('user', 'date')
    date_hierarchy = 'date'
    filter_horizontal = ('tasks',)

@admin.register(ProductivityScore)
class ProductivityScoreAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'score', 'planned_tasks', 'completed_tasks')
    list_filter = ('user', 'date')
    date_hierarchy = 'date'

@admin.register(LearningEntry)
class LearningEntryAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'tags', 'created_at')
    list_filter = ('user', 'date')
    search_fields = ('content', 'tags')
    date_hierarchy = 'date'
