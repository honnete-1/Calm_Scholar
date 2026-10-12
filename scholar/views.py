import json
import uuid
from datetime import date
from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST, require_GET
from . import ai
from .models import Profile, Assignment, Subtask, StudySession, CheckIn, ChatMessage, FocusLog
from .planner import propose_plan
from .seed import seed_demo

def profile_for(user):
    return Profile.objects.get_or_create(user=user, defaults={'display_name': user.first_name or user.username})[0]

def home(request):
    return render(request, 'home.html')

def register(request):
    form = UserCreationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save(commit=False)
        user.first_name = request.POST.get('display_name', 'Scholar').strip()[:60] or 'Scholar'
        user.save()
        profile_for(user)
        login(request, user)
        return redirect('workspace')
    return render(request, 'registration/register.html', {'form': form})

@require_POST
def demo(request):
    if request.user.is_authenticated:
        return redirect('workspace')
    ip_key = 'demo:' + request.META.get('REMOTE_ADDR', '')
    count = cache.get(ip_key, 0)
    if count >= 10:
        return HttpResponse('Too many demo workspaces created. Please wait or create an account.', status=429)
    cache.set(ip_key, count + 1, 3600)
    user = User.objects.create_user('demo-' + uuid.uuid4().hex, first_name='Scholar')
    p = profile_for(user)
    p.is_demo = True
    p.save()
    seed_demo(user)
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    return redirect('workspace')

@login_required
@ensure_csrf_cookie
def workspace(request):
    profile_for(request.user)
    return render(request, 'workspace.html', {'static_demo': False})

def serialize(user):
    p = profile_for(user)
    today = timezone.localdate()
    assignments = []
    for a in Assignment.objects.filter(user=user).prefetch_related('steps').order_by('due', 'id'):
        assignments.append({'id': a.id, 'title': a.title, 'course': a.course, 'description': a.description, 'due': str(a.due), 'minutes': a.minutes, 'priority': a.priority, 'completed': a.completed, 'steps': [{'id': s.id, 'title': s.title, 'minutes': s.minutes, 'completed': s.completed} for s in a.steps.all().order_by('order', 'id')]})
    checkins = [{'id': c.id, 'mood': c.mood, 'energy': c.energy, 'note': c.note, 'created_at': c.created_at.isoformat()} for c in CheckIn.objects.filter(user=user).order_by('-id')[:30]]
    return {
        'profile': {'name': p.display_name, 'daily_minutes': p.daily_minutes, 'start_hour': p.start_hour, 'energy': p.energy, 'remember_chat': p.remember_chat, 'share_workload': p.share_workload, 'reminders': p.reminders, 'is_demo': p.is_demo},
        'today': str(today), 'now_minute': timezone.localtime().hour * 60 + timezone.localtime().minute,
        'assignments': assignments, 'checkins': checkins,
        'sessions': list(StudySession.objects.filter(user=user).order_by('date', 'start_minute').values('id', 'assignment_id', 'subtask_id', 'title', 'date', 'start_minute', 'minutes', 'completed')),
        'messages': list(reversed(list(ChatMessage.objects.filter(user=user).order_by('-id')[:40].values('role', 'content')))),
        'focus': list(FocusLog.objects.filter(user=user).order_by('-id')[:100].values('minutes', 'created_at')),
        'ai_mode': 'live' if settings.OPENAI_API_KEY and not p.is_demo else 'demo',
    }

@login_required
@require_GET
def state(request):
    return JsonResponse(serialize(request.user))

def text(data, key, maximum, default=''):
    value = data.get(key, default)
    if not isinstance(value, str) or len(value) > maximum:
        raise ValueError(f'{key}: enter text up to {maximum} characters.')
    return value.strip()

def integer(data, key, low, high, default=None):
    value = data.get(key, default)
    if isinstance(value, bool):
        raise ValueError(f'{key}: enter a number between {low} and {high}.')
    try:
        value = int(value)
    except (TypeError, ValueError):
        raise ValueError(f'{key}: enter a number between {low} and {high}.')
    if not low <= value <= high:
        raise ValueError(f'{key}: enter a number between {low} and {high}.')
    return value

def choice(data, key, choices, default):
    value = data.get(key, default)
    if value not in choices:
        raise ValueError(f'Invalid {key}.')
    return value

def flag(data, key, default=False):
    value = data.get(key, default)
    if type(value) is not bool:
        raise ValueError(f'Invalid {key}.')
    return value

