import json  # parse incoming JSON data from M-Pesa callbacks
import traceback  # Helps print detailed error logs to the terminal for debugging
from django.shortcuts import render, redirect, get_object_or_404  
from django.contrib.auth import login, logout  # log a user in or out of the session
from django.contrib.auth.decorators import login_required  # Decorator to protect views so only logged-in users can see them
from django.contrib import messages   # Framework to send flash notifications (Success, Error, Warning alerts)
from django.db.models import Sum  # Database tool to calculate totals (like adding up total earnings)
from django.urls import reverse_lazy, reverse  # Converts a URL name (like 'home') into a real link string
from django.views.decorators.csrf import csrf_exempt  # Allows external requests (like M-Pesa) to post data without a security token
from django.http import HttpResponse, JsonResponse  # Used to send raw text or JSON data back (instead of a full HTML page)
from django.conf import settings  # Allows access to variables in your settings.py (like API keys)
from django.utils import timezone  # Django's tool for handling dates and times (used for checking expired gigs)

from .models import User, Job, Application, Donation, StudentProfile, Skill, SkillSubmission
from .forms import (
    StudentRegisterForm, ClientRegisterForm, DonorRegisterForm, 
    JobForm, StudentProfileForm, DonationForm
)

# --- normal public pages ---
def home(request):
    return render(request, 'pages/home.html')

def about(request):
    return render(request, 'pages/about.html')

def events(request):
    return render(request, 'pages/events.html')

def contact(request):
    return render(request, 'pages/contact.html')

def faqs(request):
    return render(request, 'pages/faqs.html')

# --- authenticated users views ---
def login_view(request):
    from django.contrib.auth.views import LoginView
    
    class CustomLoginView(LoginView):
        def get_success_url(self):
            user = self.request.user
            if user.role == 'student':
                return reverse('myapp:student_dashboard')
            elif user.role == 'client':
                return reverse('myapp:client_dashboard')
            elif user.role == 'donor':
                return reverse('myapp:donor_dashboard')
            elif user.role == 'admin':
                return reverse('myapp:admin_dashboard')
            return reverse('myapp:home')
            
    return CustomLoginView.as_view(template_name='auth/login.html')(request)

@login_required
def logout_view(request):
    logout(request)
    return redirect('myapp:home')

def register_landing(request):
    return render(request, 'auth/register_landing.html')

def register_student(request):
    if request.method == 'POST':
        form = StudentRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Welcome back, Comrade! Profile created.")
            return redirect('myapp:student_dashboard')
    else:
        form = StudentRegisterForm()
    return render(request, 'auth/register_student.html', {'form': form})

def register_client(request):
    if request.method == 'POST':
        form = ClientRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Client account created. Post a gig now!")
            return redirect('myapp:client_dashboard')
    else:
        form = ClientRegisterForm()
    return render(request, 'auth/register_client.html', {'form': form})

def register_donor(request):
    if request.method == 'POST':
        form = DonorRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Thank you for joining the alliance.")
            return redirect('myapp:donor_dashboard')
    else:
        form = DonorRegisterForm()
    return render(request, 'auth/register_donor.html', {'form': form})

# student views
@login_required
def student_dashboard(request):
    if request.user.role != 'student':
        return redirect('myapp:home')
    
    # 1. Get recent applications (Limit to 5)
    apps = request.user.my_applications.all().order_by('-created_at')[:5]
    
    # 2. get active jobs (assignments)

    active_jobs_list = request.user.assigned_jobs.filter(status='assigned').order_by('deadline')
    
    # 3. Calculate total earnings
    
    earnings_data = request.user.assigned_jobs.filter(status='completed').aggregate(Sum('budget'))
    total_earnings = earnings_data['budget__sum'] or 0
    
    context = {
        'my_apps': apps,
        'active_jobs_count': active_jobs_list.count(),
        'active_jobs_list': active_jobs_list, # Passing the full list for your "active projects" card
        'total_earnings': total_earnings,     # Passing this for the "total earnings" card
    }
    return render(request, 'student/dashboard.html', context)
def job_list(request):
    jobs = Job.objects.filter(status='open').order_by('-created_at')
    
    query = request.GET.get('q')
    if query:
        jobs = jobs.filter(title__icontains=query)
        
    return render(request, 'student/job_list.html', {'jobs': jobs})

