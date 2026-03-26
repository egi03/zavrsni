from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count
from .forms import UserRegistrationForm, EmailOrUsernameAuthenticationForm
from .models import UserProfile
from music.models import Playlist
import base64
from django.core.files.base import ContentFile
from django.http import JsonResponse


def register(request):
    if request.user.is_authenticated:
        messages.info(request, 'Već ste ulogirani.')
        return redirect('home')
        
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registracija uspjela!')
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
            messages.success(request, 'Uspješno prijavljeni!')
            
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
                messages.success(request, 'Profilna slika uspješno uklonjena.')
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
                
                messages.success(request, 'Profilna slika ažurirana!')
                return redirect('accounts:profile')
        
        elif 'profile_picture' in request.FILES:
            user_profile.profile_picture = request.FILES['profile_picture']
            user_profile.save()
            messages.success(request, 'Profilna slika ažurirana!')
            return redirect('accounts:profile')
    
    context = {
        'profile': user_profile
    }
    return render(request, 'accounts/profile.html', context)


def profile_view(request, username):
    try:
        profile_user = get_object_or_404(User, username=username)
        user_profile, created = UserProfile.objects.get_or_create(user=profile_user)
    except User.DoesNotExist:
        messages.error(request, 'Korisnik nije pronađen.')
        return redirect('accounts:profile')
    
    playlists = Playlist.objects.filter(user=profile_user, is_public=True).annotate(
        song_count=Count('songs')
    )

    total_songs = sum(p.song_count for p in playlists)
    
    is_following = False
    if request.user.is_authenticated and request.user != profile_user:
        from social.models import UserFollow
        is_following = UserFollow.objects.filter(
            follower=request.user, 
            following=profile_user
        ).exists()
    
    context = {
        'playlists': playlists,
        'profile': profile_user,
        'total_songs': total_songs,
        'is_following': is_following,
    }
    return render(request, 'accounts/profile_view.html', context)

def search_profiles(request):
    query = request.GET.get('q', '')
    
    if len(query) < 2:
        return JsonResponse({'users': []})
    
    users = UserProfile.objects.filter(user__username__icontains=query).select_related('user')

    user_data = []
    for user in users:
        user_data.append({
            'username': user.user.username,
            'profile_picture': user.profile_picture.url if user.profile_picture else None
        })

    return JsonResponse({'users': user_data})