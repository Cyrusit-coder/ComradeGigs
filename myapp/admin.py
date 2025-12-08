from django.contrib import admin
from .models import User, StudentProfile, Skill, Job, Application, Donation


# Register your models here.
# 1. USER ADMIN - Manage all accounts
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'role', 'phone_number', 'is_verified', 'date_joined')
    list_filter = ('role', 'is_verified', 'is_staff')
    search_fields = ('username', 'email', 'phone_number')
    ordering = ('-date_joined',)

# 2. STUDENT PROFILE - See academic details
@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'university', 'course', 'year_of_study', 'badges_earned')
    list_filter = ('university', 'year_of_study')
    search_fields = ('user__username', 'university', 'course')

# 3. JOB/GIG ADMIN - Verify posts here
@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('title', 'client', 'budget', 'status', 'deadline', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('title', 'description', 'client__username')
    list_editable = ('status',) # Allows you to approve gigs directly from the list!
    date_hierarchy = 'created_at'

# 4. APPLICATIONS - See who applied where
@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('student', 'job', 'bid_amount', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('student__username', 'job__title')

# 5. DONATIONS - Track money
@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ('donor', 'amount', 'is_paid', 'mpesa_code', 'date')
    list_filter = ('is_paid', 'date')
    search_fields = ('mpesa_code', 'donor__username')

# 6. SKILLS - Manage the list of available skills
@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
