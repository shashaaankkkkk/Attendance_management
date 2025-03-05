from django.contrib import admin
from .models import User, Teacher, Class, Student, Attendance , Program ,Admin , Timetable  , AcademicYear , Semester

# Register models with the admin site
admin.site.register([User, Teacher, Class, Student, Attendance , Program ,Admin , Timetable ,AcademicYear,Semester])
