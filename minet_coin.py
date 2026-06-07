#!/usr/bin/env python3
"""
Minet.vn Auto Coin - Watch ads and claim rewards
"""
import os, re, json, time, random, urllib.request
from seleniumbase import SB

TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID", "")
MINET_SID = os.environ.get("MINET_SID", "")
MAX_ADS = int(os.environ.get("MAX_ADS", "20"))
MINET_BASE = "https://dashboard.minet.vn"
ACCOUNT_NAME = os.environ.get("ACCOUNT_NAME", "btpp03")

def notify(text):
    if not TG_BOT_TOKEN or not TG_CHAT_ID: return
    try:
        url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
        data = json.dumps({"chat_id": TG_CHAT_ID, "text": text}).encode()
        urllib.request.urlopen(urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}), timeout=10)
    except: pass

def login_cookie(sb, sid):
    print("[login] Setting cookie...")
    sb.open(MINET_BASE)
    time.sleep(2)
    sb.driver.add_cookie({"name": "connect.sid", "value": sid, "path": "/", "domain": "dashboard.minet.vn"})
    sb.open(f"{MINET_BASE}/earn")
    time.sleep(3)
    url = sb.driver.current_url
    if "login" not in url.lower():
        print(f"[login] OK - {url[:60]}")
        return True
    print(f"[login] Failed - {url[:60]}")
    return False

def get_balance(sb):
    try:
        t = sb.get_text("body")
        m = re.search(r'(\d[\d,]*)\s*(?:coins?|points?|balance)', t, re.I)
        return int(m.group(1).replace(',', '')) if m else 0
    except: return 0

def watch_ad(sb, idx):
    print(f"[ad {idx}] Looking for play button...")
    try:
        # Find and click play/watch button
        btns = sb.find_elements("button")
        for btn in btns:
            txt = btn.text.lower()
            if "watch" in txt or "play" in txt or "earn" in txt or "start" in txt:
                print(f"[ad {idx}] Clicking: {btn.text}")
                btn.click()
                time.sleep(3)
                break
        
        # Wait for ad to finish (usually 30-60 seconds)
        print(f"[ad {idx}] Waiting for ad...")
        for i in range(90):  # Max 90 seconds
            time.sleep(1)
            # Check for claim button
            btns = sb.find_elements("button")
            for btn in btns:
                if "claim" in btn.text.lower():
                    print(f"[ad {idx}] Claim button found!")
                    time.sleep(2)  # Small delay before clicking
                    btn.click()
                    time.sleep(2)
                    print(f"[ad {idx}] ✅ Claimed!")
                    return True
            # Check if ad is still playing
            if i % 10 == 0:
                print(f"[ad {idx}] Waiting... ({i}s)")
        
        print(f"[ad {idx}] Timeout waiting for claim button")
        return False
    except Exception as e:
        print(f"[ad {idx}] Error: {e}")
        return False

def run():
    if not MINET_SID:
        print("ERROR: MINET_SID not set"); return 0
    print(f"\n{'='*50}\nMinet.vn Auto Coin ({ACCOUNT_NAME})\n{'='*50}")
    with SB(uc=True, headless=True, locale_code="en") as sb:
        if not login_cookie(sb, MINET_SID):
            notify(f"❌ [{ACCOUNT_NAME}] Minet login failed")
            return 0
        initial = get_balance(sb)
        print(f"Balance: {initial} coins")
        
        earned = 0
        for i in range(1, MAX_ADS+1):
            ok = watch_ad(sb, i)
            if ok:
                earned += 1
            else:
                print(f"[ad {i}] Failed, stopping")
                break
            time.sleep(random.uniform(2, 5))
        
        final = get_balance(sb)
        d = final - initial
        msg = f"""[{ACCOUNT_NAME}] Minet.vn
Earn: {earned}/{MAX_ADS} ads
Balance: {initial} -> {final} (delta {d})"""
        print(f"\n{'='*50}\n{msg}\n{'='*50}")
        notify(msg)
        return earned

if __name__ == "__main__":
    run()
