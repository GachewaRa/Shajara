# tracker/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Task, Activity, DailyPlan, ProductivityScore, LearningEntry

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'quadrant', 'deadline', 'estimated_time', 'status']
        widgets = {
            'deadline': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['title'].widget.attrs.update({'class': 'form-control'})
        self.fields['description'].widget.attrs.update({'class': 'form-control'})
        self.fields['quadrant'].widget.attrs.update({'class': 'form-select'})
        self.fields['deadline'].widget.attrs.update({'class': 'form-control'})
        self.fields['estimated_time'].widget.attrs.update({'class': 'form-control'})
        self.fields['status'].widget.attrs.update({'class': 'form-select'})


class CustomModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        if obj.deadline:
            # Format with date and time in 24hr format if deadline has time component
            if obj.deadline.hour != 0 or obj.deadline.minute != 0:
                deadline_str = obj.deadline.strftime('%Y-%m-%d %H:%M')
            else:
                # Just show date if time is midnight (likely just a date was set)
                deadline_str = obj.deadline.strftime('%Y-%m-%d')
        else:
            deadline_str = 'No deadline'
            
        return f"{obj.title} ({obj.get_quadrant_display()}) - Due: {deadline_str}"

class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = ['name', 'description', 'category', 'date', 'start_time', 'end_time', 'task']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Update widget attributes
        self.fields['name'].widget.attrs.update({'class': 'form-control'})
        self.fields['description'].widget.attrs.update({'class': 'form-control'})
        self.fields['category'].widget.attrs.update({'class': 'form-select'})
        self.fields['date'].widget.attrs.update({'class': 'form-control'})
        self.fields['start_time'].widget.attrs.update({'class': 'form-control'})
        self.fields['end_time'].widget.attrs.update({'class': 'form-control'})
        
        # Replace the task field with a CustomModelChoiceField
        task_queryset = self.fields['task'].queryset
        self.fields['task'] = CustomModelChoiceField(
            queryset=task_queryset,
            widget=forms.Select(attrs={'class': 'form-select'}),
            required=False  # Set to True if task is required
        )
        
        # Filter tasks by user AND non-completed status
        if user:
            self.fields['task'].queryset = Task.objects.filter(
                user=user
            ).exclude(
                status='C'  # Exclude completed tasks
            ).exclude(
                status='D'  # Optionally exclude deleted tasks if needed
            ).order_by('deadline')


class DailyPlanForm(forms.ModelForm):
    class Meta:
        model = DailyPlan
        fields = ['date', 'tasks', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
            'tasks': forms.CheckboxSelectMultiple(),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['date'].widget.attrs.update({'class': 'form-control'})
        self.fields['notes'].widget.attrs.update({'class': 'form-control'})
        
        # Filter tasks by user if provided
        if user:
            self.fields['tasks'].queryset = Task.objects.filter(user=user)


class ProductivityScoreForm(forms.ModelForm):
    class Meta:
        model = ProductivityScore
        fields = ['date', 'score', 'reflection']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'reflection': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date'].widget.attrs.update({'class': 'form-control'})
        self.fields['score'].widget.attrs.update({'class': 'form-control', 'min': 0, 'max': 100})
        self.fields['reflection'].widget.attrs.update({'class': 'form-control'})


class LearningEntryForm(forms.ModelForm):
    class Meta:
        model = LearningEntry
        fields = ['date', 'content', 'tags']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'content': forms.Textarea(attrs={'rows': 5}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date'].widget.attrs.update({'class': 'form-control'})
        self.fields['content'].widget.attrs.update({'class': 'form-control'})
        self.fields['tags'].widget.attrs.update({'class': 'form-control'})


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in self.fields:
            self.fields[field_name].widget.attrs.update({'class': 'form-control'})