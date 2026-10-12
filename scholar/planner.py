from datetime import timedelta
from django.utils import timezone
from .models import Assignment, StudySession

def propose_plan(user, profile, today=None, now_minute=None):
    """Seven days, deadline-first, capped capacity; breaks consume capacity too."""
    today = today or timezone.localdate()
    if now_minute is None:
        now = timezone.localtime()
        now_minute = now.hour * 60 + now.minute
    capacity = min(profile.daily_minutes, {'gentle': 60, 'balanced': 240, 'focused': 360}[profile.energy])
    starts = {today + timedelta(days=i): max(profile.start_hour * 60, ((now_minute + 9) // 10) * 10) if i == 0 else profile.start_hour * 60 for i in range(7)}
    cursor, ends = {}, {}
    for day, start in starts.items():
        completed = list(StudySession.objects.filter(user=user, date=day, completed=True))
        used = sum(s.minutes + 5 for s in completed)
        cursor[day] = max([start] + [s.start_minute + s.minutes + 5 for s in completed])
        ends[day] = min(cursor[day] + max(0, capacity - used), 22 * 60)
    sessions, alerts = [], []
    assignments = Assignment.objects.filter(user=user, completed=False).prefetch_related('steps').order_by('due', 'id')
    assignments = sorted(assignments, key=lambda a: (a.due, a.priority != 'high', a.id))
    for a in assignments:
        steps = list(a.steps.all().order_by('order', 'id'))
        items = [(s.id, s.title, s.minutes) for s in steps if not s.completed] if steps else [(None, a.title, a.minutes)]
        missed = sum(x.minutes for x in StudySession.objects.filter(user=user, assignment=a, date__lt=today, completed=False))
        if a.due < today:
            alerts.append(f'{a.title}: deadline has passed. Consider contacting your lecturer.')
        if missed:
            alerts.append(f'{a.title}: unfinished past sessions are included in this revised plan.')
        for sid, title, total in items:
            already_done = sum(StudySession.objects.filter(user=user, assignment=a, subtask_id=sid, completed=True).values_list('minutes', flat=True))
            remaining = max(0, total - already_done)
            latest = max(today, a.due)
            for day in cursor:
                if day > latest:
                    break
                while remaining and ends[day] - cursor[day] >= 1:
                    duration = min(25, remaining, ends[day] - cursor[day])
                    if duration < 1:
                        break
                    sessions.append({'assignment_id': a.id, 'subtask_id': sid, 'title': title, 'date': str(day), 'start_minute': cursor[day], 'minutes': duration})
                    cursor[day] += duration + 5
                    remaining -= duration
            if remaining:
                alerts.append(f'{a.title} — {title}: {remaining} minutes do not fit before the deadline within this 7-day plan. Adjust availability, scope, or request more time.')
    return {'sessions': sessions[:300], 'alerts': alerts, 'capacity': capacity, 'created_date': str(today)}
