from django.urls import path
from . import views

urlpatterns = [
    path("teacher/", views.teacher_dashboard, name="teacher_dashboard"),
    path("mark/", views.mark_attendance, name="mark_attendance"),
    path("student/", views.student_dashboard, name="student_dashboard"),
]