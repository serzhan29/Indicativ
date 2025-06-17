from .models import VisitLog
from django.utils.deprecation import MiddlewareMixin


class VisitLoggingMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if not request.session.get('visit_logged', False):
            ip = request.META.get('REMOTE_ADDR', '')
            path = request.path
            user = request.user if request.user.is_authenticated else None

            VisitLog.objects.create(user=user, ip=ip, path=path)
            request.session['visit_logged'] = True
