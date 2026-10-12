from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Delete expired sample workspaces (7 days without login).'

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=7)
        users = User.objects.filter(profile__is_demo=True, last_login__lt=cutoff)
        count = users.count()
        users.delete()
        self.stdout.write(self.style.SUCCESS(f'Deleted {count} expired demo workspaces.'))
