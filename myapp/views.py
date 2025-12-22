import json
import traceback
import qrcode
import io
import base64
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
from django.core.mail import send_mail  # Required for emails

# --- 2FA IMPORTS ---
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp import devices_for_user

# --- CONFIGURATION ---
WHATSAPP_CHANNEL_URL = "https://whatsapp.com/channel/0029Vb7l5He3rZZdfyskEv0s"

# Safe Import for M-Pesa
try:
    from .mpesa import stk_push
except ImportError:
    stk_push = None
    print("WARNING: 'requests' library not found. M-Pesa functions will fail.")

from .models import User, Job, Application, Donation, StudentProfile, Skill, SkillSubmission, Payment, Event, SiteUpdate
from .forms import (
    StudentRegisterForm, ClientRegisterForm, DonorRegisterForm, 
    JobForm, StudentProfileForm, DonationForm, EventForm, 
    ApplicationForm, SiteUpdateForm, StudentIDUploadForm,
    AdminProfileForm 
)

# 1. PUBLIC PAGES
def home(request):
    return render(request, 'pages/home.html')

def about(request):
    return render(request, 'pages/about.html')

def events(request):
    events = Event.objects.all().order_by('-date')
    return render(request, 'pages/events.html', {'events': events})

def contact(request):
    if request.method == 'POST':
        messages.success(request, "Message sent! We'll get back to you shortly.")
        return redirect('myapp:contact')
    return render(request, 'pages/contact.html')

def faqs(request):
    return render(request, 'pages/faqs.html')

def terms_of_service(request):
    return render(request, 'pages/terms.html')

def privacy_policy(request):
    return render(request, 'pages/privacy.html')

# 2. AUTHENTICATION & SECURITY 

# --- UPDATED LOGIN VIEW (Check for 2FA) ---
def login_view(request):
    from django.contrib.auth.views import LoginView
    
    class CustomLoginView(LoginView):
        def get_success_url(self):
            user = self.request.user
            
            # 1. Check if user has a confirmed 2FA device
            if user.totpdevice_set.filter(confirmed=True).exists():
                return reverse('myapp:verify_2fa_login') # <--- Redirect to Code Entry
            
            # 2. Normal Redirects
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

# --- 2FA SETUP & VERIFY VIEWS ---
@login_required
def setup_2fa(request):
    user = request.user
    
    # Get or Create a TOTP Device
    device, created = TOTPDevice.objects.get_or_create(user=user, name='default')
    
    if request.method == 'POST':
        token = request.POST.get('token')
        if device.verify_token(token):
            device.confirmed = True
            device.save()
            messages.success(request, "2FA Security Enabled Successfully! 🔐")
            
            if user.role == 'student': 
                return redirect('myapp:student_dashboard')
            if user.role == 'client': 
                return redirect('myapp:client_dashboard')
            if user.role == 'donor': 
                return redirect('myapp:donor_dashboard')
            return redirect('myapp:home')
        else:
            messages.error(request, "Invalid Code. Please try again.")

    if not device.confirmed:
        otp_url = device.config_url
        img = qrcode.make(otp_url)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
        return render(request, 'auth/setup_2fa.html', {'qr_code': qr_code_base64})
    
    else:
        messages.info(request, "2FA is already active on your account.")
        return redirect('myapp:student_dashboard')

def verify_2fa_login(request):
    if request.method == 'POST':
        token = request.POST.get('token')
        user = request.user
        
        device = user.totpdevice_set.filter(confirmed=True).first()
        
        if device and device.verify_token(token):
            # Mark verified for session
            from django_otp import login as otp_login
            otp_login(request, device)
            
            messages.success(request, "Identity Verified. Welcome.")
            
            if user.role == 'student': 
                return redirect('myapp:student_dashboard')
            elif user.role == 'client': 
                return redirect('myapp:client_dashboard')
            elif user.role == 'donor': 
                return redirect('myapp:donor_dashboard')
            elif user.role == 'admin': 
                return redirect('myapp:admin_dashboard')
            return redirect('myapp:home')
        else:
            messages.error(request, "Invalid 2FA Code.")
            
    return render(request, 'auth/verify_2fa.html')

