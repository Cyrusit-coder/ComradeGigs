import base64
import datetime
import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

# 1. Helper function to format phone numbers (07xx -> 2547xx)
def format_phone_number(phone):
    if phone.startswith('+'):
        phone = phone[1:]
    if phone.startswith('0'):
        phone = '254' + phone[1:]
    return phone

def get_access_token():
    # Use settings.py variables instead of os.environ for better Django integration
    consumer_key = getattr(settings, 'MPESA_CONSUMER_KEY', None)
    consumer_secret = getattr(settings, 'MPESA_CONSUMER_SECRET', None)

    if not consumer_key or not consumer_secret:
        raise ImproperlyConfigured("MPESA_CONSUMER_KEY or MPESA_CONSUMER_SECRET not set in settings.py")

    api_URL = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    
    try:
        r = requests.get(api_URL, auth=(consumer_key, consumer_secret))
        r.raise_for_status()  # Check if request failed
        return r.json()['access_token']
    except requests.exceptions.RequestException as e:
        print(f"Error generating Access Token: {e}")
        return None

def stk_push(phone_number, amount, account_reference, transaction_desc):
    token = get_access_token()
    if not token:
        return {"error": "Could not generate access token"}

    # Format the phone number correctly
    formatted_phone = format_phone_number(phone_number)
    
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    
    # Get credentials from settings.py
    business_short_code = getattr(settings, 'MPESA_SHORTCODE', None)
    passkey = getattr(settings, 'MPESA_PASSKEY', None)
    
    # Callback URL (Must be live/internet accessible, NOT localhost)
    # If you are testing locally, you need a tool like Ngrok, or use a placeholder if just testing the Push.
    callback_url = getattr(settings, 'MPESA_CALLBACK_URL', 'https://mydomain.com/callback') 

    if not business_short_code or not passkey:
        raise ImproperlyConfigured("MPESA_SHORTCODE or MPESA_PASSKEY not set in settings.py")

    # Generate password
    data_to_encode = business_short_code + passkey + timestamp
    online_password = base64.b64encode(data_to_encode.encode()).decode('utf-8')

    api_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    
    headers = {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json'
    }
    
    payload = {
        "BusinessShortCode": business_short_code,
        "Password": online_password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": formatted_phone, 
        "PartyB": business_short_code,
        "PhoneNumber": formatted_phone,
        "CallBackURL": callback_url,
        "AccountReference": account_reference,
        "TransactionDesc": transaction_desc
    }
    
    try:
        response = requests.post(api_url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"STK Push Error: {e}")
        return {"error": str(e)}