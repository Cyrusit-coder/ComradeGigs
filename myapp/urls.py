from django.urls import path
from . import views

app_name = 'myapp'  

urlpatterns = [
    # normal pages
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('events/', views.events, name='events'),
    path('faqs/', views.faqs, name='faqs'),

    # auth pages
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('join/', views.register_landing, name='register_landing'),
    path('join/student/', views.register_student, name='register_student'),
    path('join/client/', views.register_client, name='register_client'),
    path('join/donor/', views.register_donor, name='register_donor'),

    # student URLs pattern
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('student/profile/', views.profile_edit, name='profile_edit'),
    path('gigs/', views.job_list, name='job_list'),
    path('gigs/<int:pk>/', views.job_detail, name='job_detail'),
    path('learn/', views.learn_skills, name='learn_skills'),
    path('learn/graphics/', views.skill_graphics, name='skill_graphics'),
    path('learn/web/', views.skill_web, name='skill_web'),
    path('learn/va/', views.skill_va, name='skill_va'),
    path('learn/writing/', views.skill_writing, name='skill_writing'),



    # client URLs pattern
    path('client/dashboard/', views.client_dashboard, name='client_dashboard'),
    path('client/post-gig/', views.job_create, name='job_create'),
    path('client/gig/<int:pk>/edit/', views.job_edit, name='job_edit'),
    path('client/gig/<int:job_id>/review/', views.applicant_review, name='applicant_review'),

    # donor URLs patterns
    path('donor/dashboard/', views.donor_dashboard, name='donor_dashboard'),
    path('donate/', views.donate, name='donate'),
    path('donate/confirm/', views.donate_success, name='donate_success'),

    # custom admin URLs patterns
    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/verify/', views.admin_verify_gigs, name='admin_verify_gigs'),
    path('admin-panel/users/', views.admin_users, name='admin_users'),
    path('admin-panel/stats/', views.admin_stats, name='admin_stats'),
    path('admin-panel/ban/<int:user_id>/', views.admin_ban_user, name='admin_ban_user'),
    path('admin-panel/skills/', views.admin_verify_skills, name='admin_verify_skills'),
    path('admin-panel/skills/<int:submission_id>/decide/', views.admin_approve_skill, name='admin_approve_skill'),
    path('admin-panel/expired/', views.admin_manage_expired, name='admin_manage_expired'),
    path('admin-panel/delete-gig/<int:job_id>/', views.admin_delete_gig, name='admin_delete_gig'),
    path('admin-panel/applications/', views.admin_manage_applications, name='admin_manage_applications'),
    path('admin-panel/process-app/<int:app_id>/', views.admin_process_application, name='admin_process_application'),
]