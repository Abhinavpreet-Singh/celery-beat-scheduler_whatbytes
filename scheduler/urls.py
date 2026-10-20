from django.urls import path

from . import views

urlpatterns = [
    path('schedule-task/', views.schedule_task, name='schedule-task'),
    path('schedule-email/', views.schedule_email, name='schedule-email'),
    path('scheduled-tasks/', views.scheduled_tasks, name='scheduled-tasks'),
    path('cancel-task/<int:task_id>/', views.cancel_task, name='cancel-task'),
    path('task-history/', views.task_history, name='task-history'),
]
