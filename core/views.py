from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib import messages
from .forms import UserRegistrationForm, EmailOrUsernameAuthenticationForm
from django.contrib.auth.decorators import login_required
from .models import UserProfile
from django.contrib.auth import get_user_model
from django.shortcuts import render

songs = [
    {
        "title": "KAMIKAZE",
        "artist": "Eminem",
        "photo": "https://i.scdn.co/image/ab67616d0000b273e4073def0c03a91e3fceaf73",
        "album": "Kamikaze",
        "year": "2018",
        "genre": "Rap, Hip Hop"
    },
    {
        "title": "MY NAME IS",
        "artist": "Eminem",
        "photo": "https://i.scdn.co/image/ab67616d0000b273d12909c6ebc83cb4c6bef6f4",
        "album": "The Slim Shady LP",
        "year": "2005",
        "genre": "Rap Hip Hop"
    },
     {
        "title": "GATA",
        "artist": "Central Cee",
        "photo": "https://i.scdn.co/image/ab67616d0000b273d531f45a2948d22e5c5ff66f",
        "album": "Can't Rush Greatness",
        "year": "2025",
        "genre": "Hip Hop, Rap"
    },
    {
        "title": "GODZILLA",
        "artist": "Eminem ft. Juice WRLD",
        "photo": "https://i.scdn.co/image/ab67616d0000b2732f44aec83b20e40f3baef73c",
        "album": "Music To Be Murdered By",
        "year": "2020",
        "genre": "Hip Hop, Rap"
    },
    {
        "title": "PSYCHO",
        "artist": "Dave",
        "photo": "https://i.scdn.co/image/ab67616d0000b273c1c8d2889455db6d03d309ed",
        "album": "PSYCHODRAMA",
        "year": "2019",
        "genre": "Hip Hop, Rap"
    }
]

def homepage(request):
    return render(request, 'core/index.html')

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
    
    return render(request, 'core/register.html', {
        'form': form,
        'login_form': login_form
    })

def login_view(request):
    if request.user.is_authenticated:
        messages.info(request, 'You are already logged in.')
        return redirect('home')
        
    login_failed = False
    
    if request.method == 'POST':
        form = EmailOrUsernameAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, 'Login successful!')
            
            next_url = request.GET.get('next', 'home')
            return redirect(next_url)
        else:
            login_failed = True
            registration_form = UserRegistrationForm()
    else:
        form = EmailOrUsernameAuthenticationForm(request)
        registration_form = UserRegistrationForm()
    
    return render(request, 'core/register.html', {
        'login_form': form,
        'form': registration_form, 
        'login_failed': login_failed  
    })
    
    
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('register')

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
            return redirect('profile')
        
        
        if 'profile_picture_data' in request.POST and request.POST['profile_picture_data']:
            import base64
            from django.core.files.base import ContentFile
            
            image_data = request.POST['profile_picture_data']
            
            if ',' in image_data:
                format, imgstr = image_data.split(';base64,')
                ext = format.split('/')[-1]
                
                filename = f"profile_{request.user.username}.{ext}"
                
                data = ContentFile(base64.b64decode(imgstr), name=filename)
                
                user_profile.profile_picture = data
                user_profile.save()
                
                messages.success(request, 'Your profile picture has been updated!')
                return redirect('profile')
        
        elif 'profile_picture' in request.FILES:
            user_profile.profile_picture = request.FILES['profile_picture']
            user_profile.save()
            messages.success(request, 'Your profile picture has been updated!')
            return redirect('profile')
    
    context = {
        'profile': user_profile
    }
    return render(request, 'core/profile.html', context)