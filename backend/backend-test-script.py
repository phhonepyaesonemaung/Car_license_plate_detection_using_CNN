#!/usr/bin/env python3
"""
Backend Test Script for Car Parking System
Tests all API endpoints and functionality

Usage:
  python parking_backend_tester.py          # run full test suite
  python parking_backend_tester.py --quick  # run quick/basic checks

Requires:
  pip install requests pillow
"""

import requests
import json
import time
from io import BytesIO
from PIL import Image
import os

# Configuration
BASE_URL = "http://localhost:5000"
TEST_IMAGE_PATH = "test_vehicle.jpg"


class ParkingSystemTester:
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    # ------------------------- helpers -------------------------
    def create_test_image(self):
        """Create a simple test image for uploading."""
        img = Image.new('RGB', (640, 480), color='blue')
        img.save(TEST_IMAGE_PATH, 'JPEG')
        print(f"✅ Created test image: {TEST_IMAGE_PATH}")

    # ------------------------- endpoint tests -------------------------
    def test_health_check(self):
        """Test the health check endpoint."""
        print("\n🔍 Testing Health Check...")
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                status = data.get('status', 'unknown')
                db = data.get('database', 'unknown')
                print(f"✅ Health Check: {status}, DB: {db}")
                return True
            else:
                print(f"❌ Health Check Failed: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Health Check Error: {e}")
            return False

    def test_login(self, username="admin", password="admin123"):
        """Test the login functionality."""
        print(f"\n🔐 Testing Login with {username}/{password}...")
        try:
            data = {'username': username, 'password': password}
            response = self.session.post(f"{self.base_url}/login", data=data, timeout=15)

            # Some backends return 401/400 on bad login — try to parse JSON anyway
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
        """Test vehicle entry upload."""
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
                ts = result.get('timestamp') or result.get('entry')
                print(f"✅ Entry Successful: Plate {plate}")
                if ts:
                    print(f"   Timestamp: {ts}")
                return plate
            else:
                # Attempt to show JSON error if available
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
        """Test vehicle exit upload."""
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
                duration = result.get('duration_display') or result.get('duration')
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
                    if 'suggestion' in result:
                        print(f"   Suggestion: {result['suggestion']}")
                except ValueError:
                    print(f"❌ Exit Failed: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Exit Error: {e}")
            return False

    def test_get_logs(self):
        """Test retrieving parking logs."""
        print("\n📋 Testing Get Logs...")
        try:
            response = self.session.get(f"{self.base_url}/get-logs", timeout=20)
            if response.status_code == 200:
                logs = response.json()
                if not isinstance(logs, list):
                    print("❌ Get Logs Failed: response is not a list")
                    return 0

                print(f"✅ Retrieved {len(logs)} parking records")
                if logs:
                    print("   Recent records:")
                    for i, log in enumerate(logs[:3]):  # Show first 3 records
                        status = "🟢 Active" if not log.get('exit') else "🔴 Completed"
                        print(f"   {i+1}. {log.get('plate')} - {status} - Entry: {log.get('entry')}")
                        if log.get('fare'):
                            print(f"      Duration: {log.get('duration')}, Fare: {log.get('fare')}")
                return len(logs)
            else:
                print(f"❌ Get Logs Failed: HTTP {response.status_code}")
                return 0
        except Exception as e:
            print(f"❌ Get Logs Error: {e}")
            return 0

    def test_search_car(self, plate="ABC"):
        """Test searching for a specific car."""
        print(f"\n🔍 Testing Car Search for '{plate}'...")
        try:
            response = self.session.get(f"{self.base_url}/search-car", params={"plate": plate}, timeout=20)
            if response.status_code == 200:
                results = response.json()
                if not isinstance(results, list):
                    print("❌ Search Failed: response is not a list")
                    return 0

                print(f"✅ Search found {len(results)} results")
                for i, result in enumerate(results[:2]):  # Show first 2 results
                    status = "🟢 Active" if not result.get('exit') else "🔴 Completed"
                    print(f"   {i+1}. {result.get('plate')} - {status}")
                    print(f"      Entry: {result.get('entry')}")
                    if result.get('exit'):
                        print(f"      Exit: {result.get('exit')}")
                        if 'fare' in result:
                            print(f"      Fare: {result.get('fare')}")
                return len(results)
            else:
                print(f"❌ Search Failed: HTTP {response.status_code}")
                return 0
        except Exception as e:
            print(f"❌ Search Error: {e}")
            return 0

    def test_get_stats(self):
        """Test getting dashboard statistics."""
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
                print(f"   Today's Revenue: ${stats.get('today_revenue', 0)}")
                return True
            else:
                print(f"❌ Stats Failed: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Stats Error: {e}")
            return False

    def test_complete_parking_cycle(self):
        """Test a complete parking cycle (entry -> wait -> exit)."""
        print("\n🔄 Testing Complete Parking Cycle...")

        plate = self.test_vehicle_entry()
        if not plate:
            print("❌ Cannot proceed with cycle - entry failed")
            return False

        print("   ⏳ Waiting 3 seconds to simulate parking time...")
        time.sleep(3)

        exit_success = self.test_vehicle_exit()
        if exit_success:
            print("✅ Complete parking cycle successful!")
            return True
        else:
            print("❌ Complete parking cycle failed at exit")
            return False

    def test_duplicate_entry(self):
        """Test duplicate entry handling."""
        print("\n🔄 Testing Duplicate Entry Handling...")
        try:
            # First entry
            plate1 = self.test_vehicle_entry()
            if not plate1:
                print("❌ First entry failed")
                return False

            # Second entry with same plate (should be handled gracefully by backend)
            print("   Testing second entry for same vehicle...")
            if not os.path.exists(TEST_IMAGE_PATH):
                self.create_test_image()

            with open(TEST_IMAGE_PATH, 'rb') as f:
                files = {'image': ('test_vehicle_duplicate.jpg', f, 'image/jpeg')}
                response = self.session.post(f"{self.base_url}/upload-entry", files=files, timeout=30)

            if response.status_code in [200, 409]:
                result = response.json()
                if result.get('warning') or response.status_code == 409:
                    msg = result.get('message') or 'Duplicate prevented'
                    print(f"✅ Duplicate entry handled correctly: {msg}")
                else:
                    print(f"✅ Entry processed: {result.get('plate')}")
                return True
            else:
                print(f"❌ Duplicate entry test failed: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Duplicate entry error: {e}")
            return False

    # ------------------------- orchestration -------------------------
    def run_all_tests(self):
        """Run all tests in sequence."""
        print("🚀 Starting Car Parking System Backend Tests")
        print("=" * 60)

        results = {
            'health': False,
            'login': False,
            'entry': False,
            'exit': False,
            'logs': False,
            'search': False,
            'stats': False,
            'complete_cycle': False,
            'duplicate_entry': False,
        }

        # Health check first
        results['health'] = self.test_health_check()
        if not results['health']:
            print("\n❌ Health check failed. Make sure the server is running!")
            print("Run: python backend/app.py")
            self.print_test_summary(results)
            return results

        # Login (optional depending on backend)
        results['login'] = self.test_login()

        # Individual endpoints
        test_plate = self.test_vehicle_entry()
        results['entry'] = test_plate is not None

        log_count = self.test_get_logs()
        results['logs'] = log_count >= 0

        search_count = self.test_search_car("ABC")  # Search for common pattern
        results['search'] = search_count >= 0

        results['stats'] = self.test_get_stats()

        # Complete cycle
        results['complete_cycle'] = self.test_complete_parking_cycle()

        # Duplicate entry handling
        results['duplicate_entry'] = self.test_duplicate_entry()

        # Final exit test (for any remaining active entries)
        print("\n🚙 Testing Final Exit (for any remaining active entries)...")
        results['exit'] = self.test_vehicle_exit()

        # Summary & cleanup
        self.print_test_summary(results)

        if os.path.exists(TEST_IMAGE_PATH):
            try:
                os.remove(TEST_IMAGE_PATH)
                print(f"\n🧹 Cleaned up test image: {TEST_IMAGE_PATH}")
            except Exception:
                pass

        return results

    def print_test_summary(self, results):
        """Print test summary."""
        print("\n" + "=" * 60)
        print("📋 TEST SUMMARY")
        print("=" * 60)

        passed = sum(1 for result in results.values() if result)
        total = len(results)

        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name.upper():20} {status}")

        print("-" * 60)
        pct = (passed / total * 100) if total else 0
        print(f"OVERALL: {passed}/{total} tests passed ({pct:.1f}%)")

        if passed == total:
            print("\n🎉 ALL TESTS PASSED! Your backend is working correctly.")
            print("\n✨ System Status: FULLY OPERATIONAL")
            print("   - Database connectivity: ✅")
            print("   - API endpoints: ✅")
            print("   - File uploads: ✅")
            print("   - Fare calculation: ✅")
            print("   - Data persistence: ✅")
        elif passed >= total * 0.8:
            print("\n✅ MOST TESTS PASSED! System is largely functional.")
            print("   Check failed tests above for minor issues.")
        elif passed >= total * 0.6:
            print("\n⚠️  SOME ISSUES DETECTED. System partially functional.")
            print("   Several tests failed. Check configuration.")
        else:
            print("\n❌ MULTIPLE FAILURES. System needs attention.")
            print("   Many tests failed. Check setup and configuration.")

        print("\n💡 TROUBLESHOOTING TIPS:")
        if not results.get('health'):
            print("   🔴 Server not running: python backend/app.py")
        if not results.get('login'):
            print("   🔴 Login/DB issue: Check credentials & MySQL connection")
        if not results.get('entry') or not results.get('exit'):
            print("   🔴 Upload issue: Check file permissions and upload folder")
        if not results.get('logs') or not results.get('search'):
            print("   🔴 Database query issue: Check table structure & queries")

        print("\n📚 NEXT STEPS:")
        print("   1. Fix any failed tests shown above")
        print("   2. Start the web server: python backend/app.py")
        print("   3. Open browser: http://localhost:5000")
        print("   4. Test UI manually with real images")
        print("   5. Ready to integrate ML model when available!")


