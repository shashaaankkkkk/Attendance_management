# Standard library imports
import random
import csv
import json
from datetime import date, datetime, timedelta
from calendar import monthrange

# Django imports
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import transaction
from django.urls import reverse
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth.forms import PasswordChangeForm
from django.http import HttpResponse, JsonResponse

# Local imports
from .models import (
    Class, Student, Attendance, User, Program, Teacher, 
    Timetable, ScheduledClass, Course, Semester
)

from .forms import (
    LoginForm, VerifyOTPForm, AttendanceForm, StudentProfileForm, 
    UserProfileForm, ProgramForm, ClassForm, BulkStudentUploadForm, 
    FirstLoginPasswordChangeForm, ExportAttendanceForm
)


def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            
            if user:
                login(request, user)
                
                if user.role == 'teacher':
                    return redirect('teacher_dashboard')
                elif user.role == 'admin':
                    return redirect('admin_dashboard')
                elif user.role == 'student':
                    return redirect('student_dashboard')
                
                return redirect('')  

    else:
        form = LoginForm()
    
    return render(request, 'attendance/login.html', {'form': form})


def user_logout(request):
    if request.method == "POST":  
        logout(request)
        return redirect('login') 
    
    return render(request, 'attendance/logout_confirmation.html')

@login_required(login_url="login")
def teacher_dashboard(request):
    if not hasattr(request.user, 'teacher_profile'):
        return render(request, 'attendance/error.html', {'message': 'You are not authorized to access this page.'})
    
    classes = request.user.teacher_profile.classes.all()
    return render(request, 'attendance/teacher_dashboard.html', {'classes': classes})

def teacher_classes(request):
    """View function for the teacher's ERP dashboard."""
    if not hasattr(request.user, 'teacher_profile'):
        return render(request, 'attendance/error.html', {'message': 'You are not authorized to access this page.'})

    teacher = request.user.teacher_profile
    classes = teacher.classes.all()  # Get all classes assigned to the teacher

    # Data collection for each class
    class_data = []
    for cls in classes:
        students = Student.objects.filter(program=cls.program)
        total_students = students.count()
        
        # Fetch scheduled classes for this class's program
        scheduled_classes = ScheduledClass.objects.filter(
            course__semester=cls.program.semesters.last()
        )
        
        # Attendance records for the latest date
        latest_attendance = Attendance.objects.filter(
            scheduled_class__in=scheduled_classes
        ).order_by('-date')[:5]
        
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

def mark_attendance(request, class_id):
    class_obj = get_object_or_404(Class, id=class_id)
    today = date.today()
    
    if request.method == 'POST':
        # Get students in the program associated with this class
        students = Student.objects.filter(program=class_obj.program)
        
        # Find the scheduled class for today
        try:
            scheduled_classes = ScheduledClass.objects.filter(
                course__semester=class_obj.program.semesters.last(),  # Get current semester
                timetable__day_of_week=today.strftime('%A')
            )
            
            if not scheduled_classes.exists():
                messages.error(request, "No scheduled classes found for today.")
                return redirect('teacher_dashboard')
            
            scheduled_class = scheduled_classes.first()
            
            for student in students:
                present = request.POST.get(f'present_{student.id}') == 'on'
                
                # Create or update attendance record
                attendance_record, created = Attendance.objects.get_or_create(
                    student=student,
                    scheduled_class=scheduled_class,
                    date=today,
                    defaults={'present': present}
                )
                
                if not created:
                    attendance_record.present = present
                    attendance_record.save()
                
                # Send absence notification if needed
                if not present:
                    send_absence_notification(student, class_obj.name, today)
            
            messages.success(request, "Attendance recorded successfully.")
            return redirect('teacher_dashboard')
        
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            return redirect('teacher_dashboard')
    
    # For GET request
    # Get students in the program associated with this class
    students = Student.objects.filter(program=class_obj.program)
    
    # Try to find existing attendance records for today
    try:
        scheduled_classes = ScheduledClass.objects.filter(
            course__semester=class_obj.program.semesters.last(),
            timetable__day_of_week=today.strftime('%A')
        )
        
        if scheduled_classes.exists():
            scheduled_class = scheduled_classes.first()
            existing_attendance = Attendance.objects.filter(
                scheduled_class=scheduled_class,
                date=today
            )
            
            # Create a dict of student_id: attendance_status
            attendance_status = {
                att.student_id: att.present 
                for att in existing_attendance
            }
        else:
            attendance_status = {}
    
    except Exception as e:
        messages.error(request, f"Error fetching attendance: {str(e)}")
        attendance_status = {}
    
    return render(request, 'attendance/mark_attendance.html', {
        'class_obj': class_obj,
        'students': students,
        'today': today,
        'attendance_status': attendance_status
    })



