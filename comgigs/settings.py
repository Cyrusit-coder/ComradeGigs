"""
Django settings for comgigs project.
"""

from pathlib import Path
from dotenv import load_dotenv
import dj_database_url
import os

# 1. Load Environment Variables (CRITICAL for .env files)
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
# Try to get it from environment, fall back to insecure one for dev
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-t257&6zk)05-4i!=p(s=6z522ms%az6d)tl5uer06fx-=zwz5y')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True 

ALLOWED_HOSTS = [
    'localhost', 
    '127.0.0.1', 
    'comradegigs.onrender.com',
    '*' # Allow Ngrok access
]

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',       # Required by allauth
    
    # Third Party Apps
    'myapp',
    'cloudinary_storage',  
    'cloudinary',
    
    # 2FA Apps
    'django_otp',
    'django_otp.plugins.otp_totp',

    # Allauth (Google Login)
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google', 
]

SITE_ID = 1

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Keep near top
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    
    # --- REQUIRED FOR 2FA & GOOGLE LOGIN ---
    'django_otp.middleware.OTPMiddleware',           # For 2FA
    'allauth.account.middleware.AccountMiddleware',  # For Google Login
    # ---------------------------------------

    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'comgigs.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [], # Add dirs here if you have global templates
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'myapp.context_processors.global_site_updates',
            ],
        },
    },
]

WSGI_APPLICATION = 'comgigs.wsgi.application'

# Database Configuration
if 'DATABASE_URL' in os.environ:
    # Production (Render)
    DATABASES = {
        'default': dj_database_url.config(
            conn_max_age=600,
            ssl_require=True
        )
    }
else:
    # Localhost (SQLite)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Authentication URLs
LOGIN_URL = 'myapp:login'  
LOGIN_REDIRECT_URL = 'myapp:social_auth_dispatch' 
LOGOUT_REDIRECT_URL = 'myapp:home'
AUTH_USER_MODEL = 'myapp.User' 

# --- STATIC & MEDIA FILES (Fixed & Cleaned) ---
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'myapp/static')]

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Cloudinary & Storage Config
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.environ.get('CLOUDINARY_CLOUD_NAME'),
    'API_KEY': os.environ.get('CLOUDINARY_API_KEY'),
    'API_SECRET': os.environ.get('CLOUDINARY_API_SECRET'),
}

# New Django Storage Configuration (Replaces deprecated settings)
STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Email Configuration
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend' # Use for testing (prints to console)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend' # Use for real emails

EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'cyrusnjeri04@gmail.com'
EMAIL_HOST_PASSWORD = 'ryud gkda ovhu dznl' 
DEFAULT_FROM_EMAIL = 'cyrusnjeri04@gmail.com'

# --- M-PESA CONFIGURATION (Smart Switch) ---
MPESA_CONSUMER_KEY = os.getenv("MPESA_CONSUMER_KEY")
MPESA_CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET")
MPESA_SHORTCODE = os.getenv("MPESA_SHORTCODE")
MPESA_PASSKEY = os.getenv("MPESA_PASSKEY")

# Automatically switch between Render and Localhost (Ngrok)
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')

if RENDER_EXTERNAL_HOSTNAME:
    # WE ARE ON RENDER (Production)
    MPESA_CALLBACK_URL = f'https://{RENDER_EXTERNAL_HOSTNAME}'
else:
    # WE ARE ON LOCALHOST (Use Ngrok)
    # REPLACE THIS with your current Ngrok URL every time you restart Ngrok
    MPESA_CALLBACK_URL = '  https://anthropolatric-elena-nonmonogamously.ngrok-free.dev' 

CALLBACK_URL = MPESA_CALLBACK_URL # Alias for safety

# --- AUTHENTICATION BACKENDS ---
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend', # Standard login
    'allauth.account.auth_backends.AuthenticationBackend', # Google login
]

# --- GOOGLE AUTH SETTINGS (Django-Allauth) ---
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
        'APP': {
    'client_id': os.getenv('GOOGLE_CLIENT_ID'),     # Loaded from .env
    'secret': os.getenv('GOOGLE_CLIENT_SECRET'),    # Loaded from .env
    'key': ''
}
        }
    }


# --- ALLAUTH CONFIGURATION (Updated) ---
# Specifies that users log in with their email address
ACCOUNT_LOGIN_METHODS = {'email'}

# Defines the fields required during signup ('*' means required)
ACCOUNT_SIGNUP_FIELDS = [
    'email*',       # Email is required
    'password1*',   # Password is required
    'password2*',   # Password confirmation is required
]

ACCOUNT_EMAIL_VERIFICATION = 'none'  # Options: "mandatory", "optional", "none"