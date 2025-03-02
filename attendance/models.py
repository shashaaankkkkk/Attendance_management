from django.contrib.auth.models import AbstractUser 

from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = (
        ('teacher', 'Teacher'),
        ('student', 'Student'),
        ('admin','Admin'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    must_change_password = models.BooleanField(default=False)


class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile')
    bio = models.TextField(blank=True)

    def __str__(self):
        return self.user.username

class Admin(models.Model):
    user=models.OneToOneField(User,on_delete=models.CASCADE, related_name='admin_profile')
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


class Class(models.Model):
    name = models.CharField(max_length=100)
    teachers = models.ManyToManyField(Teacher, related_name='classes')
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name='classes')
    course_code = models.CharField(max_length=20, unique=True,null=True, blank=True)

    @property
    def students(self):
        """Returns students belonging to this class's program"""
        return Student.objects.filter(program=self.program)

    def __str__(self):
        return f"{self.name} ({self.course_code}) - {self.program.name}"


class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name='students')

    def __str__(self):
        return self.user.username
    
class Semester(models.Model):
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name='semesters')
    semester_number = models.IntegerField()  # e.g., 1, 2, 3...
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return f"{self.program.name} - Semester {self.semester_number}"

class Course(models.Model):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name='courses')

    def __str__(self):
        return f"{self.code} - {self.name}"



class Timetable(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='timetables')
    class_assigned = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='timetables')
    day_of_week = models.CharField(max_length=10, choices=[
        ('Monday', 'Monday'), ('Tuesday', 'Tuesday'), ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'), ('Friday', 'Friday'), ('Saturday', 'Saturday'),
    ])
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        return f"{self.course.name} - {self.day_of_week} ({self.start_time} - {self.end_time})"
    

    
class AcademicYear(models.Model):
    start_year = models.IntegerField()
    end_year = models.IntegerField()

    def __str__(self):
        return f"{self.start_year}-{self.end_year}"
    
class Attendance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendance_records')
    class_name = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='attendance_records')  # Kept for backward compatibility
    timetable = models.ForeignKey(Timetable, on_delete=models.SET_NULL, null=True, blank=True, related_name='attendance_records')  # New Field
    date = models.DateField()
    present = models.BooleanField(default=False)

    class Meta:
        unique_together = ('student', 'class_name', 'date')  # No change to existing constraints

    def __str__(self):
        return f"{self.student.user.username} - {self.class_name.name} - {self.date}"
