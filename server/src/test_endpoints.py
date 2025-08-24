#!/usr/bin/env python3
"""
Simple test script for ETO email endpoints
"""

import requests
import json
import time

BASE_URL = "http://localhost:8080"

def test_health():
    """Test the health endpoint"""
    print("Testing health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_email_status():
    """Test the email status endpoint"""
    print("\nTesting email status endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/api/email/status")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_start_email(email_address):
    """Test starting email monitoring"""
    print(f"\nTesting start email monitoring for: {email_address}")
    try:
        data = {"email_address": email_address}
        response = requests.post(f"{BASE_URL}/api/email/start", json=data)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_stop_email():
    """Test stopping email monitoring"""
    print("\nTesting stop email monitoring...")
    try:
        response = requests.post(f"{BASE_URL}/api/email/stop")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_recent_emails(limit=5):
    """Test getting recent emails"""
    print(f"\nTesting recent emails (limit: {limit})...")
    try:
        response = requests.get(f"{BASE_URL}/api/email/recent?limit={limit}")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    """Run all tests"""
    print("ETO Email Endpoint Tests")
    print("=" * 40)
    
    # Test health first
    if not test_health():
        print("Health check failed. Is the server running?")
        return
    
    # Test email status (should be disconnected initially)
    test_email_status()
    
    # Test recent emails (should work even when disconnected)
    test_recent_emails()
    
    # Ask for email address to test with
    email_address = input("\nEnter email address to test with (or press Enter to skip): ").strip()
    
    if email_address:
        # Test starting email monitoring
        if test_start_email(email_address):
            print("\nWaiting 5 seconds...")
            time.sleep(5)
            
            # Test status again (should be connected now)
            test_email_status()
            
            # Test recent emails again
            test_recent_emails()
            
            # Test stopping email monitoring
            test_stop_email()
            
            # Test status one more time (should be disconnected)
            test_email_status()
    
    print("\nTests completed!")

if __name__ == "__main__":
    main() 