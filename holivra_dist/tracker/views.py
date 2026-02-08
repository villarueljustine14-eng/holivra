from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from .forms import UserRegistrationForm, FoodEntryForm, UserProfileForm
from .models import UserProfile, FoodEntry
from django.contrib import messages
from django.db.models import Sum
from datetime import date, timedelta
import json

def landing(request):
    """Public landing page with hero image background.
    If the user is authenticated, show a quick summary of today's activity.
    """
    context = {}
    if request.user.is_authenticated:
        today = date.today()
        # today's entries and totals
        entries = FoodEntry.objects.filter(user=request.user, date_added=today)
        totals = entries.aggregate(
            total_calories=Sum('calories'),
            total_protein=Sum('protein'),
            total_carbs=Sum('carbs'),
            total_fats=Sum('fats')
        )
        # profile and TDEE target
        profile = None
        try:
            profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            profile = None

        tdee = None
        tdee_desc = ''
        if profile:
            try:
                w = profile.weight
                h = profile.height
                a = profile.age
                s = profile.sex
                act = profile.activity_level or 1.55
                bmr = 10 * w + 6.25 * h - 5 * a + (5 if s == 'male' else -161)
                tdee_maintain = round(bmr * act)
                tdee = tdee_maintain
                if profile.goal_rate:
                    tdee = round(tdee_maintain * (1 + profile.goal_rate))
                    tdee_desc = f"{profile.goal.title()} ({int(profile.goal_rate*100)}%)"
                else:
                    tdee_desc = 'Maintain'
            except Exception:
                tdee = None

        context.update({
            'entries': entries,
            'totals': totals,
            'profile': profile,
            'tdee_target': tdee,
            'tdee_desc': tdee_desc,
        })

    return render(request, 'tracker/landing.html', context)

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            UserProfile.objects.create(
                user=user,
                age=form.cleaned_data['age'],
                height=form.cleaned_data['height'],
                weight=form.cleaned_data['weight']
            )
            login(request, user)
            return redirect('dashboard')
    else:
        form = UserRegistrationForm()
    return render(request, 'tracker/register.html', {'form': form})

@login_required
def dashboard(request):
    today = date.today()
    if request.method == 'POST':
        form = FoodEntryForm(request.POST)
        if form.is_valid():
            food_entry = form.save(commit=False)
            food_entry.user = request.user
            food_entry.save()
            return redirect('dashboard')
    else:
        form = FoodEntryForm()

    entries = FoodEntry.objects.filter(user=request.user, date_added=today)
    totals = entries.aggregate(
        total_calories=Sum('calories'),
        total_protein=Sum('protein'),
        total_carbs=Sum('carbs'),
        total_fats=Sum('fats')
    )
    # try to fetch user profile to prefill calculators and forms
    profile = None
    try:
        profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        profile = None

    context = {
        'form': form,
        'entries': entries,
        'totals': totals,
        'profile': profile,
    }
    # weekly calories for analytics (last 7 days)
    start = today - timedelta(days=6)
    week_qs = FoodEntry.objects.filter(user=request.user, date_added__range=(start, today)).values('date_added').annotate(calories=Sum('calories')).order_by('date_added')
    # map dates to calories
    calories_map = {item['date_added']: item['calories'] for item in week_qs}
    week_labels = []
    week_calories = []
    week_protein = []
    week_carbs = []
    week_fats = []
    for i in range(7):
        d = start + timedelta(days=i)
        week_labels.append(d.strftime('%a %d'))
        week_calories.append(round(float(calories_map.get(d, 0) or 0), 1))
        # macros per day
        # compute sums for macros over the date range earlier
    macro_qs = FoodEntry.objects.filter(user=request.user, date_added__range=(start, today)).values('date_added').annotate(
        protein=Sum('protein'), carbs=Sum('carbs'), fats=Sum('fats')
    ).order_by('date_added')
    macro_map = {item['date_added']: item for item in macro_qs}
    for i in range(7):
        d = start + timedelta(days=i)
        m = macro_map.get(d, {})
        week_protein.append(round(float(m.get('protein', 0) or 0), 1))
        week_carbs.append(round(float(m.get('carbs', 0) or 0), 1))
        week_fats.append(round(float(m.get('fats', 0) or 0), 1))
    context['week_labels_json'] = json.dumps(week_labels)
    context['week_calories_json'] = json.dumps(week_calories)
    context['week_protein_json'] = json.dumps(week_protein)
    context['week_carbs_json'] = json.dumps(week_carbs)
    context['week_fats_json'] = json.dumps(week_fats)
    return render(request, 'tracker/dashboard.html', context)


