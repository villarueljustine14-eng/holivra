from django import forms
from django.contrib.auth.models import User
from .models import UserProfile, FoodEntry

class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    age = forms.IntegerField()
    height = forms.FloatField()
    weight = forms.FloatField()

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

class FoodEntryForm(forms.ModelForm):
    class Meta:
        model = FoodEntry
        fields = ['food_name', 'calories', 'protein', 'carbs', 'fats']


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['age', 'height', 'weight', 'sex', 'activity_level', 'goal', 'goal_rate']
        widgets = {
            'sex': forms.Select(choices=(('male','Male'),('female','Female'))),
            'activity_level': forms.Select(choices=(
                (1.2, 'Sedentary'),
                (1.375, 'Light'),
                (1.55, 'Moderate'),
                (1.725, 'Active'),
                (1.9, 'Very Active'))),
            'goal': forms.Select(choices=(('lose','Lose'),('maintain','Maintain'),('gain','Gain'))),
            'goal_rate': forms.Select(choices=(
                (-0.20, 'Lose 20%'),
                (-0.15, 'Lose 15%'),
                (-0.10, 'Lose 10%'),
                (0.0, 'Maintain'),
                (0.10, 'Gain 10%'),
            )),
        }
