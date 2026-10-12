from datetime import timedelta
from django.utils import timezone
from .models import Assignment, Subtask

def seed_demo(user):
    today = timezone.localdate()
    examples = [
        ('Design a student support platform', 'Software Engineering', 3, 120, 'high', ['Read the brief and map the user journey', 'Sketch the core screens', 'Write the implementation outline', 'Review the rubric and refine']),
        ('Python practice: loops and functions', 'Programming', 2, 75, 'normal', ['Review two examples', 'Solve three practice problems', 'Check your answers']),
        ('Research reflection', 'Leadership', 5, 90, 'normal', ['Choose one insight from the reading', 'Outline your reflection', 'Draft and proofread']),
    ]
    for title, course, days, minutes, priority, steps in examples:
        a = Assignment.objects.create(user=user, title=title, course=course, due=today + timedelta(days=days), minutes=minutes, priority=priority)
        for i, name in enumerate(steps):
            Subtask.objects.create(assignment=a, title=name, minutes=minutes // len(steps), order=i)
