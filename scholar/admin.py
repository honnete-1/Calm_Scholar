from django.contrib import admin
from .models import Assignment, Subtask, StudySession, Profile

# Sensitive conversations and check-in notes are deliberately not in admin.
admin.site.register([Assignment, Subtask, StudySession, Profile])
