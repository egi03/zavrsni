from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import UserRegistrationForm, EmailOrUsernameAuthenticationForm
from .models import UserProfile
from music.models import Playlist
import base64
from django.core.files.base import ContentFile
from django.http import JsonResponse


def register(request):
    if request.user.is_authenticated:
        messages.info(request, 'You are already registered and logged in.')
        return redirect('home')
        
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('home')
    else:
        form = UserRegistrationForm()
    
    login_form = EmailOrUsernameAuthenticationForm(request)
    
    return render(request, 'accounts/register.html', {
        'form': form,
        'login_form': login_form
    })

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
        
    login_failed = False
    
    if request.method == 'POST':
        form = EmailOrUsernameAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, 'Login successful!')
            
            next_url = request.GET.get('next', 'accounts:profile')
            return redirect(next_url)
        else:
            login_failed = True
            registration_form = UserRegistrationForm()
    else:
        form = EmailOrUsernameAuthenticationForm(request)
        registration_form = UserRegistrationForm()
    
    return render(request, 'accounts/register.html', {
        'login_form': form,
        'form': registration_form, 
        'login_failed': login_failed  
    })

def logout_view(request):
    logout(request)
    return redirect('accounts:register')

@login_required
def profile(request):
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        if 'remove_profile_picture' in request.POST:
            if user_profile.profile_picture:
                user_profile.profile_picture.delete()
                user_profile.profile_picture = None
                user_profile.save()
                messages.success(request, 'Profile picture removed successfully.')
            return redirect('accounts:profile')
        
        if 'profile_picture_data' in request.POST and request.POST['profile_picture_data']:
            image_data = request.POST['profile_picture_data']
            
            if ',' in image_data:
                format, imgstr = image_data.split(';base64,')
                ext = format.split('/')[-1]
                
                filename = f"profile_{request.user.username}.{ext}"
                data = ContentFile(base64.b64decode(imgstr), name=filename)
                
                user_profile.profile_picture = data
                user_profile.save()
                
                messages.success(request, 'Your profile picture has been updated!')
                return redirect('accounts:profile')
        
        elif 'profile_picture' in request.FILES:
            user_profile.profile_picture = request.FILES['profile_picture']
            user_profile.save()
            messages.success(request, 'Your profile picture has been updated!')
            return redirect('accounts:profile')
    
    context = {
        'profile': user_profile
    }
    return render(request, 'accounts/profile.html', context)


def profile_view(request, username):
    try:
        user_profile = UserProfile.objects.get(user__username=username)
    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found.')
        return redirect('accounts:profile')
    
    context = {
        'playlists': Playlist.objects.filter(user=user_profile.user, is_public=True),
        'profile': user_profile.user,
    }
    return render(request, 'accounts/profile_view.html', context)

def search_profiles(request):
    query = request.GET.get('q', '')
    
    if len(query) < 2:
        return JsonResponse({'users': []})
    
    users = UserProfile.objects.filter(user__username__icontains=query)
    
    user_data = []
    for user in users:
        user_data.append({
            'username': user.user.username,
            'profile_picture': user.profile_picture.url if user.profile_picture else None
        })

    return JsonResponse({'users': user_data})