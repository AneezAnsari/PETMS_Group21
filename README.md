# PETMS - Organizer + Real Email + Digital Ticket Version

## What is included
- Organizer model and admin organizer CRUD
- Events linked to organizers
- Real password-reset email sending via Gmail SMTP
- Digital ticket generation after booking
- Digital ticket email after booking
- My Tickets page
- Admin dashboard and event management
- SQLite by default

## Before you run
Set these PowerShell environment variables if you want real email sending:

```powershell
$env:MAIL_USERNAME="yourgmail@gmail.com"
$env:MAIL_PASSWORD="your-16-digit-app-password"
```

Optional:

```powershell
$env:SECRET_KEY="change-this"
```

## Install and run

```powershell
python -m pip install -r requirements.txt
python app.py
```

## First-time setup
Because the database schema changed, delete your old `petms.db` before running this version.

Then visit:
- `/seed-organizers`
- `/seed-events`
- `/seed-admin`

## Test admin login
- Email: `admin@petms.com`
- Password: `Admin123!`
