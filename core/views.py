from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib import messages
from .forms import UserRegistrationForm

# Create your views here.
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
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request) # Automatically log in the user after registration
            messages.success(request, 'Registration successful!')
            return redirect('home')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error[0]}")
    else:
        form = UserRegistrationForm()
        
    return render(request, 'core/register.html', {'form': form})

def login(request):
    return render(request, 'core/test.html',
                  {"songs": songs})

def profile(request):
    return render(request, 'core/profile.html')
