from django.contrib.auth.models import AbstractUser
from django.db import models

# User model for general information (role, username, etc.)
class User(AbstractUser):
    ROLE_CHOICES = (
        ('teacher', 'Teacher'),
        ('student', 'Student'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    must_change_password = models.BooleanField(default=False)
    

# Teacher model that extends User model
class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile')
    bio = models.TextField(blank=True)  # You can add more teacher-specific fields here
    
    def __str__(self):
        return self.user.username

# Class model, representing a class with many teachers and many students
class Class(models.Model):
    name = models.CharField(max_length=100)
    teachers = models.ManyToManyField(Teacher, related_name='classes')
    
    def __str__(self):
        return self.name

# Student model, related to User model for the student-specific profile
class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    roll_number = models.CharField(max_length=10, unique=True)
    classes = models.ManyToManyField(Class, related_name='students')

    def __str__(self):
        return self.user.username

# Attendance model, to keep track of student attendance in various classes
class Attendance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendance_records')
    class_name = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField(auto_now_add=True)
    present = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.student.user.username} - {self.class_name.name} - {self.date}"
