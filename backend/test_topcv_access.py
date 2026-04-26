#!/usr/bin/env python3
"""
Quick test script to check if TopCV blocks the current IP
Run this on production server to test access
"""

import sys
import os

# Fix encoding for Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from curl_cffi import requests
import json

def test_topcv_access():
    print("=" * 80)
    print("Testing TopCV Access from Current IP")
    print("=" * 80)
    
    # Test 1: Check current IP location
    print("\n[TEST 1] Checking current IP location...")
    try:
        ip_resp = requests.get("https://ipapi.co/json/", timeout=10)
        if ip_resp.status_code == 200:
            ip_data = ip_resp.json()
            print(f"[OK] Current IP: {ip_data.get('ip')}")
            print(f"[OK] Location: {ip_data.get('city')}, {ip_data.get('country_name')}")
            print(f"[OK] ISP: {ip_data.get('org')}")
        else:
            print(f"[FAIL] Failed to get IP info: {ip_resp.status_code}")
    except Exception as e:
        print(f"[FAIL] Error checking IP: {e}")
    
    # Test 2: Access TopCV homepage
    print("\n[TEST 2] Accessing TopCV homepage...")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        
        home_resp = requests.get("https://www.topcv.vn/", headers=headers, timeout=15, impersonate="chrome120")
        print(f"[OK] Status Code: {home_resp.status_code}")
        print(f"[OK] Response Length: {len(home_resp.text)} chars")
        
        # Check for blocking indicators
        if home_resp.status_code == 403:
            print("[FAIL] BLOCKED: 403 Forbidden - IP might be blocked")
        elif home_resp.status_code == 429:
            print("[FAIL] RATE LIMITED: 429 Too Many Requests")
        elif "captcha" in home_resp.text.lower():
            print("[FAIL] CAPTCHA DETECTED: Site requires captcha verification")
        elif "access denied" in home_resp.text.lower():
            print("[FAIL] ACCESS DENIED: Site explicitly denying access")
        elif home_resp.status_code == 200:
            print("[OK] Homepage accessible - No obvious blocking")
        else:
            print(f"[WARN] Unusual status code: {home_resp.status_code}")
            
    except Exception as e:
        print(f"[FAIL] Error accessing homepage: {e}")
    
    # Test 3: Access specific job posting
    print("\n[TEST 3] Accessing specific job posting...")
    test_url = "https://www.topcv.vn/viec-lam/fullstack-developer-java-springboot-javascript/2139018.html"
    try:
        job_resp = requests.get(test_url, headers=headers, timeout=15, impersonate="chrome120")
        print(f"[OK] Status Code: {job_resp.status_code}")
        print(f"[OK] Response Length: {len(job_resp.text)} chars")
        
        if job_resp.status_code == 403:
            print("[FAIL] BLOCKED: 403 Forbidden")
        elif job_resp.status_code == 404:
            print("[WARN] Job not found (might be expired)")
        elif job_resp.status_code == 429:
            print("[FAIL] RATE LIMITED: 429 Too Many Requests")
        elif "captcha" in job_resp.text.lower():
            print("[FAIL] CAPTCHA DETECTED")
        elif job_resp.status_code == 200:
            # Check if we got actual content
            if "job-description" in job_resp.text:
                print("[OK] Job page accessible with content - No blocking detected")
            else:
                print("[WARN] Got 200 but content might be incomplete")
                print(f"  First 500 chars: {job_resp.text[:500]}")
        else:
            print(f"[WARN] Unusual status code: {job_resp.status_code}")
            
    except Exception as e:
        print(f"[FAIL] Error accessing job page: {e}")
    
    # Test 4: Check response headers for blocking indicators
    print("\n[TEST 4] Checking response headers...")
    try:
        if 'job_resp' in locals():
            print("Response headers:")
            for key, value in job_resp.headers.items():
                if key.lower() in ['server', 'cf-ray', 'x-frame-options', 'x-content-type-options']:
                    print(f"  {key}: {value}")
    except Exception as e:
        print(f"[FAIL] Error checking headers: {e}")
    
    print("\n" + "=" * 80)
    print("Test Complete!")
    print("=" * 80)

if __name__ == "__main__":
    test_topcv_access()
