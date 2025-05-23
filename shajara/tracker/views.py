# tracker/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count, Avg
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.urls import reverse
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
    # Get timezone-aware today's date
    today = timezone.now().date()
    today_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
    today_end = timezone.make_aware(datetime.combine(today, datetime.max.time()))

    today_tasks = Task.objects.filter(
        user=request.user,
        status__in=['P', 'IP']
    ).exclude(
        deadline__isnull=True
    ).order_by('deadline')[:10] 

    # Debugging - print the tasks being fetched
    print(f"Found {today_tasks.count()} tasks for today:")
    for task in today_tasks:
        print(f"- {task.title} (Due: {task.deadline})")

    # Rest of your view remains the same...
    recent_activities = Activity.objects.filter(
        user=request.user
    ).order_by('-date', '-start_time')[:5]

    # Get productivity scores for the last 7 days
    last_week = today - timedelta(days=7)
    productivity_scores = ProductivityScore.objects.filter(
        user=request.user,
        date__gte=last_week
    ).order_by('date')

    # Calculate time spent today
    total_minutes = Activity.objects.filter(
        user=request.user,
        date=today
    ).aggregate(total_minutes=Sum('duration_minutes'))['total_minutes'] or 0

    hours = total_minutes // 60
    remaining_minutes = total_minutes % 60

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
        'today_time': total_minutes,
        'today_hours': hours,
        'today_remaining_minutes': remaining_minutes,
        'tasks_by_quadrant': tasks_by_quadrant,
        'recent_learning': LearningEntry.objects.filter(
            user=request.user
        ).order_by('-date')[:3],
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
            next_url = request.POST.get('next', reverse('tracker:task_list'))
            return redirect(next_url)
    else:
        form = TaskForm()

    context = {
        'form': form,
        'task_list_url': reverse('tracker:task_list'),  # Add this line
    }
    return render(request, 'tracker/add_task.html', context)


