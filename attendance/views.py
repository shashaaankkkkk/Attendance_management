import datetime
from django.shortcuts import render, redirect, get_object_or_404
from .models import Class, Student, Attendance, User
from .forms import AttendanceForm
from django.contrib.auth.decorators import login_required

@login_required
def teacher_dashboard(request):
    # Get classes where the logged-in user is a teacher
    teacher_profile = request.user.teacher_profile
    classes = teacher_profile.classes.all()
    return render(request, 'attendance/teacher_dashboard.html', {'classes': classes})

@login_required
def mark_attendance(request, class_id):
    class_obj = get_object_or_404(Class, id=class_id)
    if request.method == 'POST':
        students = class_obj.students.all()
        for student in students:
            present = request.POST.get(f'present_{student.id}') == 'on'
            # Check if attendance already exists for the date; if not, create a new record
            attendance_record, created = Attendance.objects.get_or_create(
                student=student, class_name=class_obj, date=datetime.date.today()
            )
            attendance_record.present = present
            attendance_record.save()
        return redirect('teacher_dashboard')
    
    students = class_obj.students.all()
    return render(request, 'attendance/mark_attendance.html', {'class_obj': class_obj, 'students': students})

@login_required
def student_dashboard(request):
    student_profile = request.user.student_profile
    classes = student_profile.classes.all()
    attendance_stats = {
        class_obj.name: {
            'total': Attendance.objects.filter(class_name=class_obj, student=student_profile).count(),
            'present': Attendance.objects.filter(class_name=class_obj, student=student_profile, present=True).count(),
        } for class_obj in classes
    }
    return render(request, 'attendance/student_dashboard.html', {'classes': classes, 'attendance_stats': attendance_stats})


from django.contrib.auth import login, authenticate
from django.shortcuts import render, redirect
from .forms import LoginForm

def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                # Redirect based on user role
                if user.role == 'teacher':
                    return redirect('teacher_dashboard')
                else:
                    return redirect('student_dashboard')
    else:
        form = LoginForm()
    return render(request, 'attendance/login.html', {'form': form})

@login_required
def teacher_dashboard(request):
    # Display classes assigned to the teacher
    teacher_profile = request.user.teacher_profile
    classes = teacher_profile.classes.all()
    return render(request, 'attendance/teacher_dashboard.html', {'classes': classes})

@login_required
def student_dashboard(request):
    # Display student dashboard with attendance stats
    student_profile = request.user.student_profile
    classes = student_profile.classes.all()
    attendance_stats = {
        class_obj.name: {
            'total': Attendance.objects.filter(class_name=class_obj, student=student_profile).count(),
            'present': Attendance.objects.filter(class_name=class_obj, student=student_profile, present=True).count(),
        } for class_obj in classes
    }
    return render(request, 'attendance/student_dashboard.html', {'classes': classes, 'attendance_stats': attendance_stats})


@login_required
def show_attendance(request, class_id):
    class_obj = get_object_or_404(Class, id=class_id)
    # Get today's date and display the attendance for today by default
    today = datetime.date.today()

    if request.method == 'POST':
        # If the user selected a different date from the calendar
        selected_date = request.POST.get('selected_date')
        if selected_date:
            today = datetime.datetime.strptime(selected_date, '%Y-%m-%d').date()

    # Get all the attendance records for the selected date
    attendance_records = Attendance.objects.filter(class_name=class_obj, date=today)

    # Prepare the context for rendering the template
    context = {
        'class_obj': class_obj,
        'attendance_records': attendance_records,
        'selected_date': today,
    }

    return render(request, 'attendance/show_attendance.html', context)