# ComradeGigs 🎓💼

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Django](https://img.shields.io/badge/Django-4.x-092E20)
![License](https://img.shields.io/badge/license-MIT-green)

**ComradeGigs** is a freelance marketplace and support platform tailored for university students ("Comrades"). It bridges the gap between students seeking income through gigs and clients looking for affordable talent. Additionally, it features a donation system ("The Alliance") to support students in need.

---

## 🚀 Features

### 👨‍🎓 For Students
* **Profile Verification:** Secure identity verification via University ID uploads.
* **Skill Badges:** Automated and manual assessments to verify skills (Graphics, Web Dev, Writing).
* **Gig Marketplace:** Browse and apply for jobs with proposals and CV uploads.
* **Earnings Dashboard:** Track active jobs, completed gigs, and total income.

### 🏢 For Clients
* **Job Management:** Post, edit, and delete gigs.
* **Applicant Tracking:** Review proposals, download CVs/Cover letters, and hire candidates.
* **Direct Payment:** Integrated **M-Pesa STK Push** for seamless payments to students.
* **Communication:** Direct WhatsApp and Email links to short-listed candidates.

### ❤️ For Donors
* **Impact Tracking:** View total contributions and number of students supported.
* **Transparency:** Real-time history of all donations made.

### 🛡️ Admin & System
* **Dashboard:** Comprehensive analytics on users, gigs, and finances.
* **Content Moderation:** Verify gigs and approve student IDs/skills.
* **Broadcast System:** Send targeted dismissible notifications to specific user groups (Students, Clients, Donors).

---

## 🛠️ Tech Stack

* **Backend:** Django (Python)
* **Database:** PostgreSQL (Production via Render), SQLite (Development)
* **Frontend:** Bootstrap 5, JavaScript (Custom notification logic), Django Templates
* **Payments:** Daraja API (M-Pesa Integration)
* **Storage:** Cloudinary (Media/Static files persistence)
* **Hosting:** Render (Web Service)

---

## ⚙️ Installation & Local Development

Follow these steps to get the project running on your local machine.

### 1. Clone the Repository
```bash
git clone [https://github.com/yourusername/comradegigs.git](https://github.com/yourusername/comradegigs.git)
cd comradegigs
2. Create Virtual Environment
Bash

# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
3. Install Dependencies
Bash

pip install -r requirements.txt
4. Configure Environment Variables
Create a .env file in the root directory and add the following keys:

Code snippet

SECRET_KEY=your_secret_key_here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Cloudinary (For Media)
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret

# M-Pesa (Daraja API)
MPESA_CONSUMER_KEY=your_key
MPESA_CONSUMER_SECRET=your_secret
MPESA_PASSKEY=your_passkey
MPESA_CALLBACK_URL=[https://your-domain.com/mpesa/confirmation/](https://your-domain.com/mpesa/confirmation/)
5. Run Migrations
Bash

python manage.py makemigrations
python manage.py migrate
6. Create Superuser (Admin)
Bash

python manage.py createsuperuser
7. Run Server
Bash

python manage.py runserver
Visit http://127.0.0.1:8000/ in your browser.

📦 Deployment (Render)
This project is configured for deployment on Render.

Build Command: ./build.sh

Start Command: gunicorn comradegigs.wsgi:application

Environment: Ensure PYTHON_VERSION is set to 3.9.0 (or matching your local version).

Note: Persistent storage for media files is handled via Cloudinary settings in settings.py.

🤝 Contributing
Contributions are welcome! Please follow these steps:

Fork the repository.

Create a feature branch (git checkout -b feature/AmazingFeature).

Commit your changes (git commit -m 'Add some AmazingFeature').

Push to the branch (git push origin feature/AmazingFeature).

Open a Pull Request.

📄 License
Distributed under the MIT License. See LICENSE for more information.

📞 Contact
Your Name - cyrusnjeri04@gmail|https://www.linkedin.com/in/cyrus-njeri-15896936b/ Project Link: https://github.com/Cyrusit-coder/ComradeGigs