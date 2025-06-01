from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.urls import path, include
from debug_toolbar.toolbar import debug_toolbar_urls
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),  # для смены языка
]

urlpatterns += i18n_patterns(  # Добавляем переведённые маршруты
    path('admin/', admin.site.urls),
    path('', include("main.urls")),
    path('user/', include("user.urls")),
    path('chaining/', include('smart_selects.urls')),
)

# Статические файлы
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Debug Toolbar
urlpatterns += debug_toolbar_urls()
