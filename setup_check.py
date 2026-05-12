#!/usr/bin/env python
"""
Setup validation script for MindConnect.
Run this to verify your Phase 1 installation is complete.
"""
import os
import sys
from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent

def check_file_exists(filepath, description):
    """Check if a file exists"""
    exists = Path(filepath).exists()
    status = "[OK]" if exists else "[MISSING]"
    print(f"  {status} {description}: {filepath}")
    return exists

def check_env_vars():
    """Check required environment variables"""
    required_vars = [
        'SECRET_KEY',
        'DATABASE_URL',
        'REDIS_URL',
        'JWT_SECRET',
        'SUPABASE_URL',
    ]

    optional_vars = [
        'SUPABASE_ANON_KEY',
        'SUPABASE_SERVICE_KEY',
    ]

    print("\n2. Environment Variables:")
    all_present = True
    for var in required_vars:
        try:
            value = config(var)
            status = "[OK]"
            print(f"  {status} {var}: Set")
        except:
            status = "[MISSING]"
            print(f"  {status} {var}: MISSING")
            all_present = False

    print("\n   Optional variables:")
    for var in optional_vars:
        try:
            value = config(var)
            status = "[OK]"
            print(f"  {status} {var}: Set")
        except:
            status = "[OPTIONAL]"
            print(f"  {status} {var}: Not set (optional for dev)")

    return all_present

def check_python_packages():
    """Check if required packages are installed"""
    print("\n3. Python Packages:")
    required_packages = [
        'django',
        'channels',
        'rest_framework',
        'rest_framework_simplejwt',
        'redis',
        'psycopg2',
    ]

    all_installed = True
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"  [OK] {package}")
        except ImportError:
            print(f"  [MISSING] {package} - NOT INSTALLED")
            all_installed = False
    return all_installed

def run_checks():
    print("=" * 60)
    print("MindConnect Phase 1 Setup Validation")
    print("=" * 60)

    results = []

    # 1. Check files
    print("\n1. Project Structure:")
    files_to_check = [
        ('.env', 'Environment file'),
        ('requirements.txt', 'Requirements file'),
        ('backend/settings.py', 'Django settings'),
        ('users/models.py', 'User model'),
        ('chat/models.py', 'Chat models'),
        ('notifications/models.py', 'Notification model'),
        ('users/serializers.py', 'User serializers'),
        ('chat/serializers.py', 'Chat serializers'),
        ('users/views.py', 'User views'),
        ('chat/views.py', 'Chat views'),
        ('chat/consumers.py', 'Chat WebSocket consumer'),
        ('backend/asgi.py', 'ASGI config'),
        ('backend/urls.py', 'URL configuration'),
    ]

    for filepath, description in files_to_check:
        exists = check_file_exists(filepath, description)
        results.append(exists)

    # 2. Check environment variables
    env_ok = check_env_vars()
    results.append(env_ok)

    # 3. Check Python packages
    packages_ok = check_python_packages()
    results.append(packages_ok)

    # Summary
    print("\n" + "=" * 60)
    if all(results):
        print("[SUCCESS] All checks passed! Phase 1 is complete.")
        print("\nNext steps:")
        print("1. Update .env with your Supabase credentials")
        print("2. Run: python manage.py makemigrations users chat notifications")
        print("3. Run: python manage.py migrate")
        print("4. Run: python manage.py createsuperuser")
        print("5. Start Redis: docker run -p 6379:6379 redis:7-alpine")
        print("6. Run server: python manage.py runserver")
        return 0
    else:
        print("[ERROR] Some checks failed. Please review the errors above.")
        return 1

if __name__ == '__main__':
    sys.exit(run_checks())
