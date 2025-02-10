from django.urls import path
from . import views

urlpatterns = [
    path('', views.user_login, name='login'),
    path('signout', views.user_logout, name='sign_out'),
    path('teacher/dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    path('teacher/classes/', views.teacher_classes, name='teacher_classes'),
    path('class/<int:class_id>/mark/', views.mark_attendance, name='mark_attendance'),
    path('class/<int:class_id>/attendance/', views.show_attendance, name='show_attendance'),
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('student/profile/', views.student_profile, name='student_profile'),
    path('student/edit_profile',views.edit_student_profile,name='edit_profile'),
    path('class/<int:class_id>/bulk-upload/', views.bulk_student_upload, name='bulk_student_upload'),
    path('change-password/', views.first_login_password_change, name='first_login_password_change'),
    path('fetch_attendance/<int:class_id>/', views.fetch_attendance, name='fetch_attendance'),
    path('class/<int:class_id>/', views.class_detail, name='class_detail'),
]