# --- GOOGLE SOCIAL AUTH HANDLERS (UPDATED) ---
@login_required
def social_auth_dispatch(request):
    """
    Redirects Google logins.
    If the user has a role but NO profile (fresh Google signup), force them to choose a role.
    """
    user = request.user
    
    # Check if this is a "Fake" student (Default role, but no profile data)
    if user.role == 'student':
        # If they don't have a StudentProfile object yet, they are new.
        if not hasattr(user, 'student_profile'):
             return redirect('myapp:select_role')
        return redirect('myapp:student_dashboard')

    elif user.role == 'client':
        return redirect('myapp:client_dashboard')
        
    elif user.role == 'donor':
        return redirect('myapp:donor_dashboard')
        
    elif user.role == 'admin':
        return redirect('myapp:admin_dashboard')
        
    # If no role, go to selection
    return redirect('myapp:select_role')

@login_required
def select_role(request):
    if request.method == 'POST':
        role = request.POST.get('role')
        user = request.user
        
        if role in ['student', 'client', 'donor']:
            user.role = role
            user.save()
            
            # --- EMAIL LOGIC MOVED HERE (So Google Users get it too) ---
            if role == 'student':
                from .models import StudentProfile
                StudentProfile.objects.get_or_create(user=user, defaults={
                    'university': 'Pending', 'course': 'Pending'
                })
                
                subject = f"Welcome to the Alliance | ComradeGigs 🚀"
                message = f"""Dear {user.username},\n\nWelcome to ComradeGigs. You have joined as a STUDENT.\nWe are reviewing your details.\n\nBest,\nComradeGigs Team"""
                
                # --- EMAIL DEBUG START ---
                try:
                    print(f"Attempting to send email to {user.email}...")
                    send_mail(subject, message, settings.EMAIL_HOST_USER, [user.email], fail_silently=False)
                    print("Email sent successfully!")
                except Exception as e:
                    print(f"EMAIL ERROR: {e}")
                # --- EMAIL DEBUG END ---

                messages.success(request, "Role assigned! Please complete your profile.")
                return redirect('myapp:profile_edit')
            
            elif role == 'client':
                subject = f"Welcome Partner | ComradeGigs 🤝"
                message = f"""Dear {user.username},\n\nWelcome to the ComradeGigs Business Alliance.\nYour Client account is pending admin verification.\n\nBest,\nComradeGigs Team"""
                try:
                    print(f"Attempting to send email to {user.email}...")
                    send_mail(subject, message, settings.EMAIL_HOST_USER, [user.email], fail_silently=False)
                    print("Email sent successfully!")
                except Exception as e:
                    print(f"EMAIL ERROR: {e}")
                
                messages.success(request, "Client account setup! Check your email.")
                return redirect('myapp:client_dashboard')

            elif role == 'donor':
                subject = f"Thank You for Joining | ComradeGigs 🌍"
                message = f"""Dear {user.username},\n\nThank you for joining as a DONOR.\nYour support changes lives.\n\nBest,\nComradeGigs Team"""
                try:
                    print(f"Attempting to send email to {user.email}...")
                    send_mail(subject, message, settings.EMAIL_HOST_USER, [user.email], fail_silently=False)
                    print("Email sent successfully!")
                except Exception as e:
                    print(f"EMAIL ERROR: {e}")
                
                messages.success(request, "Donor account setup! Welcome.")
                return redirect('myapp:donor_dashboard')
            
    return render(request, 'auth/select_role.html')

# --- REGISTRATION VIEWS ---
def register_landing(request):
    return render(request, 'auth/register_landing.html')

def register_student(request):
    if request.method == 'POST':
        form = StudentRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # --- EMAIL ---
            subject = f"Welcome to the Alliance | ComradeGigs 🚀"
            message = f"""
Dear {user.username},

Welcome to ComradeGigs. We are thrilled to have you join our ecosystem.

You have just taken a decisive step towards connecting with Kenya’s top verified talent and opportunities. Whether you are here to build your career or hire the best, you are now part of a community dedicated to innovation, integrity, and growth.

What to expect next:
1. Verified Access: Our team is reviewing your details to ensure a secure environment.
2. Instant Connections: Browse active gigs or post your requirements immediately.
3. Secure Transactions: All payments are protected and processed via M-Pesa.

We look forward to cooperating with you to build something impactful.

Let's get to work.

Best regards,

Cyrus Njeri
Platform Administrator & System Architect
ComradeGigs
https://comradegigs.onrender.com
            """
            try:
                print(f"Attempting to send email to {user.email}...")
                send_mail(subject, message, settings.EMAIL_HOST_USER, [user.email], fail_silently=False)
                print("Email sent successfully!")
            except Exception as e:
                print(f"Email error: {e}")
            # --- END EMAIL ---

            login(request, user)
            messages.success(request, "Welcome back, Comrade! Check your email for a welcome message.")
            return redirect('myapp:student_dashboard')
    else:
        form = StudentRegisterForm()
    return render(request, 'auth/register_student.html', {'form': form})