@login_required
def student_dashboard(request):
    student_profile = request.user.student_profile
    today = date.today()
    
    # Get the current semester
    current_semester = student_profile.program.semesters.last()
    
    # Get courses in current semester
    courses = current_semester.courses.all()
    
    processed_courses = []
    for course in courses:
        # Get all scheduled classes for this course
        scheduled_classes = ScheduledClass.objects.filter(course=course)
        
        attendance_records = Attendance.objects.filter(
            student=student_profile,
            scheduled_class__in=scheduled_classes,
            date__month=today.month,
            date__year=today.year
        )
        
        present_dates = {
            attendance.date.day 
            for attendance in attendance_records 
            if attendance.present
        }
        
        processed_courses.append({
            'id': course.id,
            'name': course.name,
            'present_dates': present_dates
        })
    
    return render(request, 'attendance/student_dashboard.html', {
        'courses': processed_courses,
        'current_month': today.strftime('%B %Y'),
        'month_dates': [
            {'day': day, 'date': today.replace(day=day)}
            for day in range(1, 32) if day <= today.day
        ]
    })

def show_attendance(request, class_id):
    class_obj = get_object_or_404(Class, id=class_id)
    selected_date = date.today()

    if request.method == 'POST' and request.POST.get('selected_date'):
        try:
            selected_date = date.fromisoformat(request.POST['selected_date'])
        except ValueError:
            pass  # Keep using today's date if invalid date provided

    # Find the scheduled class for the selected date
    try:
        scheduled_classes = ScheduledClass.objects.filter(
            course__semester=class_obj.program.semesters.last(),
            timetable__day_of_week=selected_date.strftime('%A')
        )
        
        if not scheduled_classes.exists():
            messages.error(request, "No scheduled classes found for the selected date.")
            return render(request, 'attendance/show_attendance.html', {
                'class_obj': class_obj,
                'selected_date': selected_date,
                'attendance_records': [],
                'attendance_summary': {}
            })
        
        scheduled_class = scheduled_classes.first()

        # Fetch attendance for the selected date
        attendance_records = Attendance.objects.filter(
            scheduled_class=scheduled_class, 
            date=selected_date
        )

        # Generate attendance summary for calendar
        attendance_summary = {}

        all_attendance = Attendance.objects.filter(
            scheduled_class=scheduled_class
        )
        for record in all_attendance:
            record_date = record.date.strftime("%Y-%m-%d")  # Convert date to string for JSON compatibility
            if record_date not in attendance_summary:
                attendance_summary[record_date] = {"present_count": 0, "absent_count": 0}
            if record.present:
                attendance_summary[record_date]["present_count"] += 1
            else:
                attendance_summary[record_date]["absent_count"] += 1

    except Exception as e:
        messages.error(request, f"Error fetching attendance: {str(e)}")
        attendance_records = []
        attendance_summary = {}

    return render(request, 'attendance/show_attendance.html', {
        'class_obj': class_obj,
        'attendance_records': attendance_records,
        'selected_date': selected_date,
        'attendance_summary': attendance_summary,
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
    class_obj = get_object_or_404(Class, id=class_id)
    program = class_obj.program  # Get the program for this class

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

                with transaction.atomic():
                    for row in csv_reader:
                        roll_number = row['roll_number'].strip()
                        email = row.get('email', '').strip()
                        first_name = row.get('first_name', '').strip()

                        # Create or get user
                        user, user_created = User.objects.get_or_create(
                            username=roll_number,
                            defaults={
                                'email': email,
                                'first_name': first_name,
                                'role': 'student',
                                'must_change_password': True
                            }
                        )

                        if user_created:
                            user.set_password(roll_number)  # Set roll number as initial password
                            user.save()

                        # Create or get student profile
                        student, student_created = Student.objects.get_or_create(
                            user=user,
                            program=program  # Ensure student is assigned to the correct program
                        )

                        # Add student to class if not already added
                        if class_obj not in student.program.classes.all():
                            class_obj.students.add(student)

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

@login_required
def fetch_attendance(request, class_id):
    selected_date = request.GET.get('date', None)

    if selected_date:
        try:
            selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'error': 'Invalid date format'}, status=400)

        class_obj = get_object_or_404(Class, id=class_id)
        attendance_records = Attendance.objects.filter(student__class_obj=class_obj, date=selected_date)

        data = []
        for record in attendance_records:
            data.append({
                'student_name': f"{record.student.user.first_name} {record.student.user.last_name}",
                'roll_number': record.student.roll_number,
                'present': record.present
            })

        return JsonResponse({'attendance': data})

    return JsonResponse({'error': 'Date not provided'}, status=400)

