from django import forms
from .models import Attendance
from django.contrib.auth.forms import AuthenticationForm

class AttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ['student', 'present']


class LoginForm(AuthenticationForm):
    username = forms.CharField(label='Username', widget=forms.TextInput(attrs={'class': 'form-input'}))
    password = forms.CharField(label='Password', widget=forms.PasswordInput(attrs={'class': 'form-input'}))


from django import forms
from django.contrib.auth.forms import PasswordChangeForm

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