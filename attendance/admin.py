from django.contrib import admin
from .models import User, Teacher, Class, Student, Attendance , Program

# Register models with the admin site
admin.site.register(User)
admin.site.register(Teacher)
admin.site.register(Class)
admin.site.register(Student)
admin.site.register(Attendance)
admin.site.register(Program)