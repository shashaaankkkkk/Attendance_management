from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required , user_passes_test
from .models import Class, Student, Attendance , User
from .forms import LoginForm, AttendanceForm , StudentProfileForm, UserProfileForm
import csv
from django.contrib import messages
from django.db import transaction
from django.urls import reverse
from .forms import BulkStudentUploadForm, FirstLoginPasswordChangeForm
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings




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


def teacher_classes(request):
    """View function for the teacher's ERP dashboard."""
    if not hasattr(request.user, 'teacher_profile'):
        return render(request, 'error.html', {'message': 'You are not authorized to access this page.'})

    teacher = request.user.teacher_profile
    classes = teacher.classes.all()  # Get all classes assigned to the teacher

    # Data collection for each class
    class_data = []
    for cls in classes:
        students = cls.students.all()
        total_students = students.count()
        
        # Attendance records for the latest date
        latest_attendance = Attendance.objects.filter(class_name=cls).order_by('-date')[:5]
        
        class_data.append({
            'class': cls,
            'total_students': total_students,
            'latest_attendance': latest_attendance
        })

    context = {
        'teacher': teacher,
        'class_data': class_data
    }
    return render(request, 'attendance/teacher_classes.html', context)

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
                # Check if attendance status changed from present to absent
                if attendance_record.present and not present:
                    attendance_record.present = present
                    attendance_record.save()
                    # Send absence notification
                    send_absence_notification(student, class_obj.name, today)
                else:
                    attendance_record.present = present
                    attendance_record.save()
            elif not present:  # New record and student is absent
                # Send absence notification
                send_absence_notification(student, class_obj.name, today)
                
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

    # Fetch attendance for the selected date
    attendance_records = Attendance.objects.filter(class_name=class_obj, date=selected_date)

    # Generate attendance summary for calendar
    attendance_summary = {}

    all_attendance = Attendance.objects.filter(class_name=class_obj)
    for record in all_attendance:
        record_date = record.date.strftime("%Y-%m-%d")  # Convert date to string for JSON compatibility
        if record_date not in attendance_summary:
            attendance_summary[record_date] = {"present_count": 0, "absent_count": 0}
        if record.present:
            attendance_summary[record_date]["present_count"] += 1
        else:
            attendance_summary[record_date]["absent_count"] += 1

    return render(request, 'attendance/show_attendance.html', {
        'class_obj': class_obj,
        'attendance_records': attendance_records,
        'selected_date': selected_date,
        'attendance_summary': attendance_summary,  # Send dictionary directly
    })


def password_change_required(user):
    return not user.must_change_password

@login_required
def first_login_password_change(request):
    if not request.user.must_change_password:
        return redirect('/')  # or wherever you want to redirect users who don't need to change password

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
                return redirect('mark_attendance', class_id=class_id)

            except Exception as e:
                messages.error(request, f'Error processing CSV file: {str(e)}')
                return redirect('bulk_student_upload', class_id=class_id)
    else:
        form = BulkStudentUploadForm()

    return render(request, 'attendance/bulk_student_upload.html', {
        'form': form,
        'class_obj': class_obj
    })

def send_absence_notification(student, class_name, date):
    """
    Send an email notification to a student when they are marked absent.
    """
    subject = f'Absence Notification - {class_name}'
    
    # Prepare context for email template
    context = {
        'student_name': student.user.get_full_name(),
        'class_name': class_name,
        'date': date.strftime('%B %d, %Y'),
    }
    
    # Render HTML email content from template
    html_message = render_to_string('attendance/email/absence_notification.html', context)
    plain_message = render_to_string('attendance/email/absence_notification.txt', context)
    
    # Send email
    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[student.user.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Failed to send email to {student.user.email}: {str(e)}")
        return False


def changepasstemp(request):
    form = FirstLoginPasswordChangeForm(user=request.user, data=request.POST)
<<<<<<< HEAD
    return render(request,"attendance/first_login_password_change.html",{"form":form})
=======
    return render(request,"attendance/first_login_password_change.html",{"form":form})



@login_required  
def edit_student_profile(request):  
    student = request.user.student_profile  
    user = request.user  

    if request.method == 'POST':  
        user_form = UserProfileForm(request.POST, instance=user)  
        student_form = StudentProfileForm(request.POST, instance=student)  

        if user_form.is_valid() and student_form.is_valid():  
            user_form.save()  
            student_form.save()  
            return redirect('student_profile')  

    else:  
        user_form = UserProfileForm(instance=user)  
        student_form = StudentProfileForm(instance=student)  

    return render(request, 'attendance/edit_student_profile.html', {  
        'user_form': user_form,  
        'student_form': student_form,  
        'student': student  
    })  


@login_required
def student_profile(request):
    try:
        student = request.user.student_profile  # Get student profile linked to the user
    except Student.DoesNotExist:
        return redirect('home')  # Redirect if the user is not a student

    return render(request, 'attendance/student_profile.html', {'student': student})
>>>>>>> 87d30bbc94b7fa3dd22ce5c3cc12b9eec5789c5b
