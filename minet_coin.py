#!/usr/bin/env python3
"""
Minet.vn Auto Coin - Watch ads and claim rewards
UC mode + ad blocking to reduce memory usage
"""
import os, re, json, time, random, urllib.request
from seleniumbase import SB

TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID", "")
MINET_SID = os.environ.get("MINET_SID", "")
MAX_ADS = int(os.environ.get("MAX_ADS", "20"))
MINET_BASE = "https://dashboard.minet.vn"
ACCOUNT_NAME = os.environ.get("ACCOUNT_NAME", "btpp03")

# 广告域名黑名单
AD_DOMAINS = [
    "googleads.g.doubleclick.net",
    "pagead2.googlesyndication.com",
    "adservice.google.com",
    "www.googletagmanager.com",
    "ad.doubleclick.net",
    "ad.turn.com",
    "cdn.taboola.com",
    "static.criteo.net",
    "cdn-vitals.com",
    "analytics.ocean.io",
    "fundingchoicesmessages.google.com",
]

def notify(text):
    if not TG_BOT_TOKEN or not TG_CHAT_ID: return
    try:
        url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
        data = json.dumps({"chat_id": TG_CHAT_ID, "text": text}).encode()
        urllib.request.urlopen(urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}), timeout=10)
    except: pass

def block_ads(sb):
    """使用 Chrome DevTools Protocol 屏蔽广告资源"""
    try:
        # 启用 Network 域
        sb.driver.execute_cdp_cmd("Network.enable", {})
        
        # 设置请求拦截
        sb.driver.execute_cdp_cmd("Network.setBlockedURLs", {
            "urls": AD_DOMAINS
        })
        print("[ads] ✅ 广告已屏蔽")
    except Exception as e:
        print(f"[ads] ⚠️ 屏蔽失败: {e}")

def login(sb, sid):
    """UC mode: open page first, solve Cloudflare, then set cookie"""
    print("[login] Opening minet.vn with UC mode...")
    sb.uc_open_with_reconnect(MINET_BASE, reconnect_time=12)
    time.sleep(3)
    
    url = sb.driver.current_url
    print(f"[login] Initial URL: {url[:60]}")
    
    # 检查 Cloudflare
    body = sb.get_text("body")[:200]
    if "Just a moment" in body:
        print("[login] Cloudflare challenge...")
        sb.uc_gui_click_captcha()
        time.sleep(5)
    
    # 屏蔽广告
    block_ads(sb)
    
    print("[login] Setting cookie...")
    sb.driver.add_cookie({"name": "connect.sid", "value": sid, "path": "/", "domain": "dashboard.minet.vn"})
    
    print("[login] Opening earn page...")
    sb.open(f"{MINET_BASE}/earn")
    time.sleep(5)
    
    url = sb.driver.current_url
    print(f"[login] Earn URL: {url[:60]}")
    
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
        btn = sb.find_element("#link4mBtn")
        if btn:
            print(f"[ad {idx}] Clicking #link4mBtn...")
            btn.click()
            time.sleep(3)
        
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
