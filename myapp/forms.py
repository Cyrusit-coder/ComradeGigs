from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, StudentProfile, Job, Application, Donation, Skill

# --- STUDENT REGISTRATION FORM ---
class StudentRegisterForm(UserCreationForm):
    full_name = forms.CharField(max_length=150, help_text="Enter your First and Last name")
    university = forms.CharField(max_length=100)
    course = forms.CharField(max_length=100)
    year_of_study = forms.IntegerField()
    phone = forms.CharField(max_length=15, label="Phone Number")
    
    # FIX 1: Skills Selection
    # queryset=Skill.objects.all() loads "Web Basics", "VA", etc. from your database.
    # required=False allows the "No Skill" option (leaving it blank).
    skills = forms.ModelMultipleChoiceField(
        queryset=Skill.objects.all(),
        widget=forms.CheckboxSelectMultiple, 
        required=False,
        label="Select Your Skills",
        help_text="Select the skills you have. Leave blank if you have none yet."
    )

    class Meta(UserCreationForm.Meta):
        model = User
        # We include 'email' and the extra fields defined above
        fields = UserCreationForm.Meta.fields + ('email', 'full_name', 'phone')

    def save(self, commit=True):
        # 1. Create the User instance (but don't save to DB yet)
        user = super().save(commit=False)
        user.role = 'student'
        user.phone_number = self.cleaned_data['phone']
        
        # Optional: Save full_name to first_name for the dashboard greeting
        if 'full_name' in self.cleaned_data:
            user.first_name = self.cleaned_data['full_name']
        
        if commit:
            # 2. Save User to DB
            user.save()
            
            # 3. Create Student Profile (WITHOUT skills initially)
            # This prevents the "Direct assignment" TypeError
            profile = StudentProfile.objects.create(
                user=user,
                university=self.cleaned_data['university'],
                course=self.cleaned_data['course'],
                year_of_study=self.cleaned_data['year_of_study'],
            )
            
            # 4. Add Skills safely using .set()
            # This works for the Many-to-Many relationship
            skills_data = self.cleaned_data.get('skills')
            if skills_data:
                profile.skills.set(skills_data)
                
        return user

# --- OTHER FORMS (Unchanged) ---

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

class DonationForm(forms.ModelForm):
    class Meta:
        model = Donation
        fields = ['amount', 'message']