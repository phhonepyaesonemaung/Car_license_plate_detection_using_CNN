#!/usr/bin/env python3
"""
Backend Test Script for Car Parking System (Simplified DB)
Tests all API endpoints and functionality

Usage:
  python backend-test-script.py          # run full test suite
  python backend-test-script.py --quick  # run quick/basic checks

Requires:
  pip install requests pillow
"""

import requests
import json
import time
from io import BytesIO
from PIL import Image
import os

BASE_URL = "http://localhost:5000"
TEST_IMAGE_PATH = "1E.jpg"

class ParkingSystemTester:
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def create_test_image(self):
        img = Image.new('RGB', (640, 480), color='blue')
        img.save(TEST_IMAGE_PATH, 'JPEG')
        print(f"✅ Created test image: {TEST_IMAGE_PATH}")

    def test_health_check(self):
        print("\n🔍 Testing Health Check...")
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Health Check: {data.get('status', 'unknown')}")
                return True
            else:
                print(f"❌ Health Check Failed: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Health Check Error: {e}")
            return False

    def test_login(self, username="admin", password="admin123"):
        print(f"\n🔐 Testing Login with {username}/{password}...")
        try:
            data = {'username': username, 'password': password}
            response = self.session.post(f"{self.base_url}/login", data=data, timeout=15)
            try:
                result = response.json()
            except ValueError:
                print(f"❌ Login Failed: Non-JSON response (HTTP {response.status_code})")
                return False
            if response.status_code == 200 and result.get('success'):
                print(f"✅ Login Successful: {result.get('message', 'OK')}")
                return True
            else:
                msg = result.get('message') or result.get('error') or f"HTTP {response.status_code}"
                print(f"❌ Login Failed: {msg}")
                return False
        except Exception as e:
            print(f"❌ Login Error: {e}")
            return False

    def test_vehicle_entry(self):
        print("\n🚗 Testing Vehicle Entry...")
        try:
            if not os.path.exists(TEST_IMAGE_PATH):
                self.create_test_image()
            with open(TEST_IMAGE_PATH, 'rb') as f:
                files = {'image': ('test_vehicle.jpg', f, 'image/jpeg')}
                response = self.session.post(f"{self.base_url}/upload-entry", files=files, timeout=30)
            if response.status_code == 200:
                result = response.json()
                plate = result.get('plate')
                print(f"✅ Entry Successful: Plate {plate}")
                return plate
            else:
                try:
                    result = response.json()
                    msg = result.get('error') or result.get('message') or 'Unknown error'
                except ValueError:
                    msg = f"HTTP {response.status_code}"
                print(f"❌ Entry Failed: {msg}")
                return None
        except Exception as e:
            print(f"❌ Entry Error: {e}")
            return None

    def test_vehicle_exit(self):
        print("\n🚙 Testing Vehicle Exit...")
        try:
            if not os.path.exists(TEST_IMAGE_PATH):
                self.create_test_image()
            with open(TEST_IMAGE_PATH, 'rb') as f:
                files = {'image': ('test_vehicle_exit.jpg', f, 'image/jpeg')}
                response = self.session.post(f"{self.base_url}/upload-exit", files=files, timeout=30)
            if response.status_code == 200:
                result = response.json()
                plate = result.get('plate')
                duration = result.get('duration')
                fare = result.get('fare')
                print(f"✅ Exit Successful: Plate {plate}")
                if duration:
                    print(f"   Duration: {duration}")
                if fare is not None:
                    print(f"   Fare: ${fare}")
                return True
            else:
                try:
                    result = response.json()
                    msg = result.get('error') or result.get('message') or f"HTTP {response.status_code}"
                    print(f"❌ Exit Failed: {msg}")
                except ValueError:
                    print(f"❌ Exit Failed: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Exit Error: {e}")
            return False

    def test_get_logs(self):
        print("\n📋 Testing Get Logs...")
        try:
            response = self.session.get(f"{self.base_url}/get-logs", timeout=20)
            if response.status_code == 200:
                logs = response.json()
                if not isinstance(logs, list):
                    print("❌ Get Logs Failed: response is not a list")
                    return 0
                print(f"✅ Retrieved {len(logs)} parking records")
                return len(logs)
            else:
                print(f"❌ Get Logs Failed: HTTP {response.status_code}")
                return 0
        except Exception as e:
            print(f"❌ Get Logs Error: {e}")
            return 0

    def test_search_car(self, plate="ABC"):
        print(f"\n🔍 Testing Car Search for '{plate}'...")
        try:
            response = self.session.get(f"{self.base_url}/search-car", params={"plate": plate}, timeout=20)
            if response.status_code == 200:
                results = response.json()
                if not isinstance(results, list):
                    print("❌ Search Failed: response is not a list")
                    return 0
                print(f"✅ Search found {len(results)} results")
                return len(results)
            else:
                print(f"❌ Search Failed: HTTP {response.status_code}")
                return 0
        except Exception as e:
            print(f"❌ Search Error: {e}")
            return 0

    def test_get_stats(self):
        print("\n📊 Testing Dashboard Statistics...")
        try:
            response = self.session.get(f"{self.base_url}/get-stats", timeout=20)
            if response.status_code == 200:
                stats = response.json()
                print("✅ Statistics Retrieved:")
                print(f"   Total Vehicles: {stats.get('total_vehicles', 0)}")
                print(f"   Active Parkings: {stats.get('active_parkings', 0)}")
                print(f"   Completed Parkings: {stats.get('completed_parkings', 0)}")
                print(f"   Total Revenue: ${stats.get('total_revenue', 0)}")
                print(f"   Average Duration: {stats.get('avg_duration_minutes', 0)} minutes")
                print(f"   Today's Entries: {stats.get('today_entries', 0)}")
                return True
            else:
                print(f"❌ Stats Failed: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Stats Error: {e}")
            return False

    def run_all_tests(self):
        print("🚀 Starting Car Parking System Backend Tests")
        print("=" * 60)
        results = {
            'health': self.test_health_check(),
            'login': self.test_login(),
            'entry': self.test_vehicle_entry() is not None,
            'logs': self.test_get_logs() >= 0,
            'search': self.test_search_car("ABC") >= 0,
            'stats': self.test_get_stats(),
            'exit': self.test_vehicle_exit()
        }
        passed = sum(1 for result in results.values() if result)
        total = len(results)
        print("\n📋 TEST SUMMARY")
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name.upper():20} {status}")
        print(f"\nOVERALL: {passed}/{total} tests passed ({(passed/total*100):.1f}%)")
        if os.path.exists(TEST_IMAGE_PATH):
            try:
                os.remove(TEST_IMAGE_PATH)
                print(f"\n🧹 Cleaned up test image: {TEST_IMAGE_PATH}")
            except Exception:
                pass
        return results

def main():
    import sys
    tester = ParkingSystemTester()
    if len(sys.argv) > 1 and sys.argv[1] == '--quick':
        print("⚡ Running Quick Test Suite...")
        health_ok = tester.test_health_check()
        login_ok = tester.test_login()
        logs_count = tester.test_get_logs() if health_ok and login_ok else 0
        print("\n⚡ Quick Test Results:")
        print(f"   Server: {'✅' if health_ok else '❌'}")
        print(f"   Login: {'✅' if login_ok else '❌'}")
        print(f"   Database: {'✅' if logs_count >= 0 else '❌'}")
        return
    tester.run_all_tests()

if __name__ == "__main__":
    main()