@login_required
def profile_view(request):
    # account management — edit profile
    try:
        profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user, age=25, height=170, weight=70)

    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated.')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=profile)

    context = {'form': form, 'profile': profile}
    # if AJAX request, return only the fragment for tab loading
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('partial'):
        return render(request, 'tracker/partials/profile_fragment.html', context)
    return render(request, 'tracker/profile.html', context)


@login_required
def workouts_view(request):
    # suggest workouts based on profile activity level and simple heuristics
    try:
        profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        profile = None

    # Enhanced suggestions dataset with all required fields
    base_workouts = [
        {
            'name': 'Brisk Walk', 
            'type': 'Cardio', 
            'time_min': 30,
            'difficulty': 'Beginner',
            'difficulty_level': 1,
            'calories_burned': '180-220',
            'main_time': 20
        },
        {
            'name': 'Jogging', 
            'type': 'Cardio', 
            'time_min': 20,
            'difficulty': 'Intermediate',
            'difficulty_level': 2,
            'calories_burned': '200-250',
            'main_time': 15
        },
        {
            'name': 'Bodyweight Circuit', 
            'type': 'Strength', 
            'time_min': 25,
            'difficulty': 'Intermediate',
            'difficulty_level': 3,
            'calories_burned': '250-300',
            'main_time': 20
        },
        {
            'name': 'HIIT (20 min)', 
            'type': 'HIIT', 
            'time_min': 20,
            'difficulty': 'Advanced',
            'difficulty_level': 4,
            'calories_burned': '300-350',
            'main_time': 15
        },
        {
            'name': 'Yoga Flow', 
            'type': 'Mobility', 
            'time_min': 30,
            'difficulty': 'Beginner',
            'difficulty_level': 2,
            'calories_burned': '150-200',
            'main_time': 25
        },
        {
            'name': 'Full Body Strength', 
            'type': 'Strength', 
            'time_min': 45,
            'difficulty': 'Intermediate',
            'difficulty_level': 3,
            'calories_burned': '350-450',
            'main_time': 35
        },
        {
            'name': 'Cycling Session', 
            'type': 'Cardio', 
            'time_min': 40,
            'difficulty': 'Intermediate',
            'difficulty_level': 3,
            'calories_burned': '400-500',
            'main_time': 30
        },
        {
            'name': 'Core & Stability', 
            'type': 'Strength', 
            'time_min': 20,
            'difficulty': 'Beginner',
            'difficulty_level': 2,
            'calories_burned': '150-200',
            'main_time': 15
        }
    ]

    suggestions = []
    
    if profile:
        # Determine user level based on activity_level
        act = profile.activity_level or 1.55
        
        if profile.goal == 'lose':
            # Focus more on cardio/HIIT for weight loss
            suggestions = [
                base_workouts[0],  # Brisk Walk
                base_workouts[3],  # HIIT
                base_workouts[1],  # Jogging
                base_workouts[5],  # Full Body Strength
            ]
        elif profile.goal == 'gain':
            # Focus on strength for muscle gain
            suggestions = [
                base_workouts[2],  # Bodyweight Circuit
                base_workouts[5],  # Full Body Strength
                base_workouts[6],  # Cycling Session
                base_workouts[7],  # Core & Stability
            ]
        else:
            # maintain - balanced selection
            if act < 1.4:  # Sedentary/Light
                suggestions = [
                    base_workouts[0],  # Brisk Walk
                    base_workouts[4],  # Yoga Flow
                    base_workouts[7],  # Core & Stability
                ]
            elif act < 1.7:  # Moderate
                suggestions = [
                    base_workouts[1],  # Jogging
                    base_workouts[2],  # Bodyweight Circuit
                    base_workouts[6],  # Cycling Session
                    base_workouts[4],  # Yoga Flow
                ]
            else:  # Active/Very Active
                suggestions = [
                    base_workouts[3],  # HIIT
                    base_workouts[5],  # Full Body Strength
                    base_workouts[6],  # Cycling Session
                    base_workouts[1],  # Jogging
                ]
    else:
        # Default suggestions for users without profile
        suggestions = base_workouts[:4]
    
    # Ensure each suggestion has all required fields
    for workout in suggestions:
        workout.setdefault('difficulty', 'Intermediate')
        workout.setdefault('difficulty_level', 3)
        workout.setdefault('calories_burned', '250-350')
        workout.setdefault('main_time', workout.get('time_min', 20) - 10)
    
    context = {'suggestions': suggestions, 'profile': profile}
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('partial'):
        return render(request, 'tracker/partials/workouts_fragment.html', context)
    return render(request, 'tracker/workouts.html', context)