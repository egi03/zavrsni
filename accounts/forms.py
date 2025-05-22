from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import UserProfile
from django.contrib.auth import authenticate

class UserRegistrationForm(UserCreationForm):
    username = forms.CharField(required=True, max_length=50)
    email = forms.EmailField(required=True)
    bio = forms.CharField(required=False, widget=forms.Textarea)
    profile_picture = forms.ImageField(required=False)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
    
    def clean_email(self):
        """Check if email is already in use"""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Račun sa ovim email već postoji")
        return email
    
    def clean_username(self):
        """Check if username is already in use"""
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Račun sa ovim korisničkim imenom već postoji")
        
        if len(username) < 3:
            raise forms.ValidationError("Korisničko imenom mora biti najmanje 3 karaktera")
        
        return username
    
    def save(self, commit=True):
        """Save the user and create a UserProfile instance"""
        user = super().save(commit=False)
        user.email = self.cleaned_data.get('email')
        
        if commit:
            user.save()
            user_profile = UserProfile.objects.create(
                user=user,
                bio=self.cleaned_data.get('bio', ''),
                profile_picture=self.cleaned_data.get('profile_picture', None)
            )
        return user

class EmailOrUsernameAuthenticationForm(AuthenticationForm):
    """Form that allows login with either username or email"""
    username = forms.CharField(label='Email or Username', max_length=254)
    
    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        
        if username and password:
            user = authenticate(username=username, password=password)
            
            if user is None:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                try:
                    user_obj = User.objects.get(email=username)
                    user = authenticate(username=user_obj.username, password=password)
                except User.DoesNotExist:
                    pass
            
            if user is None:
                raise forms.ValidationError(
                    "Please enter a correct email/username and password. "
                    "Note that both fields may be case-sensitive."
                )
            else:
                self.user_cache = user
        
        return self.cleaned_data