# user/signals.py
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from .models import VisitLog

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    ip = request.META.get('REMOTE_ADDR', '')
    path = request.path
    VisitLog.objects.create(user=user, ip=ip, path=path)
