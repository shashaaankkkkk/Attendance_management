from django import forms
from .models import Attendance, Student, Program , Teacher , Class
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth import get_user_model

from .models import Attendance
from django.contrib.auth.forms import AuthenticationForm , PasswordChangeForm
from django.contrib.auth import get_user_model  
from .models import Student  , Program

class AttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ['student', 'present']


class LoginForm(AuthenticationForm):
    username = forms.CharField(label='Username', widget=forms.TextInput(attrs={'class': 'form-input'}))
    password = forms.CharField(label='Password', widget=forms.PasswordInput(attrs={'class': 'form-input'}))


class BulkStudentUploadForm(forms.Form):
    csv_file = forms.FileField(
        label='Select CSV file',
        help_text='CSV should have columns: roll_number,email,first_name,last_name'
    )


class FirstLoginPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove the old password field since it's the default password
        del self.fields['old_password']


User = get_user_model()


class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['program']  # Now students belong to a program, not classes

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['program'].widget.attrs.update({'class': 'w-full p-2 border rounded'})


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'w-full p-2 border rounded'})


class VerifyOTPForm(forms.Form):
    otp = forms.IntegerField(
        label="Enter OTP",
        widget=forms.NumberInput(attrs={'class': 'w-full p-2 border rounded', 'placeholder': 'Enter OTP'})
    )
class verifyotp(forms.Form):
    otp=forms.IntegerField(label="enter otp")

from django import forms

class ExportAttendanceForm(forms.Form):
    REPORT_CHOICES = [
        ('daily', 'Daily'),
        ('monthly_range', 'Monthly (Date Range)'),
        ('monthly_whole', 'Monthly (Whole Month)'),
    ]
    
    FORMAT_CHOICES = [
        ('csv', 'CSV'),
        ('tsv', 'TSV'),
        ('txt', 'Text'),
    ]

    report_type = forms.ChoiceField(
        choices=REPORT_CHOICES, 
        widget=forms.Select(attrs={'class': 'w-full mt-1 p-2 border rounded-md'})
    )

    date = forms.DateField(
        required=False, 
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'w-full mt-1 p-2 border rounded-md'})
    )

    from_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'w-full mt-1 p-2 border rounded-md'})
    )

    to_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'w-full mt-1 p-2 border rounded-md'})
    )

    month = forms.ChoiceField(
        choices=[(str(i), str(i)) for i in range(1, 13)],
        required=False,
        widget=forms.Select(attrs={'class': 'w-full mt-1 p-2 border rounded-md'})
    )

    year = forms.IntegerField(
        required=False, 
        widget=forms.NumberInput(attrs={'class': 'w-full mt-1 p-2 border rounded-md', 'min': '2000', 'max': '2100'})
    )

    format = forms.ChoiceField(
        choices=FORMAT_CHOICES,
        widget=forms.Select(attrs={'class': 'w-full mt-1 p-2 border rounded-md'})
    )

class ProgramForm(forms.ModelForm):
    class Meta:
        model = Program
        fields = ['name','start_date', 'end_date']  
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input border-gray-300 rounded-md p-2 w-full'}),
            'start_date': forms.DateInput(attrs={'class': 'form-input border-gray-300 rounded-md p-2 w-full', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-input border-gray-300 rounded-md p-2 w-full', 'type': 'date'}),

        }



class ClassForm(forms.ModelForm):
    teachers = forms.ModelMultipleChoiceField(
        queryset=Teacher.objects.select_related('user'),
        widget=forms.CheckboxSelectMultiple,  
    )
    
    class Meta:
        model = Class
        fields = ['name', 'teachers', 'program']