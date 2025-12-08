from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

# 1. user roles (roles of web user)
ROLE_CHOICES = (
    ('student', 'Student'),
    ('client', 'Client'),
    ('donor', 'Donor'),
    ('admin', 'Admin'),
)

# 2. Custom user model
class User(AbstractUser):
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')
    is_verified = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=15, blank=True, null=True, help_text="Required for M-Pesa")
    profile_image = models.ImageField(upload_to='profiles/', blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({self.role})"

# 3. Skill model (UPDATED)
class Skill(models.Model):
    name = models.CharField(max_length=100, unique=True)
    # NEW: Stores the bootstrap icon class (e.g., 'bi-code-slash', 'bi-brush', 'bi-pen')
    # This allows the dashboard to show cool icons for each badge!
    icon_class = models.CharField(max_length=50, default='bi-star-fill', help_text="Bootstrap icon class")

    def __str__(self):
        return self.name

# 4. User profile (student)
class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    
    # academic input info
    university = models.CharField(max_length=100)
    course = models.CharField(max_length=100)
    year_of_study = models.IntegerField(default=1)
    
    # Skills  
    skills = models.ManyToManyField(Skill, blank=True, related_name='students') 
    # Badges earned by student from skill
    badges_earned = models.IntegerField(default=0)
    exam_mode = models.BooleanField(default=False)

    # Verification Fields
    # This checks if the student is generally verified (Global verification)
    is_skill_verified = models.BooleanField(default=False) 
    skill_assessment_submission = models.FileField(upload_to='assessments/', null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.university}"

# 5. Posted gigs and jobs (UPDATED)
class Job(models.Model):
    STATUS_CHOICES = (
        ('open', 'Open'),
        ('review', 'Under Review'),
        ('assigned', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posted_jobs')
    
    # CRITICAL: related_name='assigned_jobs' allows us to use request.user.assigned_jobs in the view
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_jobs')
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    # skills required for the job
    required_skills = models.ManyToManyField(Skill, blank=True)
    
    budget = models.DecimalField(max_digits=10, decimal_places=2)
    deadline = models.DateTimeField(null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='review')
    created_at = models.DateTimeField(auto_now_add=True)
    
    # NEW: Tracks when the job was finished (useful for sorting earnings history)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.title} - {self.get_status_display()}"

# 6. Application fields
class Application(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='applications')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='my_applications')
    cover_letter = models.TextField()
    bid_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    is_accepted = models.BooleanField(default=False)
    is_rejected = models.BooleanField(default=False)

    class Meta:
        unique_together = ('job', 'student')

    def __str__(self):
        return f"{self.student.username} applied to {self.job.title}"

# 7. Donation field
class Donation(models.Model):
    donor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='donations')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    message = models.TextField(blank=True)
    
    mpesa_code = models.CharField(max_length=50, blank=True, null=True)
    is_paid = models.BooleanField(default=False)
    date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Ksh {self.amount} - {'Paid' if self.is_paid else 'Pending'}"

# 8. Skill submission for the verification of the system
class SkillSubmission(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='skill_submissions')
    skill_name = models.CharField(max_length=100) # e.g., "Graphic Design"
    proof_link = models.URLField(blank=True, null=True)
    proof_file = models.FileField(upload_to='skills_proof/', blank=True, null=True)
    description = models.TextField(blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.username} - {self.skill_name}"