@login_required
def class_detail(request, class_id):
    class_obj = get_object_or_404(Class, id=class_id)
    
    # Fetch students in the class via program
    students = Student.objects.filter(program=class_obj.program)
    
    # Get attendance data for the last 7 days
    dates = [(datetime.now() - timedelta(days=i)).date() for i in range(7)]
    attendance_data = []
    
    # Find scheduled classes for this program
    scheduled_classes = ScheduledClass.objects.filter(
        course__semester=class_obj.program.semesters.last()
    )
    
    for attendance_date in dates:
        present_count = Attendance.objects.filter(
            scheduled_class__in=scheduled_classes,
            date=attendance_date,
            present=True
        ).count()
        
        attendance_data.append({
            'date': attendance_date.strftime('%d %b'),
            'present': present_count,
            'total': students.count()
        })
    
    context = {
        'class': class_obj,
        'students': students,
        'attendance_data': attendance_data
    }
    return render(request, 'attendance/class_detail.html', context)


@login_required
def change_password(request):
    if request.method == "POST":
        form=PasswordChangeForm(user=request.user,data=request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request,form.user)
            messages.success(request,"Password has been changed successfully..")
            if hasattr(request.user, 'role') and request.user.role == 'teacher':
                return redirect('teacher_dashboard')
            else:
                return redirect('student_dashboard')    
        else:
            messages.error(request,"Please give valid input")
    else:
        form=PasswordChangeForm(user=request.user)
    return render(request,'attendance/change_pass.html',{'form':form})    



def verify_otp(request):
    if request.method == "POST":
        form = VerifyOTPForm(request.POST)
        if form.is_valid():
            stored_otp = request.session.get("otp")  # Retrieve OTP from session
            if str(stored_otp) == str(form.cleaned_data["otp"]):
                del request.session["otp"]  # OTP is used, remove from session
                return redirect("sucess")  # Redirect to success page
            else:
                form.add_error("otp", "Invalid OTP")

    else:
        otp = random.randint(100000, 999999)
        request.session["otp"] = otp  # Store OTP in session
        request.session.set_expiry(300)  # OTP expires in 5 minutes

        message = f"Your OTP is {otp}. It expires in 5 minutes."
        send_mail(
            subject="OTP Verification",
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=["lavya203@gmail.com", "shashankshekhar8534@gmail.com"],
            fail_silently=False,
        )

        form = VerifyOTPForm()

    return render(request, "attendance/verifyotp.html", {"form": form})


def sucesssssss(request):
    return render(request,"attendance/sucess.html")
from django.shortcuts import render
from django.http import HttpResponse
from .forms import ExportAttendanceForm
from .models import Attendance
import csv

def export_as_csv(attendance_records):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="attendance.csv"'

    writer = csv.writer(response)
    writer.writerow(['Date', 'Student', 'Status'])

    for record in attendance_records:
        writer.writerow([
            record.date.strftime('%Y-%m-%d'),
            str(record.student),
            'Present' if record.present else 'Absent'
        ])

    return response

def export_attendance(request):
    if request.method == "POST":
        form = ExportAttendanceForm(request.POST)
        if form.is_valid():
            report_type = form.cleaned_data.get('report_type')
            export_format = form.cleaned_data.get('format')

            attendance_records = None  # ✅ Initialize to avoid UnboundLocalError

            if report_type == 'daily':
                date = form.cleaned_data.get('date')
                if date:
                    attendance_records = Attendance.objects.filter(date=date)

            elif report_type == 'monthly_range':
                from_date = form.cleaned_data.get('from_date')
                to_date = form.cleaned_data.get('to_date')
                if from_date and to_date:
                    attendance_records = Attendance.objects.filter(date__range=[from_date, to_date])

            elif report_type == 'monthly_whole':
                month = form.cleaned_data.get('month')
                year = form.cleaned_data.get('year')
                if month and year:
                    attendance_records = Attendance.objects.filter(date__year=year, date__month=month)

            # ✅ Check if attendance_records is None
            if attendance_records is None:
                return HttpResponse("❌ Error: No valid attendance data found. Please select a correct range.", status=400)

            # ✅ Export based on selected format
            if export_format == 'csv':
                return export_as_csv(attendance_records)
            elif export_format == 'tsv':
                pass
            elif export_format == 'txt':
                pass

    else:
        form = ExportAttendanceForm()

    return render(request, 'attendance/generate_att.html', {'form': form})