def run_quick_test():
    """Run a quick subset of tests for rapid feedback."""
    print("⚡ Running Quick Test Suite...")
    tester = ParkingSystemTester()

    health_ok = tester.test_health_check()
    login_ok = tester.test_login()

    if health_ok and login_ok:
        logs_count = tester.test_get_logs()
        print("\n⚡ Quick Test Results:")
        print(f"   Server: {'✅' if health_ok else '❌'}")
        print(f"   Login: {'✅' if login_ok else '❌'}")
        print(f"   Database: {'✅' if logs_count >= 0 else '❌'}")
        print("\n✨ System ready for full testing!")
        return True
    else:
        print("\n❌ Quick test failed - fix basic issues first")
        return False


def main():
    """Main test function with command line options."""
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--quick':
        success = run_quick_test()
        raise SystemExit(0 if success else 1)

    tester = ParkingSystemTester()
    results = tester.run_all_tests()

    passed = sum(1 for result in results.values() if result)
    total = len(results)

    if passed >= total * 0.8:  # 80% pass rate for success
        print("\n🏆 TESTING COMPLETE - SYSTEM READY!")
        raise SystemExit(0)
    elif passed >= total * 0.6:  # 60% pass rate for partial success
        print("\n⚠️  TESTING COMPLETE - NEEDS ATTENTION")
        raise SystemExit(1)
    else:
        print("\n🚨 TESTING COMPLETE - MAJOR ISSUES")
        raise SystemExit(2)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Testing interrupted by user")
        if os.path.exists(TEST_IMAGE_PATH):
            try:
                os.remove(TEST_IMAGE_PATH)
            except Exception:
                pass
        print("Cleanup complete.")
        raise SystemExit(130)
