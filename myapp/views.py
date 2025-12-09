import json
import traceback
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from django.utils import timezone

# Safe Import for M-Pesa (prevents crash if library missing)
try:
    from .mpesa import stk_push
except ImportError:
    stk_push = None
    print("WARNING: 'requests' library not found. M-Pesa functions will fail.")

from .models import User, Job, Application, Donation, StudentProfile, Skill, SkillSubmission, Payment
from .forms import (
    StudentRegisterForm, ClientRegisterForm, DonorRegisterForm, 
    JobForm, StudentProfileForm, DonationForm
)

# --- 1. PUBLIC PAGES ---
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

# --- 2. AUTHENTICATION ---
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

# --- 3. STUDENT VIEWS ---
@login_required
def student_dashboard(request):
    if request.user.role != 'student':
        return redirect('myapp:home')
    
    apps = request.user.my_applications.all().order_by('-created_at')[:5]
    active_jobs_list = request.user.assigned_jobs.filter(status='assigned').order_by('deadline')
    
    # Calculate Earnings (Jobs marked completed)
    earnings_data = request.user.assigned_jobs.filter(status='completed').aggregate(Sum('budget'))
    total_earnings = earnings_data['budget__sum'] or 0
    
    context = {
        'my_apps': apps,
        'active_jobs_count': active_jobs_list.count(),
        'active_jobs_list': active_jobs_list, 
        'total_earnings': total_earnings,     
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

# --- 4. CLIENT VIEWS ---
@login_required
def client_dashboard(request):
    if request.user.role != 'client':
        return redirect('myapp:home')
    
    user = request.user
    jobs = user.posted_jobs.all().order_by('-created_at')
    
    active_jobs_count = jobs.filter(status__in=['open', 'assigned']).count()
    applicants_reviewing_count = Application.objects.filter(
        job__client=user, 
        is_accepted=False, 
        is_rejected=False
    ).count()
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
    if request.user.role != 'client' and not request.user.is_superuser:
        messages.error(request, "Access Denied. Only Clients can post gigs.")
        return redirect('myapp:home')

    if request.method == 'POST':
        form = JobForm(request.POST, request.FILES)
        if form.is_valid():
            job = form.save(commit=False)
            job.client = request.user
            
            if request.user.is_superuser:
                job.status = 'open' 
                message_text = "Gig posted successfully! It is Live."
            else:
                job.status = 'review'
                message_text = "Gig posted! Pending admin approval."
                
            job.save()
            form.save_m2m()
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

# CLIENT PAY FOR JOB (M-Pesa Integration)
@login_required
def pay_for_job(request, job_id):
    job = get_object_or_404(Job, id=job_id)

    if request.user != job.client:
        return JsonResponse({"error": "Not allowed"}, status=403)

    if request.method == "POST":
        phone = request.POST.get("phone")
        amount = job.budget

        # 1. Create Payment Record
        payment = Payment.objects.create(
            payer=request.user,
            beneficiary=job.assigned_to, # Valid: Payment model has beneficiary
            purpose='JOB',
            amount=amount,
            job=job,
            status='PENDING'
        )

        # 2. Build Callback URL
        base_url = getattr(settings, 'MPESA_CALLBACK_URL', 'http://127.0.0.1:8000')
        if "confirmation" in base_url:
             callback_url = base_url
        else:
             callback_url = f"{base_url}/mpesa/confirmation"

        # 3. Trigger STK Push
        if stk_push:
            resp = stk_push(
                phone_number=phone,
                amount=amount,
                account_reference=f"JOB-{job.id}",
                transaction_desc=f"Payment for {job.title}",
                callback_url=callback_url,
            )
        else:
            resp = {"error": "M-Pesa library not loaded"}

        # 4. Handle Response
        if "ResponseCode" in resp and resp["ResponseCode"] == "0":
            checkout_request_id = resp.get("CheckoutRequestID")
            payment.checkout_request_id = checkout_request_id
            payment.save()
            messages.success(request, f"STK Push sent to {phone}. Check your phone to pay.")
        else:
            err_msg = resp.get('errorMessage') or resp.get('error') or "Unknown error"
            payment.status = 'FAILED'
            payment.save()
            messages.error(request, f"Payment Failed: {err_msg}")

        return redirect("myapp:client_dashboard")

    return render(request, "client/pay_for_job.html", {"job": job})

# --- 5. DONOR VIEWS ---
@login_required
def donor_dashboard(request):
    donations = request.user.donations.all().order_by('-date')
    total_data = donations.filter(is_paid=True).aggregate(Sum('amount'))
    total_contributed = total_data['amount__sum'] or 0
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

        # 1. Create Donation Record (NO BENEFICIARY FIELD HERE)
        donation = Donation.objects.create(
            donor=request.user,
            amount=amount,
            is_paid=False
        )

        # 2. Create Payment Record (Linked to Donation)
        payment = Payment.objects.create(
            payer=request.user,
            beneficiary=None, # Correct: Donations have no specific student beneficiary
            purpose='DONATION',
            amount=amount,
            donation=donation,
            status='PENDING'
        )

        # 3. Build Callback URL
        base_url = getattr(settings, 'MPESA_CALLBACK_URL', 'http://127.0.0.1:8000')
        if "confirmation" in base_url:
             callback_url = base_url
        else:
             callback_url = f"{base_url}/mpesa/confirmation"

        # 4. Trigger STK Push
        if stk_push:
            resp = stk_push(
                phone_number=phone,
                amount=amount,
                account_reference=f"DON-{donation.id}",
                transaction_desc="ComradeGigs Donation",
                callback_url=callback_url,
            )
        else:
            resp = {"error": "M-Pesa library not loaded"}

        # 5. Handle Response
        if "ResponseCode" in resp and resp["ResponseCode"] == "0":
            checkout_request_id = resp.get("CheckoutRequestID")
            payment.checkout_request_id = checkout_request_id
            payment.save()
            messages.success(request, f"STK Push sent to {phone}. Please confirm payment.")
            
            # Show waiting screen
            return render(
                request,
                'donor/pay.html',
                {'donation': donation, 'payment': payment, 'phone_number': phone}
            )
        else:
            err_msg = resp.get('errorMessage') or resp.get('error') or "Unknown error"
            payment.status = 'FAILED'
            payment.save()
            messages.error(request, f"Donation Failed: {err_msg}")
            return redirect('myapp:donor_dashboard')

    return render(request, 'donor/donate_form.html') 

@login_required
def donate_success(request):
    last_donation = Donation.objects.filter(
        donor=request.user,
        is_paid=True
    ).order_by('-date').first()
    return render(request, 'donor/donate_success.html', {'donation': last_donation})

# --- 6. M-PESA CALLBACK ---
@csrf_exempt
def mpesa_confirmation(request):
    if request.method != 'POST':
        return HttpResponse(status=400)

    try:
        data = json.loads(request.body.decode('utf-8'))
        body = data.get("Body", {})
        stk_callback = body.get("stkCallback", {})
        result_code = stk_callback.get("ResultCode")
        checkout_request_id = stk_callback.get("CheckoutRequestID")

        try:
            payment = Payment.objects.get(checkout_request_id=checkout_request_id)
        except Payment.DoesNotExist:
            traceback.print_exc()
            return JsonResponse({"error": "Payment not found"}, status=404)

        payment.result_code = result_code
        payment.raw_callback = data

        if result_code == 0:
            # SUCCESS
            items = stk_callback.get("CallbackMetadata", {}).get("Item", [])
            receipt = None
            for item in items:
                if item.get("Name") == "MpesaReceiptNumber":
                    receipt = item.get("Value")
                    break

            payment.status = 'SUCCESS'
            payment.mpesa_receipt = receipt
            payment.save()

            # Update Donation Record
            if payment.purpose == 'DONATION' and payment.donation:
                donation = payment.donation
                donation.is_paid = True
                donation.mpesa_code = receipt
                donation.save()

            # Update Job Record
            if payment.purpose == 'JOB' and payment.job:
                job = payment.job
                # Logic: Job is now paid for.
                # You might want to update job status to 'completed' or 'paid' depending on your flow
                job.save()

        else:
            # FAILED / CANCELLED
            payment.status = 'FAILED'
            payment.save()

        return JsonResponse({"status": "ok"})

    except Exception as e:
        traceback.print_exc()
        return HttpResponse(status=400)

# --- 7. ADMIN VIEWS ---
@login_required
def admin_dashboard(request):
    if not request.user.is_superuser:
        return redirect('myapp:home')
    
    # 1. Fetch Admin's Own Posted Gigs (For Payment Section)
    my_posted_jobs = Job.objects.filter(client=request.user).order_by('-created_at')

    # 2. Fetch Platform-wide Stats
    total_users_count = User.objects.count()
    pending_gigs_count = Job.objects.filter(status='review').count()
    pending_assessments_count = SkillSubmission.objects.filter(status='pending').count()
    
    expired_gigs_count = Job.objects.filter(
        deadline__lt=timezone.now(), 
        status__in=['open', 'review', 'assigned']
    ).count()

    pending_apps_count = Application.objects.filter(is_accepted=False, is_rejected=False).count()
    
    context = {
        'total_users_count': total_users_count,
        'pending_gigs_count': pending_gigs_count,
        'pending_assessments_count': pending_assessments_count,
        'expired_gigs_count': expired_gigs_count,
        'pending_apps_count': pending_apps_count,
        'my_posted_jobs': my_posted_jobs,  # Added this so the template can loop over it
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

@login_required
def admin_manage_expired(request):
    if not request.user.is_superuser:
        return redirect('myapp:home')

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

@login_required
def admin_manage_applications(request):
    if not request.user.is_superuser:
        return redirect('myapp:home')

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
            application.is_accepted = True
            application.save()
            
            job.assigned_to = application.student
            job.status = 'assigned' 
            job.save()
            
            other_apps = Application.objects.filter(job=job).exclude(id=application.id)
            other_apps.update(is_rejected=True)
            
            messages.success(request, f"Application Approved. Job assigned to {application.student.username}.")
            
        elif action == 'reject':
            application.is_rejected = True
            application.save()
            messages.warning(request, "Application Rejected.")
            
    return redirect('myapp:admin_manage_applications')