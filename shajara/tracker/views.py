# tracker/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count, Avg
from datetime import datetime, timedelta
from django.http import JsonResponse

from .models import Task, Activity, DailyPlan, ProductivityScore, LearningEntry
from .forms import (TaskForm, ActivityForm, DailyPlanForm, ProductivityScoreForm, 
                  LearningEntryForm, UserRegistrationForm)

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('tracker:dashboard')
    else:
        form = UserRegistrationForm()
    return render(request, 'tracker/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('tracker:dashboard')
        else:
            messages.error(request, 'Invalid username or password')
    return render(request, 'tracker/login.html')

@login_required
def logout_view(request):
    logout(request)
    return redirect('tracker:login')

@login_required
def dashboard(request):
    # Get today's date
    today = timezone.now().date()
    
    # Get tasks for today
    daily_plan = DailyPlan.objects.filter(user=request.user, date=today).first()
    if daily_plan:
        today_tasks = daily_plan.tasks.all()
    else:
        today_tasks = []
    
    # Get recent activities
    recent_activities = Activity.objects.filter(
        user=request.user
    ).order_by('-date', '-start_time')[:5]
    
    # Get productivity scores for the last 7 days
    last_week = today - timedelta(days=7)
    productivity_scores = ProductivityScore.objects.filter(
        user=request.user,
        date__gte=last_week
    ).order_by('date')
    
    # Get recent learning entries
    recent_learning = LearningEntry.objects.filter(
        user=request.user
    ).order_by('-date')[:3]
    
    # Calculate time spent today
    today_time = Activity.objects.filter(
        user=request.user,
        date=today
    ).aggregate(total_minutes=Sum('duration_minutes'))['total_minutes'] or 0
    
    # Get tasks by quadrant for quick access to Eisenhower Matrix
    tasks_by_quadrant = {
        'IU': Task.objects.filter(user=request.user, quadrant='IU', status__in=['P', 'IP']).count(),
        'IN': Task.objects.filter(user=request.user, quadrant='IN', status__in=['P', 'IP']).count(),
        'NI': Task.objects.filter(user=request.user, quadrant='NI', status__in=['P', 'IP']).count(),
        'NN': Task.objects.filter(user=request.user, quadrant='NN', status__in=['P', 'IP']).count(),
    }
    
    context = {
        'today_tasks': today_tasks,
        'recent_activities': recent_activities,
        'productivity_scores': productivity_scores,
        'recent_learning': recent_learning,
        'today_time': today_time,
        'tasks_by_quadrant': tasks_by_quadrant,
    }
    
    return render(request, 'tracker/dashboard.html', context)

@login_required
def eisenhower_matrix(request):
    # Get all active tasks (not completed or deleted)
    tasks = Task.objects.filter(
        user=request.user,
        status__in=['P', 'IP']
    ).order_by('deadline')
    
    # Group tasks by quadrant
    important_urgent = tasks.filter(quadrant='IU')
    important_not_urgent = tasks.filter(quadrant='IN')
    not_important_urgent = tasks.filter(quadrant='NI')
    not_important_not_urgent = tasks.filter(quadrant='NN')
    
    context = {
        'important_urgent': important_urgent,
        'important_not_urgent': important_not_urgent,
        'not_important_urgent': not_important_urgent,
        'not_important_not_urgent': not_important_not_urgent,
        'form': TaskForm(),
    }
    
    return render(request, 'tracker/eisenhower_matrix.html', context)

@login_required
def task_list(request):
    # Get active tasks
    active_tasks = Task.objects.filter(
        user=request.user,
        status__in=['P', 'IP']
    ).order_by('deadline')
    
    # Get completed tasks
    completed_tasks = Task.objects.filter(
        user=request.user,
        status='C'
    ).order_by('-deadline')[:10]  # Show only the 10 most recently completed
    
    context = {
        'active_tasks': active_tasks,
        'completed_tasks': completed_tasks,
    }
    
    return render(request, 'tracker/task_list.html', context)

@login_required
def add_task(request):
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.user = request.user
            task.save()
            messages.success(request, 'Task added successfully!')
            
            # Redirect based on where the task was added from
            next_url = request.POST.get('next', 'tracker:task_list')
            return redirect(next_url)
    else:
        form = TaskForm()
    
    return render(request, 'tracker/add_task.html', {'form': form})

@login_required
def edit_task(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            messages.success(request, 'Task updated successfully!')
            
            # Redirect based on where the task was edited from
            next_url = request.POST.get('next', 'tracker:task_list')
            return redirect(next_url)
    else:
        form = TaskForm(instance=task)
    
    return render(request, 'tracker/edit_task.html', {'form': form, 'task': task})

@login_required
def delete_task(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    
    if request.method == 'POST':
        task.status = 'D'  # Mark as deleted
        task.save()
        messages.success(request, 'Task deleted successfully!')
        
        # Redirect based on where the task was deleted from
        next_url = request.POST.get('next', 'tracker:task_list')
        return redirect(next_url)
    
    return render(request, 'tracker/delete_task.html', {'task': task})

@login_required
def activity_log(request):
    # Get the date filter (default to today)
    filter_date = request.GET.get('date', timezone.now().date())
    if isinstance(filter_date, str):
        try:
            filter_date = datetime.strptime(filter_date, '%Y-%m-%d').date()
        except ValueError:
            filter_date = timezone.now().date()
    
    # Get activities for the selected date
    activities = Activity.objects.filter(
        user=request.user,
        date=filter_date
    ).order_by('start_time')
    
    # Calculate total time spent
    total_minutes = activities.aggregate(total=Sum('duration_minutes'))['total'] or 0
    hours = total_minutes // 60
    minutes = total_minutes % 60
    
    # Group activities by category for visualization
    categories = Activity.objects.filter(
        user=request.user,
        date=filter_date
    ).values('category').annotate(
        total_time=Sum('duration_minutes')
    ).order_by('-total_time')
    
    context = {
        'activities': activities,
        'filter_date': filter_date,
        'total_hours': hours,
        'total_minutes': minutes,
        'categories': categories,
    }
    
    return render(request, 'tracker/activity_log.html', context)

@login_required
def add_activity(request):
    if request.method == 'POST':
        form = ActivityForm(request.POST, user=request.user)
        if form.is_valid():
            activity = form.save(commit=False)
            activity.user = request.user
            activity.save()
            messages.success(request, 'Activity added successfully!')
            return redirect('tracker:activity_log')
    else:
        # Default to current date
        form = ActivityForm(user=request.user, initial={'date': timezone.now().date()})
    
    return render(request, 'tracker/add_activity.html', {'form': form})

@login_required
def edit_activity(request, pk):
    activity = get_object_or_404(Activity, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = ActivityForm(request.POST, instance=activity, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Activity updated successfully!')
            return redirect('tracker:activity_log')
    else:
        form = ActivityForm(instance=activity, user=request.user)
    
    return render(request, 'tracker/edit_activity.html', {'form': form, 'activity': activity})

@login_required
def delete_activity(request, pk):
    activity = get_object_or_404(Activity, pk=pk, user=request.user)
    
    if request.method == 'POST':
        activity.delete()
        messages.success(request, 'Activity deleted successfully!')
        return redirect('tracker:activity_log')
    
    return render(request, 'tracker/delete_activity.html', {'activity': activity})

@login_required
def daily_plan(request):
    # Get today's date
    today = timezone.now().date()
    
    # Check if a plan exists for today
    plan = DailyPlan.objects.filter(user=request.user, date=today).first()
    
    if request.method == 'POST':
        form = DailyPlanForm(request.POST, instance=plan, user=request.user)
        if form.is_valid():
            daily_plan = form.save(commit=False)
            daily_plan.user = request.user
            daily_plan.save()
            form.save_m2m()  # Save many-to-many relationships
            messages.success(request, 'Daily plan updated successfully!')
            return redirect('tracker:daily_plan')
    else:
        form = DailyPlanForm(instance=plan, user=request.user, initial={'date': today})
    
    context = {
        'form': form,
        'today': today,
    }
    
    return render(request, 'tracker/daily_plan.html', context)

@login_required
def daily_plan_detail(request, date):
    # Parse the date
    try:
        plan_date = datetime.strptime(date, '%Y-%m-%d').date()
    except ValueError:
        messages.error(request, 'Invalid date format')
        return redirect('tracker:daily_plan')
    
    # Get the plan for the specified date
    plan = get_object_or_404(DailyPlan, user=request.user, date=plan_date)
    
    # Get activities for that day
    activities = Activity.objects.filter(
        user=request.user,
        date=plan_date
    ).order_by('start_time')
    
    # Get productivity score if exists
    productivity = ProductivityScore.objects.filter(
        user=request.user,
        date=plan_date
    ).first()
    
    context = {
        'plan': plan,
        'activities': activities,
        'productivity': productivity,
    }
    
    return render(request, 'tracker/daily_plan_detail.html', context)

@login_required
def productivity_score(request):
    # Get today's date
    today = timezone.now().date()
    
    # Check if a score exists for today
    score = ProductivityScore.objects.filter(user=request.user, date=today).first()
    
    # Get the daily plan for today (if it exists)
    plan = DailyPlan.objects.filter(user=request.user, date=today).first()
    
    # Calculate completion rate if plan exists
    completion_rate = 0
    completed_tasks = 0
    planned_tasks = 0
    
    if plan:
        planned_tasks = plan.tasks.count()
        completed_tasks = plan.tasks.filter(status='C').count()
        if planned_tasks > 0:
            completion_rate = (completed_tasks / planned_tasks) * 100
    
    if request.method == 'POST':
        form = ProductivityScoreForm(request.POST, instance=score)
        if form.is_valid():
            productivity_score = form.save(commit=False)
            productivity_score.user = request.user
            productivity_score.planned_tasks = planned_tasks
            productivity_score.completed_tasks = completed_tasks
            productivity_score.save()
            messages.success(request, 'Productivity score submitted successfully!')
            return redirect('tracker:dashboard')
    else:
        initial_data = {'date': today}
        if score is None and completion_rate > 0:
            # Suggest a score based on completion rate
            initial_data['score'] = int(completion_rate)
        form = ProductivityScoreForm(instance=score, initial=initial_data)
    
    # Get scores for the last 7 days for trend analysis
    last_week = today - timedelta(days=7)
    previous_scores = ProductivityScore.objects.filter(
        user=request.user,
        date__gte=last_week,
        date__lt=today
    ).order_by('date')
    
    context = {
        'form': form,
        'plan': plan,
        'completion_rate': completion_rate,
        'completed_tasks': completed_tasks,
        'planned_tasks': planned_tasks,
        'previous_scores': previous_scores,
    }
    
    return render(request, 'tracker/productivity_score.html', context)

@login_required
def learning_journal(request):
    # Get entries, ordered by most recent first
    entries = LearningEntry.objects.filter(user=request.user).order_by('-date')
    
    # Filter by tag if provided
    tag_filter = request.GET.get('tag')
    if tag_filter:
        entries = entries.filter(tags__icontains=tag_filter)
    
    # Get all unique tags for the filter dropdown
    all_tags = set()
    for entry in LearningEntry.objects.filter(user=request.user):
        if entry.tags:
            entry_tags = [tag.strip() for tag in entry.tags.split(',')]
            all_tags.update(entry_tags)
    
    context = {
        'entries': entries,
        'all_tags': sorted(all_tags),
        'selected_tag': tag_filter,
    }
    
    return render(request, 'tracker/learning_journal.html', context)

@login_required
def add_learning_entry(request):
    if request.method == 'POST':
        form = LearningEntryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.user = request.user
            entry.save()
            messages.success(request, 'Learning entry added successfully!')
            return redirect('tracker:learning_journal')
    else:
        form = LearningEntryForm(initial={'date': timezone.now().date()})
    
    return render(request, 'tracker/add_learning_entry.html', {'form': form})

@login_required
def edit_learning_entry(request, pk):
    entry = get_object_or_404(LearningEntry, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = LearningEntryForm(request.POST, instance=entry)
        if form.is_valid():
            form.save()
            messages.success(request, 'Learning entry updated successfully!')
            return redirect('tracker:learning_journal')
    else:
        form = LearningEntryForm(instance=entry)
    
    return render(request, 'tracker/edit_learning_entry.html', {'form': form, 'entry': entry})

@login_required
def delete_learning_entry(request, pk):
    entry = get_object_or_404(LearningEntry, pk=pk, user=request.user)
    
    if request.method == 'POST':
        entry.delete()
        messages.success(request, 'Learning entry deleted successfully!')
        return redirect('tracker:learning_journal')
    
    return render(request, 'tracker/delete_learning_entry.html', {'entry': entry})

@login_required
def reports(request):
    # Default to showing the last 30 days
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    # Allow date range filtering
    if request.GET.get('start_date') and request.GET.get('end_date'):
        try:
            start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d').date()
            end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, 'Invalid date format')
    
    # Get productivity scores in the date range
    productivity_data = ProductivityScore.objects.filter(
        user=request.user,
        date__gte=start_date,
        date__lte=end_date
    ).order_by('date')
    
    # Get activities in the date range
    activities = Activity.objects.filter(
        user=request.user,
        date__gte=start_date,
        date__lte=end_date
    )
    
    # Calculate time spent by category
    category_time = activities.values('category').annotate(
        total_time=Sum('duration_minutes')
    ).order_by('-total_time')
    
    # Calculate average daily time spent
    days_count = (end_date - start_date).days + 1
    total_time = activities.aggregate(total=Sum('duration_minutes'))['total'] or 0
    avg_daily_time = total_time / days_count if days_count > 0 else 0
    
    # Calculate average productivity score
    avg_score = productivity_data.aggregate(avg=Avg('score'))['avg'] or 0
    
    # Calculate task completion statistics
    completed_tasks = Task.objects.filter(
        user=request.user,
        status='C',
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    ).count()
    
    new_tasks = Task.objects.filter(
        user=request.user,
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    ).count()
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'productivity_data': productivity_data,
        'category_time': category_time,
        'avg_daily_time': avg_daily_time,
        'avg_score': avg_score,
        'completed_tasks': completed_tasks,
        'new_tasks': new_tasks,
        'days_count': days_count,
    }
    
    return render(request, 'tracker/reports.html', context)