def register_client(request):
    if request.method == 'POST':
        form = ClientRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()

            # --- EMAIL ---
            subject = f"Welcome Partner | ComradeGigs 🤝"
            message = f"""
Dear {user.username},

Welcome to the ComradeGigs Business Alliance.

Thank you for choosing to hire from Kenya's top pool of university talent. You are helping bridge the gap between education and industry.

Important Next Steps:
1. Account Verification: Your account is currently pending admin verification to ensure platform safety. This typically takes less than 2 hours.
2. Posting Gigs: Once verified, you can post unlimited gigs and review applicants instantly.
3. Secure Payments: All transactions are protected via our M-Pesa escrow system.

We are committed to delivering quality results for your business needs.

Let's get to work.

Best regards,

Cyrus Njeri
Platform Administrator
ComradeGigs
https://comradegigs.onrender.com
            """
            try:
                print(f"Attempting to send email to {user.email}...")
                send_mail(subject, message, settings.EMAIL_HOST_USER, [user.email], fail_silently=False)
                print("Email sent successfully!")
            except Exception as e:
                print(f"Email error: {e}")
            # --- END EMAIL ---

            login(request, user)
            messages.success(request, "Client account created. Check your email. Admin verification pending.")
            return redirect('myapp:client_dashboard')
    else:
        form = ClientRegisterForm()
    return render(request, 'auth/register_client.html', {'form': form})

def register_donor(request):
    if request.method == 'POST':
        form = DonorRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()

            # --- EMAIL ---
            subject = f"Thank You for Joining the Vision | ComradeGigs 🌍"
            message = f"""
Dear {user.username},

Welcome to the ComradeGigs Alliance. We are deeply grateful for your presence here.

Your decision to join as a supporter creates a direct pathway for students to earn dignity through work, not charity. You are empowering the next generation of Kenyan innovators.

Transparency Promise:
We ensure complete transparency on how contributions are used to verify student skills and facilitate safe transactions.

Thank you for believing in the vision.

Warm regards,

Cyrus Njeri
Platform Administrator
ComradeGigs
https://comradegigs.onrender.com
            """
            try:
                print(f"Attempting to send email to {user.email}...")
                send_mail(subject, message, settings.EMAIL_HOST_USER, [user.email], fail_silently=False)
                print("Email sent successfully!")
            except Exception as e:
                print(f"Email error: {e}")
            # --- END EMAIL ---

            login(request, user)
            messages.success(request, "Thank you for joining the alliance. Check your email for a welcome note.")
            return redirect('myapp:donor_dashboard')
    else:
        form = DonorRegisterForm()
    return render(request, 'auth/register_donor.html', {'form': form})

# 3. STUDENT VIEWS 
@login_required
def student_dashboard(request):
    if request.user.role != 'student':
        return redirect('myapp:home')
    
    apps = request.user.my_applications.all().order_by('-created_at')[:5]
    active_jobs_list = request.user.assigned_jobs.filter(status='assigned').order_by('deadline')
    
    earnings_data = request.user.assigned_jobs.filter(status='completed').aggregate(Sum('budget'))
    total_earnings = earnings_data['budget__sum'] or 0
    
    site_updates = SiteUpdate.objects.filter(
        is_active=True, 
        audience__in=['all', 'student']
    ).order_by('-created_at')[:3]
    
    context = {
        'my_apps': apps,
        'active_jobs_count': active_jobs_list.count(),
        'active_jobs_list': active_jobs_list, 
        'total_earnings': total_earnings,
        'site_updates': site_updates,
        'whatsapp_url': WHATSAPP_CHANNEL_URL,
    }
    return render(request, 'student/dashboard.html', context)

