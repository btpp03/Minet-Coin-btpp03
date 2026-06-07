#!/usr/bin/env python3
"""
Minet.vn Auto Coin - UC mode + Discord OAuth + cf_clearance
不用 uc_gui_click_captcha（headless 不支持 PyAutoGUI）
"""
import os, re, json, time, random, urllib.request
from seleniumbase import SB

TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID", "")
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN", "")
CF_CLEARANCE = os.environ.get("CF_CLEARANCE", "")
MAX_ADS = int(os.environ.get("MAX_ADS", "20"))
MINET_BASE = "https://dashboard.minet.vn"
ACCOUNT_NAME = os.environ.get("ACCOUNT_NAME", "btpp03")
PROXY = os.environ.get("PROXY", "")

def notify(text):
    if not TG_BOT_TOKEN or not TG_CHAT_ID: return
    try:
        url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
        data = json.dumps({"chat_id": TG_CHAT_ID, "text": text}).encode()
        urllib.request.urlopen(urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}), timeout=10)
    except: pass

def wait_cf(sb, max_wait=60):
    """等待 Cloudflare 完成（不调用 PyAutoGUI）"""
    for i in range(max_wait // 2):
        time.sleep(2)
        body = sb.get_text("body")[:300].lower()
        if "security verification" not in body and \
           "checking" not in body and \
           "just a moment" not in body and \
           "waiting for" not in body:
            print(f"[CF] ✅ Passed!")
            return True
        if i % 5 == 0:
            print(f"[CF] Waiting... ({i*2}s)")
    return False

def login(sb):
    """使用 cf_clearance + Discord token"""
    print(f"[login] Opening minet.vn...")
    
    sb.uc_open_with_reconnect(MINET_BASE, reconnect_time=30)
    time.sleep(5)
    
    # 设置 cf_clearance cookie
    if CF_CLEARANCE:
        print("[login] Setting cf_clearance...")
        try:
            sb.driver.add_cookie({
                "name": "cf_clearance",
                "value": CF_CLEARANCE,
                "path": "/",
                "domain": ".minet.vn"
            })
            print("[login] cf_clearance set!")
        except Exception as e:
            print(f"[login] cf_clearance error: {e}")
    
    # 刷新页面
    print("[login] Refreshing...")
    sb.execute_script("location.reload();")
    time.sleep(10)
    
    url = sb.driver.current_url
    print(f"[login] URL: {url[:80]}")
    body_text = sb.get_text("body")[:500]
    print(f"[login] Page: {body_text[:300]}")
    
    # 检查是否过 CF
    if not wait_cf(sb):
        print("[login] CF timeout")
        return False
    
    time.sleep(3)
    body_text = sb.get_text("body")[:500]
    print(f"[login] After CF: {body_text[:200]}")
    
    # 点 Discord 登录
    print("[login] Looking for Discord login...")
    try:
        discord_btn = None
        btns = sb.find_elements("button, a")
        for b in btns:
            text = b.text.lower()
            if "discord" in text:
                discord_btn = b
                print(f"[login] Found: {b.text}")
                break
        
        if not discord_btn:
            links = sb.find_elements("a")
            for l in links:
                href = l.get_attribute("href") or ""
                if "discord" in href.lower():
                    discord_btn = l
                    print(f"[login] Found link: {href[:60]}")
                    break
        
        if discord_btn:
            discord_btn.click()
            time.sleep(8)
            
            url = sb.driver.current_url
            print(f"[login] After click: {url[:80]}")
            
            if "discord" in url.lower():
                print("[login] On Discord, injecting token...")
                sb.execute_script(f"window.localStorage.setItem('token', '{DISCORD_TOKEN}');")
                time.sleep(2)
                sb.execute_script("location.reload();")
                time.sleep(8)
        else:
            print("[login] Discord button not found")
            return False
    
    except Exception as e:
        print(f"[login] Error: {e}")
        return False
    
    url = sb.driver.current_url
    print(f"[login] Final URL: {url[:80]}")
    body_text = sb.get_text("body")[:500]
    print(f"[login] Final page: {body_text[:200]}")
    
    if "dashboard" in url.lower() and "login" not in url.lower():
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
        print(f"[ad {idx}] Navigating to /earn...")
        sb.open(f"{MINET_BASE}/earn")
        
        # 设置 cf_clearance
        if CF_CLEARANCE:
            try:
                sb.driver.add_cookie({
                    "name": "cf_clearance",
                    "value": CF_CLEARANCE,
                    "path": "/",
                    "domain": ".minet.vn"
                })
            except: pass
        
        sb.execute_script("location.reload();")
        time.sleep(10)
        
        if not wait_cf(sb):
            print(f"[ad {idx}] CF timeout")
            return False
        
        time.sleep(3)
        
        body_text = sb.get_text("body")[:500]
        print(f"[ad {idx}] Page: {body_text[:200]}")
        
        btn = sb.find_element("#link4mBtn")
        if btn:
            print(f"[ad {idx}] Found button: {btn.text}")
            btn.click()
            time.sleep(3)
        else:
            print(f"[ad {idx}] Button not found")
            return False
        
        print(f"[ad {idx}] Waiting for ad...")
        for i in range(90):
            time.sleep(1)
            btns = sb.find_elements("button")
            for b in btns:
                if "claim" in b.text.lower():
                    print(f"[ad {idx}] Claim found!")
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
    if not DISCORD_TOKEN:
        print("ERROR: DISCORD_TOKEN not set"); return 0
    if not CF_CLEARANCE:
        print("WARNING: CF_CLEARANCE not set")
    print(f"\n{'='*50}\nMinet.vn Auto Coin ({ACCOUNT_NAME})\n{'='*50}")
    
    sb_args = {"uc": True, "headless": True, "locale_code": "en"}
    if PROXY:
        sb_args["proxy"] = PROXY
    
    with SB(**sb_args) as sb:
        if not login(sb):
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
