from .models import VisitLog
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver


class VisitLoggingMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if not request.session.get('visit_logged', False):
            ip = request.META.get('REMOTE_ADDR', '')
            path = request.path
            user = request.user if request.user.is_authenticated else None

            VisitLog.objects.create(user=user, ip=ip, path=path)
            request.session['visit_logged'] = True  # Устанавливаем флаг



# Логирование каждого запроса
# class VisitLoggingMiddleware(MiddlewareMixin):
#     def process_request(self, request):
#         ip = request.META.get('REMOTE_ADDR', '')
#         path = request.path
#         user = request.user if request.user.is_authenticated else None
#
#         # Сохраняем в базу
#         VisitLog.objects.create(user=user, ip=ip, path=path)