@login_required
def upload_school_id(request):
    if request.user.role != 'student':
        return redirect('myapp:home')
        
    profile = request.user.student_profile
    
    if request.method == 'POST':
        form = StudentIDUploadForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            profile.id_rejection_reason = None
            profile.save()
            
            messages.success(request, "School ID uploaded! Waiting for Admin verification.")
            return redirect('myapp:student_dashboard')
    else:
        form = StudentIDUploadForm(instance=profile)
        
    return render(request, 'student/upload_id.html', {'form': form})

@login_required
def job_list(request):
    if request.user.role == 'student':
        profile = request.user.student_profile
        if not profile.is_id_verified:
            messages.error(request, "Please upload your School ID and wait for verification first.")
            return redirect('myapp:student_dashboard')
        if not profile.is_skill_verified:
            messages.error(request, "You must pass a skill assessment to browse gigs.")
            return redirect('myapp:student_dashboard')

    # FIX: Use 'is_account_verified' here!
    elif request.user.role == 'client' and not request.user.is_account_verified:
        messages.error(request, "Your account is pending verification.")
        return redirect('myapp:client_dashboard')

    jobs = Job.objects.filter(status='open').order_by('-created_at')
    query = request.GET.get('q')
    if query:
        jobs = jobs.filter(title__icontains=query)
    return render(request, 'student/job_list.html', {'jobs': jobs})

@login_required
def job_detail(request, pk):
    job = get_object_or_404(Job, pk=pk)
    
    if request.method == 'POST':
        if request.user.role != 'student':
            messages.error(request, "Only Student accounts can apply.")
            return redirect('myapp:job_detail', pk=pk)

        if not request.user.student_profile.is_skill_verified:
             messages.error(request, "You must be verified to apply.")
             return redirect('myapp:job_detail', pk=pk)

        if Application.objects.filter(job=job, student=request.user).exists():
            messages.warning(request, "You have already applied for this gig!")
        else:
            form = ApplicationForm(request.POST, request.FILES)
            if form.is_valid():
                app = form.save(commit=False)
                app.job = job
                app.student = request.user
                app.save()
                messages.success(request, "Application sent successfully!")
            else:
                messages.error(request, "Error submitting application. Check file types/sizes.")
        
        return redirect('myapp:job_detail', pk=pk)
    
    form = ApplicationForm()
    return render(request, 'student/job_detail.html', {'job': job, 'form': form})

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

# 4. CLIENT VIEWS 
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
    
    site_updates = SiteUpdate.objects.filter(
        is_active=True, 
        audience__in=['all', 'client']
    ).order_by('-created_at')[:3]
    
    context = {
        'jobs': jobs,
        'active_jobs_count': active_jobs_count,
        'applicants_reviewing_count': applicants_reviewing_count,
        'completed_gigs_count': completed_gigs_count,
        'site_updates': site_updates,
        'whatsapp_url': WHATSAPP_CHANNEL_URL,
    }
    return render(request, 'client/dashboard.html', context)

@login_required
def job_create(request):
    if not request.user.is_superuser:
        # FIX: Use 'is_account_verified' here!
        if request.user.role != 'client' or not request.user.is_account_verified:
            messages.error(request, "Access Denied. Account verification required.")
            return redirect('myapp:client_dashboard')

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
        action = request.POST.get('action') 
        application = get_object_or_404(Application, pk=app_id)
        
        if action == 'hire':
            application.status = 'accepted'
            application.is_accepted = True
            application.save()

            other_apps = job.applications.exclude(id=app_id)
            other_apps.update(status='rejected', is_rejected=True)

            job.assigned_to = application.student
            job.status = 'assigned'
            job.save()
            
            messages.success(request, f"You hired {application.student.username}!")
            return redirect('myapp:client_dashboard')
            
        elif action == 'reject':
            application.status = 'rejected'
            application.is_rejected = True
            application.save()
            
            messages.warning(request, "Applicant rejected.")
            return redirect('myapp:applicant_review', job_id=job.id)

    return render(request, 'client/applicant_review.html', {'job': job})

