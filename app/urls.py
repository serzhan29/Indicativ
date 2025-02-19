from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include("main.urls")),
    path('user/', include("user.urls")),
    path('', include("django.conf.urls.i18n")),
]
urlpatterns += i18n_patterns(
    path('pages/', include('django.contrib.flatpages.urls')),
    path('', include("main.urls")),
    path('user/', include('user.urls')),
)