def admin_dashboard(request):
    total_students = Student.objects.count()
    total_programs = Program.objects.count()
    total_teachers = Teacher.objects.count()
    context = {
        'total_students': total_students,
        'total_programs': total_programs,
        'total_teachers': total_teachers,
    }
   
    return render(request, 'attendance/admin_dashboard.html', context)


def programs(request):
    total_programs = Program.objects.count()
    all_programs = Program.objects.all().order_by('name') if total_programs else []
    
    if request.method == 'POST':
        form = ProgramForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('program')  
    else:
        form = ProgramForm()

    context = {
        'total_programs': total_programs,
        'all_programs': all_programs,
        'form': form,
    }
    
    return render(request, 'attendance/program.html', context)


def teachers(request):
    all_teachers = Teacher.objects.all()  # Fetch all teachers
    total_teachers = all_teachers.count()
    
    context = {
        'total_teachers': total_teachers,
        'teachers': all_teachers,  # Pass all teacher records
    }
    return render(request, 'attendance/admin_teachers.html', context)
       

def attendance_policy(request):
    return render(request, 'attendance/attendance_policy.txt')       


def add_teacher_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        bio = request.POST.get("bio", "")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists!")
        else:
            user = User.objects.create_user(username=username, email=email, password=password, role="teacher")
            Teacher.objects.create(user=user, bio=bio)
            messages.success(request, "Teacher added successfully!")
            return redirect("add_teacher")  # Redirect to the same form
        
    return render(request, "attendance/add_teacher.html")


def class_list(request):
    classes = Class.objects.select_related('program').prefetch_related('teachers')
    
    context = {
        'classes': classes
    }
    return render(request, 'attendance/admin_classes.html', context)


def create_class(request):
    if request.method == "POST":
        form = ClassForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('class_list')  # Redirect to class list after creation
    else:
        form = ClassForm()
    
    context = {'form': form}
    return render(request, 'attendance/create_class.html', context)

def excel_attendance(request, class_id):
    class_obj = get_object_or_404(Class, id=class_id)

    # Get year and month from request, default to current
    year = int(request.GET.get('year', date.today().year))
    month = int(request.GET.get('month', date.today().month))
    
    # Get number of days in the month
    _, num_days = monthrange(year, month)
    dates = [date(year, month, day) for day in range(1, num_days + 1)]

    # Get all students in the class's program
    students = Student.objects.filter(program=class_obj.program).order_by('user__username')

    # Find scheduled classes for this program
    scheduled_classes = ScheduledClass.objects.filter(
        course__semester=class_obj.program.semesters.last()
    )

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            attendance_data = data.get('attendance', {})

            for student_id, dates_data in attendance_data.items():
                student = get_object_or_404(Student, id=student_id)

                for date_str, present in dates_data.items():
                    attendance_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    
                    # Find matching scheduled class for this date
                    matching_scheduled_class = scheduled_classes.filter(
                        timetable__day_of_week=attendance_date.strftime('%A')
                    ).first()

                    if matching_scheduled_class:
                        Attendance.objects.update_or_create(
                            student=student,
                            scheduled_class=matching_scheduled_class,
                            date=attendance_date,
                            defaults={'present': present}
                        )

            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    # Get existing attendance records
    attendance_records = Attendance.objects.filter(
        scheduled_class__in=scheduled_classes, 
        date__year=year, 
        date__month=month
    ).select_related('student')

    # Create attendance matrix
    attendance_matrix = {
        student.id: {
            'student_name': student.user.get_full_name(),
            'attendance': {d.strftime('%Y-%m-%d'): False for d in dates}
        }
        for student in students
    }

    # Fill in existing attendance records
    for record in attendance_records:
        attendance_matrix[record.student.id]['attendance'][record.date.strftime('%Y-%m-%d')] = record.present

    context = {
        'class_obj': class_obj,
        'dates': dates,
        'students': students,
        'attendance_matrix': attendance_matrix,
        'current_month': date(year, month, 1).strftime('%B %Y'),
        'prev_month': (date(year, month, 1) - timedelta(days=1)).strftime('%Y-%m'),
        'next_month': (date(year, month, 1) + timedelta(days=32)).strftime('%Y-%m'),
        'year': year,
        'month': month,
    }

    return render(request, 'attendance/excel_attendance.html', context)