@login_required
@require_POST
def action(request):
    try:
        data = json.loads(request.body)
        if not isinstance(data, dict):
            raise ValueError('Expected an object.')
        operation = data.get('action')
        p = profile_for(request.user)
        if operation in ('chat', 'breakdown'):
            # Development/pilot backstop. Use a shared cache in multi-worker hosting.
            key = f'ai:{request.user.pk}:{timezone.localdate()}'
            count = cache.get(key, 0)
            if count >= 40:
                return JsonResponse({'error': 'Daily assistant limit reached. Your planner still works.'}, status=429)
            cache.set(key, count + 1, 86400)
        response = {}
        if operation == 'assignment_save':
            if Assignment.objects.filter(user=request.user).count() >= 150 and not data.get('id'):
                raise ValueError('Keep at most 150 assignments. Archive or delete old work first.')
            title = text(data, 'title', 160)
            if not title:
                raise ValueError('Give your assignment a title.')
            due = date.fromisoformat(text(data, 'due', 10))
            a = get_object_or_404(Assignment, pk=data['id'], user=request.user) if data.get('id') else Assignment(user=request.user)
            a.title, a.course, a.description, a.due = title, text(data, 'course', 80, 'My course') or 'My course', text(data, 'description', 2000), due
            a.minutes = integer(data, 'minutes', 15, 1440, 90)
            a.priority = choice(data, 'priority', ['normal', 'high'], 'normal')
            a.save()
            response['assignment_id'] = a.id
        elif operation == 'assignment_delete':
            get_object_or_404(Assignment, pk=data.get('id'), user=request.user).delete()
        elif operation == 'assignment_toggle':
            a = get_object_or_404(Assignment, pk=data.get('id'), user=request.user)
            a.completed = not a.completed
            a.save()
            a.steps.update(completed=a.completed)
            StudySession.objects.filter(assignment=a, user=request.user).update(completed=a.completed)
        elif operation == 'step_toggle':
            s = get_object_or_404(Subtask, pk=data.get('id'), assignment__user=request.user)
            s.completed = not s.completed
            s.save()
            StudySession.objects.filter(subtask=s, user=request.user).update(completed=s.completed)
            s.assignment.completed = not s.assignment.steps.filter(completed=False).exists()
            s.assignment.save()
        elif operation == 'step_save':
            a = get_object_or_404(Assignment, pk=data.get('assignment_id'), user=request.user)
            title = text(data, 'title', 180)
            if not title:
                raise ValueError('Enter a step title.')
            s = get_object_or_404(Subtask, pk=data['id'], assignment=a) if data.get('id') else Subtask(assignment=a, order=a.steps.count())
            s.title, s.minutes = title, integer(data, 'minutes', 1, 1440, 25)
            s.save()
            a.completed = not a.steps.filter(completed=False).exists()
            a.save()
        elif operation == 'breakdown':
            a = get_object_or_404(Assignment, pk=data.get('id'), user=request.user)
            if a.steps.exists():
                raise ValueError('This assignment already has steps. Edit those steps instead.')
            result = ai.breakdown(a, allow_live=not p.is_demo)
            with transaction.atomic():
                for i, s in enumerate(result['steps']):
                    Subtask.objects.create(assignment=a, order=i, title=s['title'], minutes=s['minutes'])
            response.update({'mode': result['mode']})
        elif operation == 'checkin':
            mood = choice(data, 'mood', ['overwhelmed', 'low', 'okay', 'good', 'great'], 'okay')
            energy = choice(data, 'energy', ['gentle', 'balanced', 'focused'], 'balanced')
            CheckIn.objects.create(user=request.user, mood=mood, energy=energy, note=text(data, 'note', 1000))
            p.energy = energy
            p.save()
        elif operation == 'profile':
            p.display_name = text(data, 'name', 60, p.display_name) or 'Scholar'
            p.daily_minutes = integer(data, 'daily_minutes', 15, 360, p.daily_minutes)
            p.start_hour = integer(data, 'start_hour', 6, 21, p.start_hour)
            p.energy = choice(data, 'energy', ['gentle', 'balanced', 'focused'], p.energy)
            p.remember_chat = flag(data, 'remember_chat', p.remember_chat)
            p.share_workload = flag(data, 'share_workload', p.share_workload)
            p.reminders = flag(data, 'reminders', p.reminders)
            p.save()
            if not p.remember_chat:
                ChatMessage.objects.filter(user=request.user).delete()
        elif operation == 'plan_preview':
            proposal = propose_plan(request.user, p)
            request.session['proposal'] = proposal
            response['proposal'] = proposal
        elif operation == 'plan_confirm':
            proposal = request.session.pop('proposal', None)
            if not proposal or proposal.get('created_date') != str(timezone.localdate()):
                raise ValueError('Preview a fresh plan before confirming it.')
            with transaction.atomic():
                StudySession.objects.filter(user=request.user, completed=False, date__gte=timezone.localdate()).delete()
                for s in proposal['sessions']:
                    a = get_object_or_404(Assignment, pk=s['assignment_id'], user=request.user)
                    StudySession.objects.create(user=request.user, assignment=a, subtask_id=s['subtask_id'], title=s['title'], date=s['date'], start_minute=s['start_minute'], minutes=s['minutes'])
        elif operation == 'session_toggle':
            s = get_object_or_404(StudySession, pk=data.get('id'), user=request.user)
            s.completed = not s.completed
            s.save()
            if s.subtask:
                done_minutes = sum(StudySession.objects.filter(subtask=s.subtask, completed=True).values_list('minutes', flat=True))
                s.subtask.completed = done_minutes >= s.subtask.minutes
                s.subtask.save()
                s.assignment.completed = not s.assignment.steps.filter(completed=False).exists()
                s.assignment.save()
            else:
                done_minutes = sum(StudySession.objects.filter(assignment=s.assignment, completed=True).values_list('minutes', flat=True))
                s.assignment.completed = done_minutes >= s.assignment.minutes
                s.assignment.save()
        elif operation == 'chat':
            message = text(data, 'message', 3000)
            if not message:
                raise ValueError('Write a message first.')
            workload = []
            if p.share_workload:
                workload = list(Assignment.objects.filter(user=request.user, completed=False).values('title', 'due', 'minutes')[:15])
                for a in workload:
                    a['due'] = str(a['due'])
            history = list(reversed(list(ChatMessage.objects.filter(user=request.user).order_by('-id')[:10].values('role', 'content')))) if p.remember_chat else []
            response = ai.support(message, workload, history, allow_live=not p.is_demo)
            if p.remember_chat:
                ChatMessage.objects.create(user=request.user, role='user', content=message)
                ChatMessage.objects.create(user=request.user, role='assistant', content=response['reply'])
        elif operation == 'focus_log':
            minutes = integer(data, 'minutes', 1, 120)
            a = get_object_or_404(Assignment, pk=data['assignment_id'], user=request.user) if data.get('assignment_id') else None
            FocusLog.objects.create(user=request.user, assignment=a, minutes=minutes)
        elif operation == 'clear_chat':
            ChatMessage.objects.filter(user=request.user).delete()
        elif operation == 'delete_checkins':
            CheckIn.objects.filter(user=request.user).delete()
        elif operation == 'delete_account':
            if data.get('confirmation') != 'DELETE':
                raise ValueError('Type DELETE to confirm account deletion.')
            user = request.user
            logout(request)
            user.delete()
            return JsonResponse({'deleted': True})
        else:
            raise ValueError('Unknown action.')
        if operation in ('assignment_save', 'assignment_delete', 'assignment_toggle', 'step_toggle', 'step_save', 'breakdown', 'checkin', 'profile', 'session_toggle'):
            request.session.pop('proposal', None)
        response['state'] = serialize(request.user)
        return JsonResponse(response)
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        return JsonResponse({'error': 'Check the form values and try again. Titles and dates are required; time estimates must be within the displayed limits.'}, status=400)

@login_required
@require_GET
def export_data(request):
    result = serialize(request.user)
    result['checkins'] = list(CheckIn.objects.filter(user=request.user).values('mood', 'energy', 'note', 'created_at'))
    result['messages'] = list(ChatMessage.objects.filter(user=request.user).values('role', 'content', 'created_at'))
    result['focus'] = list(FocusLog.objects.filter(user=request.user).values('minutes', 'created_at'))
    response = JsonResponse(result, json_dumps_params={'indent': 2})
    response['Content-Disposition'] = 'attachment; filename="calm-scholar-data.json"'
    return response

@require_GET
def health(request):
    return JsonResponse({'status': 'ok'})
