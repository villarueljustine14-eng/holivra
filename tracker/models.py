from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    age = models.IntegerField()
    height = models.FloatField(help_text="Height in cm")
    weight = models.FloatField(help_text="Weight in kg")
    sex = models.CharField(max_length=6, choices=(('male','Male'),('female','Female')), default='male')
    activity_level = models.FloatField(help_text='Activity multiplier', default=1.55)
    # user goal: lose, maintain, gain
    goal = models.CharField(max_length=10, choices=(('lose','Lose'),('maintain','Maintain'),('gain','Gain')), default='maintain')
    # goal rate as fraction (e.g., -0.15 means 15% calorie reduction for weight loss, 0.1 means +10% for gain)
    goal_rate = models.FloatField(default=0.0, help_text='Fractional calorie change for goal (negative for loss)')

    def __str__(self):
        return self.user.username

class FoodEntry(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    food_name = models.CharField(max_length=200)
    calories = models.FloatField()
    protein = models.FloatField()
    carbs = models.FloatField()
    fats = models.FloatField()
    date_added = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.food_name} - {self.date_added}"