def job_detail(request, pk):
    job = get_object_or_404(Job, pk=pk)
    
    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.error(request, "Please login to apply.")
            return redirect('myapp:login')
            
        if request.user.role != 'student':
            messages.error(request, "Only Student accounts can apply.")
            return redirect('myapp:job_detail', pk=pk)

        cover_letter = request.POST.get('cover_letter')

        if Application.objects.filter(job=job, student=request.user).exists():
            messages.warning(request, "You have already applied for this gig!")
        else:
            Application.objects.create(
                job=job, 
                student=request.user, 
                cover_letter=cover_letter,
                bid_amount=job.budget
            )
            messages.success(request, "Application sent successfully!")
        
        return redirect('myapp:job_detail', pk=pk)
            
    return render(request, 'student/job_detail.html', {'job': job})

@login_required
def profile_edit(request):
    try:
        profile = request.user.student_profile
    except StudentProfile.DoesNotExist:
        return redirect('myapp:home') 

    if request.method == 'POST':
        form = StudentProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            request.user.phone_number = form.cleaned_data['phone_number']
            request.user.email = form.cleaned_data['email']
            
            if 'profile_image' in request.FILES:
                request.user.profile_image = request.FILES['profile_image']
            
            request.user.save()
            form.save()
            
            messages.success(request, "Profile Updated Successfully")
            return redirect('myapp:student_dashboard')
            
    else:
        initial_data = {
            'email': request.user.email,
            'phone_number': request.user.phone_number
        }
        form = StudentProfileForm(instance=profile, initial=initial_data)
    
    return render(request, 'student/profile_edit.html', {'form': form})

def approve_student_skill(request, student_id):
    student = get_object_or_404(StudentProfile, id=student_id)
    student.is_skill_verified = True
    student.save()
    # this triggers the badge to appear on their profile(student prof)
    return redirect('admin_panel')

@login_required
def learn_skills(request):
    return render(request, 'student/learn_skills.html')

@login_required
def skill_graphics(request):
    if request.method == "POST":
        SkillSubmission.objects.create(
            student=request.user,
            skill_name="Graphic Design",
            proof_link=request.POST.get('link'),
            proof_file=request.FILES.get('file'),
            description=request.POST.get('description')
        )
        messages.success(request, "Assessment submitted! It is now Pending Review.")
        return redirect('myapp:student_dashboard')
    return render(request, "student/skill_graphics.html")

@login_required
def skill_web(request):
    if request.method == "POST":
        SkillSubmission.objects.create(
            student=request.user,
            skill_name="Web Basics",
            proof_link=request.POST.get('link'),
            proof_file=request.FILES.get('file')
        )
        messages.success(request, "Web Design assessment submitted! Admin will review it.")
        return redirect('myapp:student_dashboard')
    return render(request, "student/skill_web.html")

@login_required
def skill_va(request):
    if request.method == "POST":
        SkillSubmission.objects.create(
            student=request.user,
            skill_name="Virtual Assistant",
            proof_link=request.POST.get('link'),
            description=request.POST.get('email_draft')
        )
        messages.success(request, "Virtual Assistant assessment submitted! Admin will review it.")
        return redirect('myapp:student_dashboard')
    return render(request, "student/skill_va.html")

@login_required
def skill_writing(request):
    if request.method == "POST":
        SkillSubmission.objects.create(
            student=request.user,
            skill_name="Content Writing",
            description=request.POST.get('article_text')
        )
        messages.success(request, "Writing assessment submitted! Admin will review it.")
        return redirect('myapp:student_dashboard')
    return render(request, "student/skill_writing.html")

@login_required
def client_dashboard(request):
    if request.user.role != 'client':
        return redirect('myapp:home')
    
    user = request.user
    
    # 1. Get the list of jobs (for the recent postings table)
    jobs = user.posted_jobs.all().order_by('-created_at')
    
    
    # 2. Count active jobs
    
    active_jobs_count = jobs.filter(status__in=['open', 'assigned']).count()
    
    # 3. Count applicants reviewing
    
    applicants_reviewing_count = Application.objects.filter(
        job__client=user, 
        is_accepted=False, 
        is_rejected=False
    ).count()
    
    # 4. Count completed gigs
    completed_gigs_count = jobs.filter(status='completed').count()
    
    context = {
        'jobs': jobs,
        'active_jobs_count': active_jobs_count,
        'applicants_reviewing_count': applicants_reviewing_count,
        'completed_gigs_count': completed_gigs_count,
    }
    return render(request, 'client/dashboard.html', context)

