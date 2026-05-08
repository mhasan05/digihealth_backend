# DigiHealth Backend

Django REST Framework backend for the DigiHealth healthcare CMS.

## Requirements

- Python 3.10+
- pip

## Setup

```bash
cd /Volumes/Projects/DigiHealth/digihealth_backend

# Create virtual environment
python3 -m venv venv

# Activate
source venv/bin/activate   # macOS/Linux
# venv\Scripts\activate    # Windows

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Seed demo data
python manage.py seed_demo

# Start development server
python manage.py runserver
```

## Demo Credentials

| Role        | Phone        | Password  |
|-------------|--------------|-----------|
| Admin       | 01700000001  | demo1234  |
| Owner       | 01711111111  | demo1234  |
| Manager     | 01722000001  | demo1234  |
| Pathologist | 01733000001  | demo1234  |
| Patient     | 01799000001  | demo1234  |
| Multi-Role  | 01788000001  | demo1234  |

## API Base URL

`http://localhost:8000`

## Authentication

All protected endpoints require:
```
Authorization: Bearer <jwt-token>
```

Token is returned from `/api/auth/login/` or `/api/auth/demo-login/` as the `"token"` key.
