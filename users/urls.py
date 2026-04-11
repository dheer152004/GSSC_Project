from django.urls import path
from . import views

app_name = 'users'  # Add namespace

urlpatterns = [
    path('', views.login_view, name='home'),  # Home shows login page
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('welcome/', views.welcome_view, name='welcome'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('change-password/', views.change_password_view, name='change_password'),
    path('file-upload/', views.file_upload_view, name='file_upload'),
    path('delete-file/<int:file_id>/', views.delete_file_view, name='delete_file'),
    path('edit-user/<int:user_id>/', views.edit_user_view, name='edit_user'),
    path('delete-user/<int:user_id>/', views.delete_user_view, name='delete_user'),
    path('get-schools/', views.get_schools, name='get_schools'),
    path('get-departments/', views.get_departments, name='get_departments'),
    path('get-mentors/', views.get_mentors, name='get_mentors'),
    path('mentor/student-lookup/', views.mentor_student_lookup, name='mentor_student_lookup'),
]