@login_required
def job_create(request):
    # Allow clients or Superusers to post gigs or jobs the admin verifies
    if request.user.role != 'client' and not request.user.is_superuser:
        messages.error(request, "Access Denied. Only Clients can post gigs.")
        return redirect('myapp:home')

    if request.method == 'POST':
        form = JobForm(request.POST, request.FILES)
        if form.is_valid():
            job = form.save(commit=False)
            job.client = request.user
            
            # admin posts a gig and it goes immediately, clients gigs have to be approved 
            if request.user.is_superuser:
                job.status = 'open' 
                message_text = "Gig posted successfully! It is Live."
            else:
                job.status = 'review'
                message_text = "Gig posted! Pending admin approval."
                
            job.save()
            form.save_m2m() # important for ManyToMany fields (eg skills)
            messages.success(request, message_text)
            
            if request.user.is_superuser:
                return redirect('myapp:admin_dashboard')
            return redirect('myapp:client_dashboard')
    else:
        form = JobForm()
    return render(request, 'client/job_create.html', {'form': form})

@login_required
def job_edit(request, pk):
    job = get_object_or_404(Job, pk=pk, client=request.user)
    if request.method == 'POST':
        form = JobForm(request.POST, instance=job)
        if form.is_valid():
            form.save()
            messages.success(request, "Gig updated.")
            return redirect('myapp:client_dashboard')
    else:
        form = JobForm(instance=job)
    return render(request, 'client/job_edit.html', {'form': form, 'job': job})

@login_required
def applicant_review(request, job_id):
    job = get_object_or_404(Job, pk=job_id, client=request.user)
    
    if request.method == 'POST':
        app_id = request.POST.get('applicant_id')
        application = get_object_or_404(Application, pk=app_id)
        
        job.assigned_to = application.student
        job.status = 'assigned'
        job.save()
        messages.success(request, f"You hired {application.student.username}!")
        return redirect('myapp:client_dashboard')

    return render(request, 'client/applicant_review.html', {'job': job})

# donor views
@login_required
def donor_dashboard(request):
    # 1. get donation history
    donations = request.user.donations.all().order_by('-date')
    
    # 2. Calculate Total Contributed Sum of only paid donations
    total_data = donations.filter(is_paid=True).aggregate(Sum('amount'))
    
    # If there are no donations, amount__sum will be None, so we verify it with 'or 0'
    total_contributed = total_data['amount__sum'] or 0
    
    # 3. Calculate Comrades Supported
    # Logic: assuming roughly Ksh 500 supports one comrade (meal/bundles)
    comrades_supported = int(total_contributed / 500)
    
    context = {
        'donations': donations,
        'total_contributed': total_contributed,
        'comrades_supported': comrades_supported
    }
    return render(request, 'donor/dashboard.html', context)

@login_required
def donate(request):
    if request.method == 'POST':
        amount = request.POST.get('amount')
        phone = request.POST.get('phone')
        
        # Create the donation record (initially unpaid)
        donation = Donation.objects.create(
            donor=request.user,
            amount=amount,
            is_paid=False 
        )
        
        # Pass the phone number to the payment page to trigger STK Push
        return render(request, 'donor/pay.html', {'donation': donation, 'phone_number': phone})
        
    return render(request, 'donor/donate_form.html')

@login_required
def donate_success(request):
    last_donation = Donation.objects.filter(donor=request.user).last()
    if last_donation:
        last_donation.is_paid = True
        last_donation.save()
    return render(request, 'donor/donate_success.html')

