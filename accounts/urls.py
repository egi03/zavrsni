from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('profile/<str:username>/', views.profile_view, name='profile_view'),
    path('search-profiles/', views.search_profiles, name='search_profiles'),
]