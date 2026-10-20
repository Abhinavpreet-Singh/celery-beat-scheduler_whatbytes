from django.contrib import admin
from django.urls import include, path

from scheduler import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('scheduler.urls')),
    path('', views.dashboard, name='dashboard'),
]