@login_required
def edit_task(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    next_url = request.POST.get('next')

    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            messages.success(request, 'Task updated successfully!')

            # Ensure next_url has a value before redirecting
            if next_url:
                return redirect(next_url)
            else:
                return redirect(reverse('tracker:task_list'))
    else:
        form = TaskForm(instance=task)

    context = {
        'form': form,
        'task': task,
    }
    return render(request, 'tracker/edit_task.html', context)

from django.http import JsonResponse



@login_required
def toggle_task_status(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    
    if request.method == 'POST':
        if task.status == 'C':
            task.status = 'IP'
            task.completed_at = None  # Clear completion time when reopening
        else:
            task.status = 'C'
            task.completed_at = timezone.now()  # Set completion time
        task.save()
        
        messages.success(request, f'Task marked as {task.get_status_display()}')
        return redirect(request.POST.get('next', 'tracker:task_list'))
    
    return redirect('tracker:task_list')



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

    total_minutes = activities.aggregate(total=Sum('duration_minutes'))['total'] or 0
    total_hours = total_minutes // 60
    remaining_minutes = total_minutes % 60

    for activity in activities:
        activity.hours = activity.duration_minutes // 60
        activity.remaining_minutes = activity.duration_minutes % 60

    categories = Activity.objects.filter(
        user=request.user,
        date=filter_date
    ).values('category').annotate(
        total_time=Sum('duration_minutes')
    ).order_by('-total_time')

    for category in categories:
        category['total_hours'] = category['total_time'] // 60
        category['total_remaining_minutes'] = category['total_time'] % 60

    context = {
        'activities': activities,
        'filter_date': filter_date,
        'total_hours': total_hours,
        'total_minutes': remaining_minutes,
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
            return redirect(reverse('tracker:daily_plan_detail', kwargs={'date': today.isoformat()}))
    else:
        form = DailyPlanForm(instance=plan, user=request.user, initial={'date': today})

    context = {
        'form': form,
        'today': today,
    }

    return render(request, 'tracker/daily_plan.html', context)



@login_required
def daily_plan_detail(request, date=None):
    if not date:
        selected_date = timezone.now().date()
    else:
        try:
            selected_date = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, 'Invalid date format')
            return redirect(reverse('tracker:daily_plan'))

    daily_plan, created = DailyPlan.objects.get_or_create(user=request.user, date=selected_date)
    daily_plan_form = DailyPlanForm(instance=daily_plan, user=request.user)

    if request.method == 'POST':
        daily_plan_form = DailyPlanForm(request.POST, instance=daily_plan, user=request.user)
        if daily_plan_form.is_valid():
            daily_plan = daily_plan_form.save()
            messages.success(request, 'Daily plan updated successfully!')
            return redirect(reverse('tracker:daily_plan_detail', kwargs={'date': selected_date.isoformat()}))

    activities = Activity.objects.filter(
        user=request.user,
        date=selected_date
    ).order_by('start_time')

    productivity = ProductivityScore.objects.filter(
        user=request.user,
        date=selected_date
    ).first()

    prev_date = selected_date - timedelta(days=1)
    next_date = selected_date + timedelta(days=1)
    today = timezone.now().date()

    context = {
        'daily_plan': daily_plan,
        'daily_plan_form': daily_plan_form,
        'selected_date': selected_date,
        'prev_date': prev_date,
        'next_date': next_date,
        'today': today,
        'activities': activities,
        'productivity': productivity,
    }

    return render(request, 'tracker/daily_plan_detail.html', context)


@login_required
def learning_journal(request):
    # Get entries, ordered by most recent first
    learning_entries = LearningEntry.objects.filter(user=request.user).order_by('-date')

    # Filter by tag if provided
    tag_filter = request.GET.get('tag')
    if tag_filter:
        learning_entries = learning_entries.filter(tags__icontains=tag_filter)

    # Get all unique tags for the filter dropdown
    all_tags = set()
    for entry in LearningEntry.objects.filter(user=request.user):
        if entry.tags:
            entry_tags = [tag.strip() for tag in entry.tags.split(',')]
            all_tags.update(entry_tags)

    context = {
        'learning_entries': learning_entries,
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
    category_time_list = []
    category_time = activities.values('category').annotate(
        total_time=Sum('duration_minutes')
    ).order_by('-total_time')
    for item in category_time:
        total_minutes = item['total_time'] or 0
        hours = int(total_minutes // 60)
        minutes = int(total_minutes % 60)
        category_time_list.append({'category': item['category'], 'hours': hours, 'minutes': minutes})

    # Calculate average daily time spent
    days_count = (end_date - start_date).days + 1
    total_time_minutes = activities.aggregate(total=Sum('duration_minutes'))['total'] or 0
    avg_daily_minutes = total_time_minutes / days_count if days_count > 0 else 0
    avg_daily_hours = int(avg_daily_minutes // 60)
    avg_daily_remainder_minutes = int(avg_daily_minutes % 60)

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
        'category_time': category_time_list,
        'avg_daily_hours': avg_daily_hours,
        'avg_daily_minutes': avg_daily_remainder_minutes,
        'avg_score': avg_score,
        'completed_tasks': completed_tasks,
        'new_tasks': new_tasks,
        'days_count': days_count,
    }

    return render(request, 'tracker/reports.html', context)



@login_required
def productivity_dashboard(request):
    """View for displaying productivity scores and allowing users to add new ones"""
    today = timezone.now().date()
    
    # Get the last 7 days of productivity scores
    seven_days_ago = today - timedelta(days=6)
    productivity_scores = ProductivityScore.objects.filter(
        user=request.user,
        date__gte=seven_days_ago,
        date__lte=today
    ).order_by('-date')
    
    # Check if today's score exists
    today_score = ProductivityScore.objects.filter(user=request.user, date=today).first()
    
    if request.method == 'POST':
        # If today's score exists, update it; otherwise create new
        if today_score:
            form = ProductivityScoreForm(request.POST, instance=today_score)
        else:
            form = ProductivityScoreForm(request.POST)
            
        if form.is_valid():
            score_instance = form.save(commit=False)
            score_instance.user = request.user
            
            # Calculate planned tasks (tasks with deadline today)
            planned_tasks = Task.objects.filter(
                user=request.user,
                deadline__date=today
            ).count()
            
            # Calculate completed tasks (tasks completed today)
            completed_tasks = Task.objects.filter(
                user=request.user,
                status='C',
                completed_at__date=today
            ).count()
            
            score_instance.planned_tasks = planned_tasks
            score_instance.completed_tasks = completed_tasks
            
            # If user didn't provide a score, calculate one
            if not score_instance.score:
                if planned_tasks > 0:
                    completion_rate = (completed_tasks / planned_tasks) * 100
                    # Base score on completion rate but cap at 100
                    score_instance.score = min(int(completion_rate), 100)
                else:
                    # If no planned tasks but some completed, give a score of 80
                    score_instance.score = 80 if completed_tasks > 0 else 60
            
            score_instance.save()
            return redirect('tracker:productivity_dashboard')
    else:
        # For GET request, create a form for today
        if today_score:
            form = ProductivityScoreForm(instance=today_score)
        else:
            form = ProductivityScoreForm(initial={'date': today})
    
    # Calculate stats for the past 7 days
    dates = []
    scores = []
    
    # Create a dictionary to store existing scores
    score_dict = {score.date: score for score in productivity_scores}
    
    # Generate dates for the past 7 days
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        dates.append(date.strftime('%b %d'))
        
        # If we have a score for this date, use it; otherwise use 0
        if date in score_dict:
            scores.append(score_dict[date].score)
        else:
            scores.append(0)

    total_score = sum(scores) if scores else 0

    context = {
        'form': form,
        'productivity_scores': productivity_scores,
        'dates': dates,
        'scores': scores,
        'total_score': total_score,
        'today': today
    }
    
    return render(request, 'tracker/productivity_dashboard.html', context)

@login_required
def edit_productivity_score(request, score_id):
    """View for editing an existing productivity score"""
    score = get_object_or_404(ProductivityScore, id=score_id, user=request.user)
    
    if request.method == 'POST':
        form = ProductivityScoreForm(request.POST, instance=score)
        if form.is_valid():
            score_instance = form.save(commit=False)
            
            # Keep the planned and completed tasks as they were originally calculated
            score_instance.save()
            return redirect('tracker:productivity_dashboard')
    else:
        form = ProductivityScoreForm(instance=score)
    
    context = {
        'form': form,
        'score': score
    }
    
    return render(request, 'tracker/edit_productivity_score.html', context)

@login_required
def delete_productivity_score(request, score_id):
    """View for deleting a productivity score"""
    score = get_object_or_404(ProductivityScore, id=score_id, user=request.user)
    
    if request.method == 'POST':
        score.delete()
        return redirect('tracker:productivity_dashboard')
    
    return redirect('tracker:productivity_dashboard')