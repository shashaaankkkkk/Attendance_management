from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.user_login, name='login'),
    path('teacher/dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    path('class/<int:class_id>/mark/', views.mark_attendance, name='mark_attendance'),
    path('class/<int:class_id>/attendance/', views.show_attendance, name='show_attendance'),
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
]