from django.urls import path, re_path  # Added re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve  # Added serve
from . import views

app_name = 'myapp'   

urlpatterns = [
    # --- 1. Public Pages ---
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('events/', views.events, name='events'),
    path('faqs/', views.faqs, name='faqs'),
    path('terms/', views.terms_of_service, name='terms'),
    path('privacy/', views.privacy_policy, name='privacy'),

    # --- 2. Authentication ---
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('join/', views.register_landing, name='register_landing'),
    path('join/student/', views.register_student, name='register_student'),
    path('join/client/', views.register_client, name='register_client'),
    path('join/donor/', views.register_donor, name='register_donor'),

    # --- 3. Student Section ---
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('student/profile/', views.profile_edit, name='profile_edit'),
    path('gigs/', views.job_list, name='job_list'),
    path('gigs/<int:pk>/', views.job_detail, name='job_detail'),
    path('student/upload-id/', views.upload_school_id, name='upload_school_id'),
    
    # Skill Assessments
    path('learn/', views.learn_skills, name='learn_skills'),
    path('learn/graphics/', views.skill_graphics, name='skill_graphics'),
    path('learn/web/', views.skill_web, name='skill_web'),
    path('learn/va/', views.skill_va, name='skill_va'),
    path('learn/writing/', views.skill_writing, name='skill_writing'),

    # --- 4. Client Section ---
    path('client/dashboard/', views.client_dashboard, name='client_dashboard'),
    path('client/post-gig/', views.job_create, name='job_create'),
    path('client/gig/<int:pk>/edit/', views.job_edit, name='job_edit'),
    path('client/gig/<int:job_id>/review/', views.applicant_review, name='applicant_review'),
    path('client/gig/<int:pk>/delete/', views.job_delete, name='job_delete'),
    
    # PAYMENT ROUTE (M-Pesa STK Push)
    path('client/gig/<int:job_id>/pay/', views.pay_for_job, name='pay_for_job'),

    # --- 5. Donor Section ---
    path('donor/dashboard/', views.donor_dashboard, name='donor_dashboard'),
    path('donate/', views.donate, name='donate'),
    path('donate/confirm/', views.donate_success, name='donate_success'),

    # --- 6. M-PESA Callback (Public) ---
    path('mpesa/confirmation/', views.mpesa_confirmation, name='mpesa_confirmation'),

    # --- 7. Custom Admin Panel ---
    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/stats/', views.admin_stats, name='admin_stats'),
    
    # User Management
    path('admin-panel/users/', views.admin_users, name='admin_users'),
    path('admin-panel/users/ban/<int:user_id>/', views.admin_ban_user, name='admin_ban_user'),
    path('admin-panel/users/verify/<int:user_id>/', views.admin_verify_user, name='admin_verify_user'),
    
    # Gig Management
    path('admin-panel/verify/', views.admin_verify_gigs, name='admin_verify_gigs'),
    path('admin-panel/expired/', views.admin_manage_expired, name='admin_manage_expired'),
    path('admin-panel/delete-gig/<int:job_id>/', views.admin_delete_gig, name='admin_delete_gig'),
    
    # Skills & Applications
    path('admin-panel/skills/', views.admin_verify_skills, name='admin_verify_skills'),
    path('admin-panel/skills/<int:submission_id>/decide/', views.admin_approve_skill, name='admin_approve_skill'),
    path('admin-panel/applications/', views.admin_manage_applications, name='admin_manage_applications'),
    path('admin-panel/process-app/<int:app_id>/', views.admin_process_application, name='admin_process_application'),
    
    # Content Management (Events & Updates)
    path('admin-panel/event/create/', views.event_create, name='event_create'),
    path('admin-panel/event/edit/<int:pk>/', views.event_edit, name='event_edit'),
    
    # This URL handles the creation of updates for specific users (Maintenance, etc.)
    path('admin-panel/update/create/', views.create_site_update, name='create_site_update'), 
    # NEW: Reject ID Logic
    path('admin-panel/users/reject/<int:user_id>/', views.admin_reject_id, name='admin_reject_id'),
]

# --- CRITICAL: Serve Media Files (Images) manually to fix Render 404 ---
# This forces Django to serve files from MEDIA_ROOT when accessed via MEDIA_URL
# urlpatterns += [
#     re_path(r'^media/(?P<path>.*)$', serve, {
#         'document_root': settings.MEDIA_ROOT,
#     }),
# ]