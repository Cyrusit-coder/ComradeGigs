from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

# 1. User Roles
ROLE_CHOICES = (
    ('student', 'Student'),
    ('client', 'Client'),
    ('donor', 'Donor'),
    ('admin', 'Admin'),
)

# 2. Custom User Model
class User(AbstractUser):
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')
    
    # FIX: This is just a field now. No conflicting function.
    is_verified = models.BooleanField(default=False) 
    
    phone_number = models.CharField(max_length=15, blank=True, null=True, help_text="Required for M-Pesa")
    profile_image = models.ImageField(upload_to='profiles/', blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({self.role})"

# 3. Skill Model (With Icon support)
class Skill(models.Model):
    name = models.CharField(max_length=100, unique=True)
    icon_class = models.CharField(max_length=50, default='bi-star-fill', help_text="Bootstrap icon class")

    def __str__(self):
        return self.name

# 4. Student Profile
class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    
    # Academic Info
    university = models.CharField(max_length=100)
    course = models.CharField(max_length=100)
    year_of_study = models.IntegerField(default=1)
    
    # Skills & Badges
    skills = models.ManyToManyField(Skill, blank=True, related_name='students') 
    badges_earned = models.IntegerField(default=0)
    exam_mode = models.BooleanField(default=False)

    # --- Verification Fields ---
    
    # 1. Skill Verification (Tests)
    is_skill_verified = models.BooleanField(default=False) 
    skill_assessment_submission = models.FileField(upload_to='assessments/', null=True, blank=True)

    # 2. Identity Verification (School ID)
    school_id_image = models.ImageField(upload_to='student_ids/', blank=True, null=True)
    is_id_verified = models.BooleanField(default=False)
    
    # Rejection Reason
    id_rejection_reason = models.TextField(blank=True, null=True, help_text="Reason for rejecting the ID")

    def __str__(self):
        return f"{self.user.username} - {self.university}"

# 5. Job / Gig Model
class Job(models.Model):
    STATUS_CHOICES = (
        ('open', 'Open'),
        ('review', 'Under Review'),
        ('assigned', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posted_jobs')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_jobs')
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    # Skills required
    required_skills = models.ManyToManyField(Skill, blank=True)
    
    budget = models.DecimalField(max_digits=10, decimal_places=2)
    deadline = models.DateTimeField(null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='review')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.title} - {self.get_status_display()}"

# 6. Application Model
class Application(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    )

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='applications')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='my_applications')
    
    # Proposal & Files
    proposal = models.TextField(help_text="Short message to the client") 
    bid_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # File Uploads
    cv = models.FileField(upload_to='applications/cvs/', blank=True, null=True)
    cover_letter_file = models.FileField(upload_to='applications/cover_letters/', blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    
    is_accepted = models.BooleanField(default=False)
    is_rejected = models.BooleanField(default=False)

    class Meta:
        unique_together = ('job', 'student')

    def __str__(self):
        return f"{self.student.username} applied to {self.job.title}"

# 7. Donation Model
class Donation(models.Model):
    donor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='donations')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    message = models.TextField(blank=True)
    
    mpesa_code = models.CharField(max_length=50, blank=True, null=True)
    is_paid = models.BooleanField(default=False)
    date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Ksh {self.amount} - {'Paid' if self.is_paid else 'Pending'}"

# 8. Payment Model
class Payment(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
    )
    
    payer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments_made')
    beneficiary = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments_received')
    
    job = models.ForeignKey(Job, on_delete=models.SET_NULL, null=True, blank=True)
    donation = models.ForeignKey(Donation, on_delete=models.SET_NULL, null=True, blank=True)
    
    purpose = models.CharField(max_length=20) # 'JOB' or 'DONATION'
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    checkout_request_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    mpesa_receipt = models.CharField(max_length=50, null=True, blank=True)
    result_code = models.IntegerField(null=True, blank=True)
    raw_callback = models.JSONField(null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.purpose} - {self.amount} ({self.status})"

# 9. Skill Verification
class SkillSubmission(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='skill_submissions')
    skill_name = models.CharField(max_length=100)
    proof_link = models.URLField(blank=True, null=True)
    proof_file = models.FileField(upload_to='skills_proof/', blank=True, null=True)
    description = models.TextField(blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.username} - {self.skill_name}"

# 10. Event Model
class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    date = models.DateTimeField()
    location = models.CharField(max_length=200)
    image = models.ImageField(upload_to='event_images/', blank=True, null=True) 
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

# 11. Site Updates (Admin Announcements)
class SiteUpdate(models.Model):
    AUDIENCE_CHOICES = (
        ('all', 'All Users'),
        ('student', 'Students Only'),
        ('client', 'Clients Only'),
        ('donor', 'Donors Only'),
    )
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # New field for targeting specific groups
    audience = models.CharField(max_length=10, choices=AUDIENCE_CHOICES, default='all')
    
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.title} ({self.get_audience_display()})"