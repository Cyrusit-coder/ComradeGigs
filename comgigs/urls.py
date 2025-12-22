from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views # Required for Password Reset

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # --- GOOGLE LOGIN (Global) ---
    path('accounts/', include('allauth.urls')), 
    
    # --- PASSWORD RESET (Global - MUST BE HERE) ---
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='auth/password_reset.html',
             email_template_name='registration/password_reset_email.html', # <--- Professional Email Body
             subject_template_name='registration/password_reset_subject.txt' # <--- Professional Subject Line
         ), 
         name='password_reset'),
         
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(template_name='auth/password_reset_done.html'), 
         name='password_reset_done'),
         
    path('password-reset-confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(template_name='auth/password_reset_confirm.html'), 
         name='password_reset_confirm'),
         
    path('password-reset-complete/', 
         auth_views.PasswordResetCompleteView.as_view(template_name='auth/password_reset_complete.html'), 
         name='password_reset_complete'),
    # ----------------------------------------------

    # Connects to your app
    path('', include('myapp.urls')),
]