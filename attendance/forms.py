from django import forms
from .models import Attendance
from django.contrib.auth.forms import AuthenticationForm , PasswordChangeForm
from django.contrib.auth import get_user_model  
from .models import Student  

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
        fields = ['classes']  

    def __init__(self, *args, **kwargs):  
        super().__init__(*args, **kwargs)  
        self.fields['classes'].widget.attrs.update({'class': 'w-full p-2 border rounded'})  

class UserProfileForm(forms.ModelForm):  
    class Meta:  
        model = User  
        fields = ['first_name', 'last_name', 'email']  

    def __init__(self, *args, **kwargs):  
        super().__init__(*args, **kwargs)  
        for field in self.fields.values():  
            field.widget.attrs.update({'class': 'w-full p-2 border rounded'})  
