from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import AttendanceRecord
from users.models import StudentProfile

# Teacher Dashboard
@login_required
def teacher_dashboard(request):
    if request.user.role != "teacher":
        return redirect("student_dashboard")
    students = StudentProfile.objects.all()
    return render(request, "attendance/teacher_dashboard.html", {"students": students})

# Mark Attendance
@login_required
def mark_attendance(request):
    if request.user.role != "teacher":
        return redirect("student_dashboard")
    if request.method == "POST":
        student_ids = request.POST.getlist("students")
        date = request.POST.get("date")
        for student_id in student_ids:
            student = StudentProfile.objects.get(id=student_id)
            AttendanceRecord.objects.create(student=student, date=date, present=True)
        return redirect("teacher_dashboard")
    students = StudentProfile.objects.all()
    return render(request, "attendance/mark_attendance.html", {"students": students})

# Student Dashboard
@login_required
def student_dashboard(request):
    if request.user.role != "student":
        return redirect("teacher_dashboard")
    attendance = AttendanceRecord.objects.filter(student=request.user.student_profile)
    return render(request, "attendance/student_dashboard.html", {"attendance": attendance})
