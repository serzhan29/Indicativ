from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.urls import path, include
from debug_toolbar.toolbar import debug_toolbar_urls

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include("main.urls")),
    path('user/', include("user.urls")),
    path('chaining/', include('smart_selects.urls')),

] + debug_toolbar_urls()
