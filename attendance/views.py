from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from .models import Class, Student, Attendance
from .forms import LoginForm, AttendanceForm
import csv
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.db import transaction
from django.contrib.auth.decorators import user_passes_test
from django.urls import reverse
from .models import User, Student, Class
from .forms import BulkStudentUploadForm, FirstLoginPasswordChangeForm

def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                return redirect('teacher_dashboard' if user.role == 'teacher' else 'student_dashboard')
    else:
        form = LoginForm()
    return render(request, 'attendance/login.html', {'form': form})

@login_required(login_url="login")
def teacher_dashboard(request):
    classes = request.user.teacher_profile.classes.all()
    return render(request, 'attendance/teacher_dashboard.html', {'classes': classes})

@login_required
def mark_attendance(request, class_id):
    class_obj = get_object_or_404(Class, id=class_id)
    today = date.today()
    
    if request.method == 'POST':
        students = class_obj.students.all()
        for student in students:
            present = request.POST.get(f'present_{student.id}') == 'on'
            attendance_record, _ = Attendance.objects.get_or_create(
                student=student,
                class_name=class_obj,
                date=today,
                defaults={'present': present}
            )
            if not _:  # If record exists, update it
                attendance_record.present = present
                attendance_record.save()
                
        return redirect('teacher_dashboard')
    
    # Get existing attendance records for today
    students = class_obj.students.all()
    existing_attendance = Attendance.objects.filter(
        class_name=class_obj,
        date=today
    ).select_related('student')
    
    # Create a dict of student_id: attendance_status
    attendance_status = {
        att.student_id: att.present 
        for att in existing_attendance
    }
    
    return render(request, 'attendance/mark_attendance.html', {
        'class_obj': class_obj,
        'students': students,
        'today': today,
        'attendance_status': attendance_status
    })

@login_required
def student_dashboard(request):
    student_profile = request.user.student_profile
    classes = student_profile.classes.all()
    today = date.today()
    
    processed_classes = []
    for class_obj in classes:
        attendance_records = Attendance.objects.filter(
            class_name=class_obj,
            student=student_profile,
            date__month=today.month,
            date__year=today.year
        )
        
        present_dates = {
            attendance.date.day 
            for attendance in attendance_records 
            if attendance.present
        }
        
        processed_classes.append({
            'id': class_obj.id,
            'name': class_obj.name,
            'present_dates': present_dates
        })
    
    return render(request, 'attendance/student_dashboard.html', {
        'classes': processed_classes,
        'current_month': today.strftime('%B %Y'),
        'month_dates': [
            {'day': day, 'date': today.replace(day=day)}
            for day in range(1, 32) if day <= today.day
        ]
    })

@login_required
def show_attendance(request, class_id):
    class_obj = get_object_or_404(Class, id=class_id)
    selected_date = date.today()

    if request.method == 'POST' and request.POST.get('selected_date'):
        try:
            selected_date = date.fromisoformat(request.POST['selected_date'])
        except ValueError:
            pass  # Keep using today's date if invalid date provided

    attendance_records = Attendance.objects.filter(
        class_name=class_obj,
        date=selected_date
    )

    return render(request, 'attendance/show_attendance.html', {
        'class_obj': class_obj,
        'attendance_records': attendance_records,
        'selected_date': selected_date,
    })


def password_change_required(user):
    return not user.must_change_password

@login_required
def first_login_password_change(request):
    if not request.user.must_change_password:
        return redirect('home')  # or wherever you want to redirect users who don't need to change password

    if request.method == 'POST':
        form = FirstLoginPasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            request.user.must_change_password = False
            request.user.save()
            messages.success(request, 'Your password has been changed successfully. Please log in with your new password.')
            return redirect('login')
    else:
        form = FirstLoginPasswordChangeForm(user=request.user)

    return render(request, 'attendance/first_login_password_change.html', {'form': form})

@login_required
@user_passes_test(lambda u: u.role == 'teacher')
def bulk_student_upload(request, class_id):
    try:
        class_obj = Class.objects.get(id=class_id)
    except Class.DoesNotExist:
        messages.error(request, "Class not found")
        return redirect('class_list')

    if request.method == 'POST':
        form = BulkStudentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            
            if not csv_file.name.endswith('.csv'):
                messages.error(request, 'Please upload a CSV file')
                return redirect('bulk_student_upload', class_id=class_id)

            try:
                decoded_file = csv_file.read().decode('utf-8').splitlines()
                csv_reader = csv.DictReader(decoded_file)
                
                for row in csv_reader:
                    with transaction.atomic():
                        roll_number = row['roll_number'].strip()
                        
                        # Use roll number as username
                        user, user_created = User.objects.get_or_create(
                            username=roll_number,
                            defaults={
                                'email': row['email'],
                                'first_name': row['first_name'],
                                'last_name': row['last_name'],
                                'role': 'student',
                                'must_change_password': True
                            }
                        )

                        if user_created:
                            # Set roll number as initial password
                            user.set_password(roll_number)
                            user.save()

                        # Create or get student profile
                        student, student_created = Student.objects.get_or_create(
                            user=user,
                            defaults={
                                'roll_number': roll_number
                            }
                        )

                        # Add student to class if not already added
                        if class_obj not in student.classes.all():
                            student.classes.add(class_obj)

                messages.success(request, 'Students have been successfully uploaded and added to the class')
                return redirect('class_detail', class_id=class_id)

            except Exception as e:
                messages.error(request, f'Error processing CSV file: {str(e)}')
                return redirect('bulk_student_upload', class_id=class_id)
    else:
        form = BulkStudentUploadForm()

    return render(request, 'attendance/bulk_student_upload.html', {
        'form': form,
        'class_obj': class_obj
    })
