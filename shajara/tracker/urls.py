# tracker/urls.py
from django.urls import path
from . import views

app_name = 'tracker'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('eisenhower/', views.eisenhower_matrix, name='eisenhower_matrix'),
    path('activities/', views.activity_log, name='activity_log'),
    path('activities/add/', views.add_activity, name='add_activity'),
    path('activities/<int:pk>/edit/', views.edit_activity, name='edit_activity'),
    path('activities/<int:pk>/delete/', views.delete_activity, name='delete_activity'),
    path('tasks/', views.task_list, name='task_list'),
    path('tasks/add/', views.add_task, name='add_task'),
    path('tasks/<int:pk>/edit/', views.edit_task, name='edit_task'),
    path('tasks/<int:pk>/delete/', views.delete_task, name='delete_task'),
    path('daily-plan/', views.daily_plan, name='daily_plan'),
    path('daily-plan/<str:date>/', views.daily_plan_detail, name='daily_plan_detail'),
    path('learning-journal/', views.learning_journal, name='learning_journal'),
    path('learning-journal/add/', views.add_learning_entry, name='add_learning_entry'),
    path('learning-journal/<int:pk>/edit/', views.edit_learning_entry, name='edit_learning_entry'),
    path('learning-journal/<int:pk>/delete/', views.delete_learning_entry, name='delete_learning_entry'),
    path('reports/', views.reports, name='reports'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register, name='register'),
    path('tasks/delete/<int:pk>/', views.delete_task, name='delete_task'),
    path('task/<int:pk>/toggle-status/', views.toggle_task_status, name='toggle_task_status'),

    path('productivity/', views.productivity_dashboard, name='productivity_dashboard'),
    path('productivity/edit/<int:score_id>/', views.edit_productivity_score, name='edit_productivity_score'),
    path('productivity/delete/<int:score_id>/', views.delete_productivity_score, name='delete_productivity_score'),
]