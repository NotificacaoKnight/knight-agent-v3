from django.urls import path
from . import views

urlpatterns = [
    path('microsoft/login/', views.microsoft_login, name='microsoft_login'),
    path('microsoft/callback/', views.microsoft_callback, name='microsoft_callback'),
    path('microsoft/token/', views.microsoft_token_login, name='microsoft_token_login'),
    path('logout/', views.logout, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('profile/update/', views.update_profile, name='update_profile'),
    path('refresh/', views.refresh_session, name='refresh_session'),
]