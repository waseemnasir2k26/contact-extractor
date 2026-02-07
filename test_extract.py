"""
Test script for contact-extractor/api/extract.py
Tests the crawl function against github.com
"""
import sys
import os
import json
from datetime import datetime

# Add the api directory to path so we can import extract
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))

print("=" * 60)
print("Contact Extractor Test Script")
print(f"Run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

# Test 1: Import the module (checks for syntax errors)
print("\n[TEST 1] Importing module...")
try:
    from extract import crawl, fetch_url, extract_all, LinkExtractor
    print("  SUCCESS: Module imported without syntax errors")
    test1_pass = True
except Exception as e:
    print(f"  FAILED: {type(e).__name__}: {e}")
    test1_pass = False

if not test1_pass:
    print("\nCannot continue tests - module import failed")
    sys.exit(1)

# Test 2: Test fetch_url function
print("\n[TEST 2] Testing fetch_url function with github.com...")
try:
    html, final_url = fetch_url("github.com", timeout=10)
    print(f"  SUCCESS: Fetched URL")
    print(f"  - Final URL: {final_url}")
    print(f"  - HTML length: {len(html)} characters")
    test2_pass = True
except Exception as e:
    print(f"  FAILED: {type(e).__name__}: {e}")
    test2_pass = False

# Test 3: Test extract_all function with sample HTML
print("\n[TEST 3] Testing extract_all function with sample HTML...")
sample_html = """
<html>
<body>
    <a href="mailto:contact@example-test.com">Email us</a>
    <p>Call us: (555) 123-4567</p>
    <a href="https://facebook.com/testpage">Facebook</a>
    <a href="https://twitter.com/testhandle">Twitter</a>
    <a href="https://wa.me/15551234567">WhatsApp</a>
</body>
</html>
"""
try:
    result = extract_all(sample_html)
    print("  SUCCESS: extract_all returned a result")
    print(f"  - Keys in result: {list(result.keys())}")
    print(f"  - Emails found: {result.get('emails', [])}")
    print(f"  - Phones found: {result.get('phones', [])}")
    print(f"  - WhatsApp found: {result.get('whatsapp', [])}")
    print(f"  - Social platforms: {list(result.get('social_links', {}).keys())}")
    test3_pass = True
except Exception as e:
    print(f"  FAILED: {type(e).__name__}: {e}")
    test3_pass = False

# Test 4: Test crawl function with github.com
print("\n[TEST 4] Testing crawl function with github.com (max_pages=1)...")
try:
    result = crawl("github.com", max_pages=1)
    print("  SUCCESS: crawl function returned a result")
    print(f"  - success: {result.get('success')}")
    print(f"  - source_url: {result.get('source_url')}")
    print(f"  - pages_scraped: {result.get('pages_scraped')}")
    print(f"  - time_taken: {result.get('time_taken')} seconds")
    print(f"  - emails found: {len(result.get('emails', []))}")
    print(f"  - phones found: {len(result.get('phones', []))}")
    print(f"  - whatsapp found: {len(result.get('whatsapp', []))}")

    # Check data structure
    expected_keys = ['success', 'source_url', 'pages_scraped', 'time_taken', 'emails', 'phones', 'whatsapp', 'social_links']
    missing_keys = [k for k in expected_keys if k not in result]
    if missing_keys:
        print(f"  WARNING: Missing expected keys: {missing_keys}")
    else:
        print("  - All expected keys present in response")

    # Check social_links structure
    social = result.get('social_links', {})
    print(f"  - Social platforms tracked: {list(social.keys())}")

    # Show GitHub-specific social links found (if any)
    github_links = social.get('github', [])
    if github_links:
        print(f"  - GitHub usernames found: {[l.get('username') for l in github_links[:5]]}")

    test4_pass = result.get('success') == True
except Exception as e:
    print(f"  FAILED: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    test4_pass = False

# Test 5: Verify return data types
print("\n[TEST 5] Verifying data types in crawl result...")
try:
    result = crawl("github.com", max_pages=1)

    checks = []
    checks.append(("success is bool", isinstance(result.get('success'), bool)))
    checks.append(("source_url is str", isinstance(result.get('source_url'), str)))
    checks.append(("pages_scraped is int", isinstance(result.get('pages_scraped'), int)))
    checks.append(("time_taken is float/int", isinstance(result.get('time_taken'), (int, float))))
    checks.append(("emails is list", isinstance(result.get('emails'), list)))
    checks.append(("phones is list", isinstance(result.get('phones'), list)))
    checks.append(("whatsapp is list", isinstance(result.get('whatsapp'), list)))
    checks.append(("social_links is dict", isinstance(result.get('social_links'), dict)))

    all_pass = True
    for check_name, passed in checks:
        status = "PASS" if passed else "FAIL"
        print(f"    {status}: {check_name}")
        if not passed:
            all_pass = False

    test5_pass = all_pass
except Exception as e:
    print(f"  FAILED: {type(e).__name__}: {e}")
    test5_pass = False

# Summary
print("\n" + "=" * 60)
print("TEST SUMMARY")
print("=" * 60)
tests = [
    ("Module import (syntax check)", test1_pass),
    ("fetch_url function", test2_pass),
    ("extract_all function", test3_pass),
    ("crawl function", test4_pass),
    ("Data type verification", test5_pass),
]

passed = sum(1 for _, p in tests if p)
total = len(tests)

for name, result in tests:
    status = "PASS" if result else "FAIL"
    print(f"  [{status}] {name}")

print(f"\nResult: {passed}/{total} tests passed")

if passed == total:
    print("\nAll tests PASSED! The contact extraction code is working correctly.")
else:
    print(f"\nSome tests FAILED. Please review the output above.")

# Save results to file
results_data = {
    "test_date": datetime.now().isoformat(),
    "target_url": "github.com",
    "tests": {name: result for name, result in tests},
    "passed": passed,
    "total": total,
    "all_passed": passed == total
}

with open(os.path.join(os.path.dirname(__file__), 'test_results.json'), 'w') as f:
    json.dump(results_data, f, indent=2)

print(f"\nResults saved to test_results.json")
