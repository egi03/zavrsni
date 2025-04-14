from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import UserProfile

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
            raise forms.ValidationError("Email already in use")
        return email
    
    def clean_username(self):
        """Check if username is already in use"""
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Username already in use")
        
        if len(username) < 3:
            raise forms.ValidationError("Username must be at least 3 characters long")
        
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
