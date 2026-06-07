#!/usr/bin/env python3
"""
Minet.vn Auto Coin - UC mode, no proxy
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

def login(sb, sid):
    """UC mode: open page, solve Cloudflare, set cookie"""
    print("[login] Opening minet.vn with UC mode (no proxy)...")
    
    sb.uc_open_with_reconnect(MINET_BASE, reconnect_time=20)
    time.sleep(5)
    
    url = sb.driver.current_url
    print(f"[login] URL: {url[:80]}")
    
    # 检查 Cloudflare
    body = sb.get_text("body")[:300]
    print(f"[login] Body: {body[:150]}")
    
    if "Just a moment" in body or "checking" in body.lower():
        print("[login] Cloudflare challenge...")
        sb.uc_gui_click_captcha()
        time.sleep(8)
    
    # 等页面完全加载
    print("[login] Waiting for page...")
    time.sleep(5)
    
    url = sb.driver.current_url
    print(f"[login] URL after wait: {url[:80]}")
    
    # 打印页面内容
    body_text = sb.get_text("body")[:500]
    print(f"[login] Page text: {body_text[:300]}")
    
    # 设置 cookie
    print("[login] Setting cookie...")
    try:
        sb.driver.add_cookie({"name": "connect.sid", "value": sid, "path": "/", "domain": "dashboard.minet.vn"})
        print("[login] Cookie set!")
    except Exception as e:
        print(f"[login] Cookie error: {e}")
        return False
    
    # 刷新页面
    print("[login] Refreshing...")
    sb.execute_script("location.reload();")
    time.sleep(5)
    
    url = sb.driver.current_url
    print(f"[login] After refresh: {url[:80]}")
    body_text = sb.get_text("body")[:500]
    print(f"[login] Page text: {body_text[:300]}")
    
    if "login" not in url.lower():
        print("[login] ✅ OK!")
        return True
    print("[login] ❌ Failed")
    return False

def get_balance(sb):
    try:
        t = sb.get_text("body")
        m = re.search(r'(\d[\d,]*)\s*(?:coins?|points?|balance)', t, re.I)
        return int(m.group(1).replace(',', '')) if m else 0
    except: return 0

def watch_ad(sb, idx):
    print(f"[ad {idx}] Looking for button...")
    try:
        # 导航到 earn 页面
        print(f"[ad {idx}] Navigating to /earn...")
        sb.open(f"{MINET_BASE}/earn")
        time.sleep(8)
        
        body_text = sb.get_text("body")[:500]
        print(f"[ad {idx}] Page text: {body_text[:300]}")
        
        # 找按钮
        btn = sb.find_element("#link4mBtn")
        if btn:
            print(f"[ad {idx}] Found button: {btn.text}")
            btn.click()
            time.sleep(3)
        else:
            print(f"[ad {idx}] Button not found")
            return False
        
        # 等广告完成
        print(f"[ad {idx}] Waiting for ad...")
        for i in range(90):
            time.sleep(1)
            btns = sb.find_elements("button")
            for b in btns:
                if "claim" in b.text.lower():
                    print(f"[ad {idx}] Claim button found!")
                    time.sleep(2)
                    b.click()
                    time.sleep(2)
                    print(f"[ad {idx}] ✅ Claimed!")
                    return True
            if i % 10 == 0:
                print(f"[ad {idx}] Waiting... ({i}s)")
        
        print(f"[ad {idx}] Timeout")
        return False
    except Exception as e:
        print(f"[ad {idx}] Error: {e}")
        return False

def run():
    if not MINET_SID:
        print("ERROR: MINET_SID not set"); return 0
    print(f"\n{'='*50}\nMinet.vn Auto Coin ({ACCOUNT_NAME})\n{'='*50}")
    with SB(uc=True, headless=True, locale_code="en") as sb:
        if not login(sb, MINET_SID):
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
