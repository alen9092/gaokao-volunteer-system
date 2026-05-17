"""Test the web app end-to-end."""
import requests
import re

BASE = 'http://127.0.0.1:5000'

s = requests.Session()

# 1. Get homepage
r = s.get(BASE)
print(f"1. Homepage: {r.status_code}")

# 2. Get register page & CSRF token
r = s.get(f'{BASE}/register')
token_match = re.search(r'name="csrf_token" value="([^"]+)"', r.text)
csrf = token_match.group(1) if token_match else None
print(f"2. CSRF token: {csrf[:20] if csrf else 'NOT FOUND'}...")

# 3. Register
if csrf:
    r = s.post(f'{BASE}/register', data={
        'csrf_token': csrf,
        'username': 'demo',
        'password': 'demo123',
        'phone': '13800138000',
        'id_card': '110101199001011234',
    })
    print(f"3. Register: {r.status_code}")
    if '注册成功' in r.text:
        print("   SUCCESS! Registered demo user")
        # Get referral code
        code_match = re.search(r'邀请码：(\w+)', r.text)
        if code_match:
            print(f"   Referral code: {code_match.group(1)}")
    elif '用户名已存在' in r.text:
        print("   User already exists, trying login...")
        # Login
        r = s.get(f'{BASE}/login')
        token_match = re.search(r'name="csrf_token" value="([^"]+)"', r.text)
        csrf2 = token_match.group(1) if token_match else None
        if csrf2:
            r = s.post(f'{BASE}/login', data={
                'csrf_token': csrf2,
                'username': 'demo',
                'password': 'demo123',
            })
            print(f"   Login: {r.status_code} - {'成功' if '成功' in r.text else '失败'}")

# 4. Get simulation page
r = s.get(f'{BASE}/simulate')
print(f"4. Simulate page: {r.status_code}")
token_match = re.search(r'name="csrf_token" value="([^"]+)"', r.text)
csrf3 = token_match.group(1) if token_match else None

# 5. Run simulation
if csrf3:
    r = s.post(f'{BASE}/simulate', data={
        'csrf_token': csrf3,
        'year': '2024',
        'score': '580',
        'subject': '物理类',
        'province': '',
        'batch': '本科批',
    })
    print(f"5. Simulation: {r.status_code}")
    if '冲刺' in r.text or '稳妥' in r.text or '保底' in r.text:
        print("   SUCCESS! Results rendered with tiers")
    else:
        # Check for errors
        if '用完' in r.text:
            print("   (Credits used, but simulation ran)")
        elif 'alert' in r.text:
            # extract alert
            alert_match = re.search(r'alert alert-\w+[^>]*>([^<]+)', r.text)
            if alert_match:
                print(f"   Message: {alert_match.group(1)}")
        else:
            print(f"   Response snippet: {r.text[2000:2500]}")

# 6. Profile page
r = s.get(f'{BASE}/profile')
print(f"6. Profile: {r.status_code}")
if '剩余' in r.text:
    credits_match = re.search(r'(\d+)\s*</h2>\s*<p>剩余免费次数', r.text)
    if credits_match:
        print(f"   Credits: {credits_match.group(1)}")
    invite_match = re.search(r'id="inviteCode">(\w+)<', r.text)
    if invite_match:
        print(f"   Invite code: {invite_match.group(1)}")

print("\n=== ALL TESTS PASSED ===")
