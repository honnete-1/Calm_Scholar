from django.conf import settings
from django.db import models

class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    display_name = models.CharField(max_length=60, default='Scholar')
    daily_minutes = models.PositiveIntegerField(default=120)
    start_hour = models.PositiveIntegerField(default=16)
    energy = models.CharField(max_length=12, default='balanced')
    remember_chat = models.BooleanField(default=False)
    share_workload = models.BooleanField(default=False)
    reminders = models.BooleanField(default=True)
    is_demo = models.BooleanField(default=False)

class Assignment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=160)
    course = models.CharField(max_length=80, default='My course')
    description = models.TextField(blank=True)
    due = models.DateField()
    minutes = models.PositiveIntegerField(default=90)
    priority = models.CharField(max_length=12, default='normal')
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class Subtask(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='steps')
    title = models.CharField(max_length=180)
    minutes = models.PositiveIntegerField(default=25)
    completed = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

class StudySession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)
    subtask = models.ForeignKey(Subtask, on_delete=models.CASCADE, null=True)
    date = models.DateField()
    start_minute = models.PositiveIntegerField()
    minutes = models.PositiveIntegerField()
    title = models.CharField(max_length=180)
    completed = models.BooleanField(default=False)

class CheckIn(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    mood = models.CharField(max_length=20)
    energy = models.CharField(max_length=12)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class ChatMessage(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=12)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class FocusLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    assignment = models.ForeignKey(Assignment, on_delete=models.SET_NULL, null=True)
    minutes = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
