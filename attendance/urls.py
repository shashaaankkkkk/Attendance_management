from django.urls import path
from . import views

urlpatterns = [
    path('', views.user_login, name='login'),
    path('teacher/dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    path('teacher/classes/', views.teacher_classes, name='teacher_dashboard'),
    path('class/<int:class_id>/mark/', views.mark_attendance, name='mark_attendance'),
    path('class/<int:class_id>/attendance/', views.show_attendance, name='show_attendance'),
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('class/<int:class_id>/bulk-upload/', views.bulk_student_upload, name='bulk_student_upload'),
    path('change-password/', views.first_login_password_change, name='first_login_password_change'),
<<<<<<< HEAD
    path('changepass',views.ppassword),
=======
    path('mekochangepasswordkauibananedo',views.changepasstemp),
>>>>>>> 3566580fb1cee0c3f8099ca8876f68eaf16ef809
]