from django.urls import path
from . import views

urlpatterns = [
    path('send/', views.send_message, name='send_message'),
    path('sessions/', views.get_sessions, name='get_sessions'),
    path('sessions/new/', views.new_session, name='new_session'),
    path('sessions/<int:session_id>/', views.get_session_history, name='get_session_history'),
    path('sessions/<int:session_id>/delete/', views.delete_session, name='delete_session'),
    path('sessions/<int:session_id>/title/', views.update_session_title, name='update_session_title'),
    path('feedback/', views.submit_feedback, name='submit_feedback'),
    path('stats/', views.chat_stats, name='chat_stats'),
]