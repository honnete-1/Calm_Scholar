"""Generate a static demo for DOM tests or a static host; no Django backend."""
import os
from pathlib import Path
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.template.loader import render_to_string
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser

request = RequestFactory().get('/')
request.user = AnonymousUser()
html = render_to_string('workspace.html', {'static_demo': True}, request=request)
html = html.replace('/static/', 'static/')
Path('preview.html').write_text(html)
print('Created preview.html. This is a scripted browser-local demo, not the Django server.')