@login_required
def pay_for_job(request, job_id):
    job = get_object_or_404(Job, id=job_id)

    if request.user != job.client:
        return JsonResponse({"error": "Not allowed"}, status=403)

    if request.method == "POST":
        phone = request.POST.get("phone")
        amount = job.budget

        payment = Payment.objects.create(
            payer=request.user,
            beneficiary=job.assigned_to,
            purpose='JOB',
            amount=amount,
            job=job,
            status='PENDING'
        )

        # FIXED: Removed 'callback_url' to prevent TypeError
        if stk_push:
            try:
                resp = stk_push(
                    phone_number=phone,
                    amount=amount,
                    account_reference=f"JOB-{job.id}",
                    transaction_desc=f"Payment for {job.title}"
                )
            except TypeError as e:
                resp = {"error": f"Internal Error: {str(e)}"}
        else:
            resp = {"error": "M-Pesa library not loaded"}

        if "ResponseCode" in resp and resp["ResponseCode"] == "0":
            payment.checkout_request_id = resp.get("CheckoutRequestID")
            payment.save()
            messages.success(request, f"STK Push sent to {phone}. Check your phone to pay.")
        else:
            err_msg = resp.get('errorMessage') or resp.get('error') or "Unknown error"
            payment.status = 'FAILED'
            payment.save()
            messages.error(request, f"Payment Failed: {err_msg}")

        return redirect("myapp:client_dashboard")

    return render(request, "client/pay_for_job.html", {"job": job})

@login_required
def job_delete(request, pk):
    job = get_object_or_404(Job, pk=pk, client=request.user)
    
    if job.status in ['assigned', 'completed']:
        messages.error(request, "Cannot delete a gig that is in progress or completed.")
        return redirect('myapp:client_dashboard')
        
    job.delete()
    messages.success(request, "Gig deleted successfully.")
    return redirect('myapp:client_dashboard')

# --- 5. DONOR VIEWS ---
@login_required
def donor_dashboard(request):
    donations = request.user.donations.all().order_by('-date')
    total_data = donations.filter(is_paid=True).aggregate(Sum('amount'))
    total_contributed = total_data['amount__sum'] or 0
    comrades_supported = int(total_contributed / 500)
    
    site_updates = SiteUpdate.objects.filter(
        is_active=True, 
        audience__in=['all', 'donor']
    ).order_by('-created_at')[:3]
    
    context = {
        'donations': donations,
        'total_contributed': total_contributed,
        'comrades_supported': comrades_supported,
        'site_updates': site_updates,
        'whatsapp_url': WHATSAPP_CHANNEL_URL,
    }
    return render(request, 'donor/dashboard.html', context)

