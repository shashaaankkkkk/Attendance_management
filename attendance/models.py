# Create your models here.
from django.db import models
from users.models import StudentProfile, TeacherProfile

class AttendanceRecord(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    date = models.DateField()
    present = models.BooleanField(default=False)