# mpesa callback
@csrf_exempt
def mpesa_confirmation(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # Add logic here to update the Donation model based on callback
            return JsonResponse({"status": "ok"})
        except:
            return HttpResponse(status=400)
    return HttpResponse(status=400)

# admin views
@login_required
def admin_dashboard(request):
    if not request.user.is_superuser:
        return redirect('myapp:home')
    
    #stats for dashboard
    total_users_count = User.objects.count()
    pending_gigs_count = Job.objects.filter(status='review').count()
    pending_assessments_count = SkillSubmission.objects.filter(status='pending').count()
    
    # Count expired gigs
    expired_gigs_count = Job.objects.filter(
        deadline__lt=timezone.now(), 
        status__in=['open', 'review', 'assigned']
    ).count()

    #Count pending applications neither accepted nor rejected
    pending_apps_count = Application.objects.filter(is_accepted=False, is_rejected=False).count()
    
    context = {
        'total_users_count': total_users_count,
        'pending_gigs_count': pending_gigs_count,
        'pending_assessments_count': pending_assessments_count,
        'expired_gigs_count': expired_gigs_count,
        'pending_apps_count': pending_apps_count,
    }
    
    return render(request, 'custom_admin/dashboard.html', context)

@login_required
def admin_verify_gigs(request):
    if not request.user.is_superuser:
        return redirect('myapp:home')
    
    if request.method == 'POST':
        job_id = request.POST.get('job_id')
        action = request.POST.get('action')
        job = Job.objects.get(pk=job_id)
        
        if action == 'approve':
            job.status = 'open'
            messages.success(request, "Gig Approved & Live.")
        elif action == 'reject':
            job.status = 'cancelled'
            messages.warning(request, "Gig Rejected.")
        job.save()
        return redirect('myapp:admin_verify_gigs')

    pending_jobs = Job.objects.filter(status='review')
    return render(request, 'custom_admin/verify_gigs.html', {'pending_jobs': pending_jobs})

@login_required
def admin_users(request):
    if not request.user.is_superuser:
        return redirect('myapp:home')
    users = User.objects.all().order_by('-date_joined')
    return render(request, 'custom_admin/manage_users.html', {'users': users})

@login_required
def admin_ban_user(request, user_id):
    if not request.user.is_superuser:
        messages.error(request, "Unauthorized action.")
        return redirect('myapp:home')
    
    user_to_mod = get_object_or_404(User, pk=user_id)
    
    if user_to_mod == request.user:
        messages.error(request, "You cannot ban yourself!")
        return redirect('myapp:admin_users')

    if user_to_mod.is_active:
        user_to_mod.is_active = False
        messages.warning(request, f"User {user_to_mod.username} has been BANNED.")
    else:
        user_to_mod.is_active = True
        messages.success(request, f"User {user_to_mod.username} has been ACTIVATED.")
    
    user_to_mod.save()
    return redirect('myapp:admin_users')

@login_required
def admin_stats(request):
    if not request.user.is_superuser:
        return redirect('myapp:home')
    return render(request, 'custom_admin/site_stats.html')

@login_required
def admin_verify_skills(request):
    if not request.user.is_superuser:
        return redirect('myapp:home')
    
    pending_submissions = SkillSubmission.objects.filter(status='pending').order_by('-submitted_at')
    return render(request, 'custom_admin/verify_skills.html', {'submissions': pending_submissions})

@login_required
def admin_approve_skill(request, submission_id):
    if not request.user.is_superuser:
        return redirect('myapp:home')
        
    submission = get_object_or_404(SkillSubmission, pk=submission_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve':
            submission.status = 'approved'
            submission.save()
            
            profile = submission.student.student_profile
            skill_obj, created = Skill.objects.get_or_create(name=submission.skill_name)
            profile.skills.add(skill_obj)
            
            profile.badges_earned += 1
            profile.save()
            
            messages.success(request, f"Skill approved! {submission.student.username} now has the {submission.skill_name} badge.")
            
        elif action == 'reject':
            submission.status = 'rejected'
            submission.save()
            messages.warning(request, "Skill submission rejected.")
            
    return redirect('myapp:admin_verify_skills')

# management of expired gigs views

@login_required
def admin_manage_expired(request):
    if not request.user.is_superuser:
        return redirect('myapp:home')

    # Get all gigs where deadline has passed
    expired_jobs = Job.objects.filter(
        deadline__lt=timezone.now(),
        status__in=['open', 'review', 'assigned']
    ).order_by('deadline')

    return render(request, 'custom_admin/manage_expired.html', {'expired_jobs': expired_jobs})

@login_required
def admin_delete_gig(request, job_id):
    if not request.user.is_superuser:
        return redirect('myapp:home')
        
    job = get_object_or_404(Job, pk=job_id)
    job.delete()
    messages.success(request, "Gig deleted successfully.")
    
    return redirect('myapp:admin_manage_expired')

# application workflow views

@login_required
def admin_manage_applications(request):
    if not request.user.is_superuser:
        return redirect('myapp:home')

    # Get all applications that haven't been decided yet
    pending_apps = Application.objects.filter(
        is_accepted=False, 
        is_rejected=False
    ).order_by('-created_at')

    return render(request, 'custom_admin/manage_applications.html', {'pending_apps': pending_apps})

@login_required
def admin_process_application(request, app_id):
    if not request.user.is_superuser:
        return redirect('myapp:home')
        
    application = get_object_or_404(Application, pk=app_id)
    job = application.job
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve':
            # 1. Accept this application
            application.is_accepted = True
            application.save()
            
            # 2. Assign the job to this student
            job.assigned_to = application.student
            job.status = 'assigned' 
            job.save()
            
            # 3. Reject other applicants for this same job 
            other_apps = Application.objects.filter(job=job).exclude(id=application.id)
            other_apps.update(is_rejected=True)
            
            messages.success(request, f"Application Approved. Job assigned to {application.student.username}.")
            
        elif action == 'reject':
            application.is_rejected = True
            application.save()
            messages.warning(request, "Application Rejected.")
            
    return redirect('myapp:admin_manage_applications')