@login_required
def donate(request):
    if request.method == 'POST':
        amount = request.POST.get('amount')
        phone = request.POST.get('phone')

        # --- STEP 1: Auto-Correct Phone Number ---
        if phone:
            phone = str(phone).strip().replace(" ", "").replace("+", "")
            if phone.startswith("0"):
                phone = "254" + phone[1:]
        
        # --- STEP 2: Ensure Amount is a Number ---
        try:
            amount = int(float(amount))
        except (ValueError, TypeError):
            messages.error(request, "Invalid amount.")
            return redirect('myapp:donor_dashboard')

        # --- STEP 3: Check if Settings are Loaded ---
        if not settings.MPESA_SHORTCODE:
            messages.error(request, "System Error: M-Pesa Shortcode is missing in settings.")
            return redirect('myapp:donor_dashboard')

        # 1. Create Donation Record
        donation = Donation.objects.create(
            donor=request.user,
            amount=amount,
            is_paid=False
        )

        # 2. Create Payment Record
        payment = Payment.objects.create(
            payer=request.user,
            beneficiary=None, 
            purpose='DONATION',
            amount=amount,
            donation=donation,
            status='PENDING'
        )

        # 3. Trigger M-Pesa STK Push
        if stk_push:
            try:
                # --- FIX: FORCE REMOVE SPACES FROM SETTINGS ---
                # Safaricom rejects URLs with spaces. We clean the setting in memory
                # so the library uses the clean version automatically.
                if hasattr(settings, 'MPESA_CALLBACK_URL'):
                    settings.MPESA_CALLBACK_URL = str(settings.MPESA_CALLBACK_URL).strip()

                # --- DEBUG PRINT ---
                print("--- DEBUG INFO ---")
                print(f"Shortcode: {settings.MPESA_SHORTCODE}")
                print(f"Clean Callback URL: '{settings.MPESA_CALLBACK_URL}'") # Verify spaces are gone
                print(f"Phone: {phone}")
                print("------------------")

                # --- STEP 4: STRICT TRUNCATION ---
                # AccountReference: Max 12 chars
                ref = f"DON-{donation.id}"[:12] 
                
                # TransactionDesc: Max 13 chars
                desc = "Donation" 

                # Note: We do NOT pass 'callback_url' as an argument here 
                # because your library gave a TypeError previously. 
                # It will read the clean URL from settings.MPESA_CALLBACK_URL.
                resp = stk_push(
                    phone_number=phone,
                    amount=amount,
                    account_reference=ref,
                    transaction_desc=desc
                )
            except Exception as e:
                print(f"STK Push Crash: {e}")
                resp = {"error": str(e)}
        else:
            resp = {"error": "M-Pesa library not loaded"}

        # 4. Handle Response
        if "ResponseCode" in resp and resp["ResponseCode"] == "0":
            payment.checkout_request_id = resp.get("CheckoutRequestID")
            payment.save()
            messages.success(request, f"STK Push sent to {phone}. Please enter your PIN.")
            
            return render(
                request,
                'donor/pay.html',
                {'donation': donation, 'payment': payment, 'phone_number': phone}
            )
        else:
            # Log the full error to terminal for debugging
            print(f"M-Pesa Failed Response: {resp}")
            err_msg = resp.get('errorMessage') or resp.get('error') or "Transaction Failed"
            payment.status = 'FAILED'
            payment.save()
            messages.error(request, f"M-Pesa Error: {err_msg}")
            return redirect('myapp:donor_dashboard')

    return render(request, 'donor/donate_form.html')

@login_required
def donate_success(request):
    last_donation = Donation.objects.filter(
        donor=request.user,
        is_paid=True
    ).order_by('-date').first()
    return render(request, 'donor/donate_success.html', {'donation': last_donation})

# --- NEW: PAYMENT STATUS API (For Polling) ---
def check_payment_status(request, payment_id):
    """
    Checks if a specific payment has been marked as SUCCESS.
    Frontend calls this every few seconds.
    """
    try:
        payment = Payment.objects.get(id=payment_id)
        return JsonResponse({'status': payment.status})
    except Payment.DoesNotExist:
        return JsonResponse({'status': 'ERROR'}, status=404)

# 6. M-PESA CALLBACK 
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
            items = stk_callback.get("CallbackMetadata", {}).get("Item", [])
            receipt = None
            for item in items:
                if item.get("Name") == "MpesaReceiptNumber":
                    receipt = item.get("Value")
                    break

            payment.status = 'SUCCESS'
            payment.mpesa_receipt = receipt
            payment.save()

            if payment.purpose == 'DONATION' and payment.donation:
                donation = payment.donation
                donation.is_paid = True
                donation.mpesa_code = receipt
                donation.save()

            if payment.purpose == 'JOB' and payment.job:
                job = payment.job
                job.status = 'completed'
                job.save()

        else:
            payment.status = 'FAILED'
            payment.save()

        return JsonResponse({"status": "ok"})

    except Exception as e:
        traceback.print_exc()
        return HttpResponse(status=400)
