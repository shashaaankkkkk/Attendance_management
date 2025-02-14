from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = (
        ('teacher', 'Teacher'),
        ('student', 'Student'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    must_change_password = models.BooleanField(default=False)


class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile')
    bio = models.TextField(blank=True)

    def __str__(self):
        return self.user.username


class Program(models.Model):
    name = models.CharField(max_length=100, unique=True)
    duration = models.CharField(max_length=50)  
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return self.name

# Class model with Program association
class Class(models.Model):
    name = models.CharField(max_length=100)
    teachers = models.ManyToManyField(Teacher, related_name='classes')
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name='classes')

    def __str__(self):
        return f"{self.name} - {self.program.name}"

# Student model linked to classes and programs indirectly
class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    roll_number = models.CharField(max_length=10, unique=True)
    classes = models.ManyToManyField(Class, related_name='students')

    def __str__(self):
        return self.user.username

# Attendance model
class Attendance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendance_records')
    class_name = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField()
    present = models.BooleanField(default=False)

    class Meta:
        unique_together = ('student', 'class_name', 'date')

    def __str__(self):
        return f"{self.student.user.username} - {self.class_name.name} - {self.date}"
