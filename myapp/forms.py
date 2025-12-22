from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, StudentProfile, Job, Application, Donation, Skill, Event, SiteUpdate

# 1. Student Registration Form
class StudentRegisterForm(UserCreationForm):
    full_name = forms.CharField(max_length=150, help_text="Enter your First and Last name")
    university = forms.CharField(max_length=100)
    course = forms.CharField(max_length=100)
    year_of_study = forms.IntegerField()
    phone = forms.CharField(max_length=15, label="Phone Number")
    
    # Skills Selection
    skills = forms.ModelMultipleChoiceField(
        queryset=Skill.objects.all(),
        widget=forms.CheckboxSelectMultiple, 
        required=False,
        label="Select Your Skills",
        help_text="Select the skills you have. Leave blank if you have none yet."
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email', 'full_name', 'phone')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'student'
        user.phone_number = self.cleaned_data['phone']
        
        if 'full_name' in self.cleaned_data:
            user.first_name = self.cleaned_data['full_name']
        
        if commit:
            user.save()
            
            # Create Profile
            profile = StudentProfile.objects.create(
                user=user,
                university=self.cleaned_data['university'],
                course=self.cleaned_data['course'],
                year_of_study=self.cleaned_data['year_of_study'],
            )
            
            # Add Skills safely
            skills_data = self.cleaned_data.get('skills')
            if skills_data:
                profile.skills.set(skills_data)
                
        return user

# 2. Client Registration Form
class ClientRegisterForm(UserCreationForm):
    email = forms.EmailField()
    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email',)
    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'client'
        if commit:
            user.save()
        return user

# 3. Donor Registration Form
class DonorRegisterForm(UserCreationForm):
    email = forms.EmailField()
    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email',)
    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'donor'
        if commit:
            user.save()
        return user

# 4. Job Posting Form
class JobForm(forms.ModelForm):
    required_skills = forms.ModelMultipleChoiceField(
        queryset=Skill.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    class Meta:
        model = Job
        fields = ['title', 'budget', 'deadline', 'description', 'required_skills']
        widgets = {
            'deadline': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'budget': forms.NumberInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        }

# 5. Student Profile Edit Form
class StudentProfileForm(forms.ModelForm):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    phone_number = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    skills = forms.ModelMultipleChoiceField(
        queryset=Skill.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    class Meta:
        model = StudentProfile
        fields = ['university', 'course', 'year_of_study', 'skills', 'exam_mode']
        widgets = {
            'university': forms.TextInput(attrs={'class': 'form-control'}),
            'course': forms.TextInput(attrs={'class': 'form-control'}),
            'year_of_study': forms.NumberInput(attrs={'class': 'form-control'}),
            'exam_mode': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

# 6. Donation Form
class DonationForm(forms.ModelForm):
    class Meta:
        model = Donation
        fields = ['amount', 'message']

# 7. Event Creation Form (Admin)
class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['title', 'description', 'date', 'location', 'image']
        widgets = {
            'date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
        }

# 8. Job Application Form
class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        # proposal = text area, cv & cover_letter_file = file uploads
        fields = ['proposal', 'bid_amount', 'cv', 'cover_letter_file'] 
        widgets = {
            'proposal': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Write a short pitch...'}),
            'bid_amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Optional'}),
            'cv': forms.FileInput(attrs={'class': 'form-control'}),
            'cover_letter_file': forms.FileInput(attrs={'class': 'form-control'}),
        }

# 9. Site Announcement Form (Admin) - UPDATED
class SiteUpdateForm(forms.ModelForm):
    class Meta:
        model = SiteUpdate
        fields = ['title', 'audience', 'message', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Scheduled Maintenance'}),
            'audience': forms.Select(attrs={'class': 'form-select'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Enter your announcement details...'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

# 10. Student ID Upload Form (NEW)
class StudentIDUploadForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = ['school_id_image']
        widgets = {
            'school_id_image': forms.FileInput(attrs={'class': 'form-control form-control-lg', 'accept': 'image/*'}),
        }

# --- ADMIN PROFILE FORM ---
class AdminProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'profile_image']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control rounded-pill', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control rounded-pill', 'placeholder': 'Last Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control rounded-pill', 'placeholder': 'Official Email'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control rounded-pill', 'placeholder': 'WhatsApp Number'}),
            'profile_image': forms.FileInput(attrs={'class': 'form-control rounded-pill'}),
        }