# 7. ADMIN VIEWS 
@login_required
def admin_dashboard(request):
    if not request.user.is_superuser:
        return redirect('myapp:home')
    
    my_posted_jobs = Job.objects.filter(client=request.user).order_by('-created_at')
    
    total_users_count = User.objects.count()
    pending_gigs_count = Job.objects.filter(status='review').count()
    pending_assessments_count = SkillSubmission.objects.filter(status='pending').count()
    
    expired_gigs_count = Job.objects.filter(
        deadline__lt=timezone.now(), 
        status__in=['open', 'review', 'assigned']
    ).count()

    pending_apps_count = Application.objects.filter(is_accepted=False, is_rejected=False).count()
    
    events = Event.objects.all().order_by('date')
    site_updates = SiteUpdate.objects.filter(is_active=True).order_by('-created_at')

    context = {
        'total_users_count': total_users_count,
        'pending_gigs_count': pending_gigs_count,
        'pending_assessments_count': pending_assessments_count,
        'expired_gigs_count': expired_gigs_count,
        'pending_apps_count': pending_apps_count,
        'my_posted_jobs': my_posted_jobs,
        'events': events,
        'site_updates': site_updates,
        'whatsapp_url': WHATSAPP_CHANNEL_URL,
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
def admin_verify_user(request, user_id):
    if not request.user.is_superuser:
        return redirect('myapp:home')
        
    user_to_verify = get_object_or_404(User, pk=user_id)
    
    if user_to_verify.role == 'student':
        profile = user_to_verify.student_profile
        if profile.is_id_verified:
            profile.is_id_verified = False
            messages.warning(request, f"Student {user_to_verify.username} ID Unverified.")
        else:
            profile.is_id_verified = True
            messages.success(request, f"Student {user_to_verify.username} ID Verified.")
        profile.save()
        
    else:
        # FIX: Use 'is_account_verified' here!
        if user_to_verify.is_account_verified:
            user_to_verify.is_account_verified = False
            messages.warning(request, f"{user_to_verify.username} unverified.")
        else:
            user_to_verify.is_account_verified = True
            messages.success(request, f"{user_to_verify.username} successfully verified.")
        user_to_verify.save()
        
    return redirect('myapp:admin_users')

@login_required
def admin_reject_id(request, user_id):
    if not request.user.is_superuser:
        return redirect('myapp:home')
        
    user_to_reject = get_object_or_404(User, pk=user_id)
    
    if user_to_reject.role == 'student':
        profile = user_to_reject.student_profile
        
        profile.is_id_verified = False
        profile.id_rejection_reason = "Your ID was blurry or invalid. Please upload a clearer photo."
        
        if profile.school_id_image:
            profile.school_id_image.delete()
            
        profile.save()
        messages.warning(request, f"ID Rejected for {user_to_reject.username}. Image removed.")
        
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
            
            profile.is_skill_verified = True
            profile.badges_earned += 1
            profile.save()
            
            messages.success(request, f"Skill approved! {submission.student.username} verified.")
            
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
            application.status = 'accepted'
            application.is_accepted = True
            application.save()
            
            job.assigned_to = application.student
            job.status = 'assigned' 
            job.save()
            
            other_apps = Application.objects.filter(job=job).exclude(id=application.id)
            other_apps.update(status='rejected', is_rejected=True)
            
            messages.success(request, f"Application Approved. Job assigned to {application.student.username}.")
            
        elif action == 'reject':
            application.status = 'rejected'
            application.is_rejected = True
            application.save()
            messages.warning(request, "Application Rejected.")
            
    return redirect('myapp:admin_manage_applications')

@login_required
def event_create(request):
    if not request.user.is_superuser:
        messages.error(request, "Access Denied.")
        return redirect('myapp:home')
    
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES) 
        if form.is_valid():
            form.save()
            messages.success(request, "Event posted successfully!")
            return redirect('myapp:admin_dashboard')
    else:
        form = EventForm()
    
    return render(request, 'custom_admin/event_create.html', {'form': form})

@login_required
def event_edit(request, pk):
    if not request.user.is_superuser:
        return redirect('myapp:home')
        
    event = get_object_or_404(Event, pk=pk)
    
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, "Event updated successfully.")
            return redirect('myapp:admin_dashboard')
    else:
        form = EventForm(instance=event)
        
    return render(request, 'custom_admin/event_create.html', {'form': form})

@login_required
def create_site_update(request):
    if not request.user.is_superuser:
        return redirect('myapp:home')
        
    if request.method == 'POST':
        form = SiteUpdateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Announcement Posted Successfully!")
            return redirect('myapp:admin_dashboard')
    else:
        form = SiteUpdateForm()
    
    return render(request, 'custom_admin/create_update.html', {'form': form})

# 8. ADMIN PROFILE (NEW)
from .forms import AdminProfileForm

@login_required
def admin_profile(request):
    if not request.user.is_superuser:
        return redirect('myapp:home')
        
    if request.method == 'POST':
        form = AdminProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Admin Profile updated successfully! You look official now. 👔")
            return redirect('myapp:admin_profile')
    else:
        form = AdminProfileForm(instance=request.user)
        
    return render(request, 'custom_admin/profile.html', {'form': form})