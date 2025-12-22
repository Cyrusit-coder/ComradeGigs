from django.contrib import admin
from .models import (
    User, StudentProfile, Skill, Job, Application, 
    Donation, Payment, SkillSubmission, Event, SiteUpdate
)

# 1. User Admin (FIXED)
class UserAdmin(admin.ModelAdmin):
    # Changed 'is_verified' to 'is_account_verified'
    list_display = ('username', 'email', 'role', 'is_account_verified', 'date_joined') 
    list_filter = ('role', 'is_account_verified', 'is_active') 
    search_fields = ('username', 'email')

# 2. Student Profile Admin
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'university', 'course', 'is_id_verified', 'is_skill_verified')
    list_filter = ('is_id_verified', 'is_skill_verified', 'year_of_study')
    search_fields = ('user__username', 'university')

# 3. Job Admin
class JobAdmin(admin.ModelAdmin):
    list_display = ('title', 'client', 'budget', 'status', 'deadline')
    list_filter = ('status', 'created_at')
    search_fields = ('title', 'description')

# 4. Application Admin
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('student', 'job', 'bid_amount', 'status', 'created_at')
    list_filter = ('status',)

# 5. Payment Admin
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('checkout_request_id', 'payer', 'amount', 'purpose', 'status')
    list_filter = ('status', 'purpose')

# 6. Skill Submission Admin
class SkillSubmissionAdmin(admin.ModelAdmin):
    list_display = ('student', 'skill_name', 'status', 'submitted_at')
    list_filter = ('status',)

# Register your models
admin.site.register(User, UserAdmin)
admin.site.register(StudentProfile, StudentProfileAdmin)
admin.site.register(Skill)
admin.site.register(Job, JobAdmin)
admin.site.register(Application, ApplicationAdmin)
admin.site.register(Donation)
admin.site.register(Payment, PaymentAdmin)
admin.site.register(SkillSubmission, SkillSubmissionAdmin)
admin.site.register(Event)
admin.site.register(SiteUpdate)