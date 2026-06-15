#!/usr/bin/env python3
"""
Minet.vn Auto Coin - UC mode + Discord OAuth + proxy
策略: 不用 CF_CLEARANCE (cookie IP 不匹配会弹 alert), 
      靠 uc_open_with_reconnect + alert dismiss + retry
"""
import os, re, json, time, random, urllib.request, sys
from seleniumbase import SB

TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID", "")
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN", "")
MAX_ADS = int(os.environ.get("MAX_ADS", "20"))
MINET_BASE = "https://dashboard.minet.vn"
ACCOUNT_NAME = os.environ.get("ACCOUNT_NAME", "btpp03")
PROXY = os.environ.get("PROXY", "")
# CF_CLEARANCE not used - causes IP mismatch alert
CF_CLEARANCE = ""

def notify(text):
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        print(f"[notify] Telegram not configured, skipping: {text[:50]}")
        return
    try:
        url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
        data = json.dumps({"chat_id": TG_CHAT_ID, "text": text}).encode()
        urllib.request.urlopen(urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}), timeout=10)
        print(f"[notify] ✅ Sent: {text[:50]}")
    except Exception as e:
        print(f"[notify] ❌ Failed: {e}")

def save_debug(sb, name):
    """保存失败现场，供 GitHub Actions artifact 下载排查"""
    try:
        sb.save_screenshot(f"/tmp/{name}.png")
    except Exception as e:
        print(f"[debug] screenshot failed: {e}")
    try:
        html = sb.driver.page_source
        with open(f"/tmp/{name}.html", "w", encoding="utf-8") as f:
            f.write(html)
    except Exception as e:
        print(f"[debug] html dump failed: {e}")
    try:
        with open(f"/tmp/{name}.txt", "w", encoding="utf-8") as f:
            f.write("URL: " + sb.driver.current_url + "\n\n")
            f.write(sb.get_text("body")[:5000])
    except Exception as e:
        print(f"[debug] text dump failed: {e}")
    print(f"[debug] Saved /tmp/{name}.png/.html/.txt")

def dismiss_alerts(sb, max_attempts=3):
    """Dismiss any open alerts (CF 'complete verification' etc)"""
    for i in range(max_attempts):
        try:
            alert = sb.driver.switch_to.alert
            text = alert.text
            print(f"[alert] Dismissing alert: {text[:80]}")
            alert.dismiss()
            time.sleep(1)
        except Exception:
            # No alert open
            return True
    return False

def wait_page_load(sb, max_wait=120):
    """等待页面真正加载。轮询 + alert dismiss"""
    print("[wait] Waiting for page to fully load...")
    for i in range(max_wait // 3):
        time.sleep(3)
        
        # Dismiss any open alerts (CF "complete verification" popups)
        dismiss_alerts(sb)
        
        url = sb.driver.current_url
        try:
            body = sb.get_text("body")[:500]
        except:
            body = ""
        
        # 加载成功的判断
        if len(body) > 50 and \
           "security verification" not in body.lower() and \
           "just a moment" not in body.lower() and \
           "checking" not in body.lower() and \
           "waiting for" not in body.lower() and \
           "site can't be reached" not in body.lower() and \
           "err_" not in body.lower() and \
           "performing security" not in body.lower():
            print(f"[wait] ✅ Page loaded! URL: {url[:60]}")
            print(f"[wait] Content: {body[:200]}")
            return True
        
        if i % 10 == 0:
            print(f"[wait] Waiting... ({i*3}s) URL: {url[:60]}")
            print(f"[wait] Body: {body[:150]}")
    
    print("[wait] ❌ Page load timeout")
    return False

def verify_login(sb):
    """验证是否真的登录了（不只是 URL 正确）"""
    print("[verify] Checking if logged in...")
    try:
        body = sb.get_text("body")[:1000].lower()
        url = sb.driver.current_url.lower()
        
        if "discord" in body and ("login" in url or "sign in" in body):
            print("[verify] ❌ Still on login page")
            return False
        
        logged_in_indicators = ["coin", "balance", "point", "earn", "dashboard", "logout", "sign out"]
        found = [x for x in logged_in_indicators if x in body]
        print(f"[verify] Logged in indicators found: {found}")
        
        if len(found) >= 2:
            print("[verify] ✅ Login verified!")
            return True
        
        # 尝试访问 API 验证
        try:
            sb.open(f"{MINET_BASE}/api/user/me")
            time.sleep(3)
            api_body = sb.get_text("body")[:500]
            if "error" not in api_body.lower() and len(api_body) > 10:
                print(f"[verify] ✅ API check passed: {api_body[:200]}")
                return True
            print(f"[verify] API response: {api_body[:200]}")
        except:
            pass
        
        return False
    except Exception as e:
        print(f"[verify] ❌ Error: {e}")
        return False

def login(sb):
    """使用代理 + Discord OAuth, 让 UC mode 自己处理 CF challenge"""
    print(f"[login] Starting login process...")
    print(f"[login] Discord token: {'✅ SET' if DISCORD_TOKEN else '❌ NOT SET'}")
    if not DISCORD_TOKEN:
        notify(f"❌ [{ACCOUNT_NAME}] DISCORD_TOKEN not set!")
        return False
    
    if PROXY:
        print(f"[login] Using proxy: {PROXY[:30]}...")
    
    # Open with reconnect - UC mode handles Turnstile challenges automatically
    # reconnect_time=60 gives CF enough time to auto-pass
    sb.uc_open_with_reconnect(MINET_BASE, reconnect_time=60)
    time.sleep(15)
    
    # Dismiss any alerts that may have appeared during challenge
    dismiss_alerts(sb)
    
    url = sb.driver.current_url
    print(f"[login] URL: {url[:80]}")
    try:
        body = sb.get_text("body")[:300]
        print(f"[login] Body: {body[:150]}")
    except:
        body = ""
    
    # 等页面加载
    if not wait_page_load(sb):
        print("[login] Page load timeout, retrying with reload...")
        # Try one more reload + wait
        try:
            sb.execute_script("location.reload();")
            time.sleep(20)
            dismiss_alerts(sb)
        except:
            pass
        if not wait_page_load(sb):
            save_debug(sb, "minet_page_load_timeout")
            notify(f"❌ [{ACCOUNT_NAME}] Page load timeout")
            return False
    
    url = sb.driver.current_url
    print(f"[login] After wait URL: {url[:80]}")
    
    # 点 Discord 登录
    print("[login] Looking for Discord login button...")
    try:
        # Dismiss alerts first
        dismiss_alerts(sb)
        
        discord_btn = None
        btns = sb.find_elements("button, a")
        for b in btns:
            text = b.text.lower()
            if "discord" in text:
                discord_btn = b
                print(f"[login] Found button: {b.text}")
                break
        
        if not discord_btn:
            links = sb.find_elements("a")
            for l in links:
                href = l.get_attribute("href") or ""
                if "discord" in href.lower():
                    discord_btn = l
                    print(f"[login] Found link: {href[:60]}")
                    break
        
        if not discord_btn:
            print("[login] ❌ Discord button not found")
            save_debug(sb, "minet_login_no_discord_button")
            return False
        
        discord_btn.click()
        time.sleep(10)
        
        # If alert popped up after click, dismiss and retry
        dismiss_alerts(sb)
        
        url = sb.driver.current_url
        print(f"[login] After click: {url[:80]}")
        
        if "discord" in url.lower():
            print("[login] On Discord page, injecting token...")
            sb.execute_script(f"window.localStorage.setItem('token', '{DISCORD_TOKEN}');")
            time.sleep(2)
            sb.execute_script("location.reload();")
            time.sleep(8)
            dismiss_alerts(sb)
            
            url = sb.driver.current_url
            print(f"[login] After reload: {url[:80]}")
    
    except Exception as e:
        print(f"[login] Error during Discord click: {e}")
        # Check if it's an alert issue
        if "alert" in str(e).lower():
            print("[login] Alert issue, trying to dismiss and retry...")
            dismiss_alerts(sb)
            notify(f"❌ [{ACCOUNT_NAME}] Alert blocked Discord click: {e}")
        else:
            notify(f"❌ [{ACCOUNT_NAME}] Discord login error: {e}")
        return False
    
    # 等待页面稳定
    time.sleep(5)
    dismiss_alerts(sb)
    
    # 验证登录
    if verify_login(sb):
        print("[login] ✅ Login SUCCESS!")
        return True
    
    print("[login] ❌ Login FAILED - not verified")
    save_debug(sb, "minet_login_not_verified")
    notify(f"❌ [{ACCOUNT_NAME}] Login not verified")
    return False

def get_balance(sb):
    try:
        t = sb.get_text("body")
        m = re.search(r'(\d[\d,]*)\s*(?:coins?|points?|balance)', t, re.I)
        return int(m.group(1).replace(',', '')) if m else 0
    except:
        return 0

def watch_ad(sb, idx):
    print(f"[ad {idx}] Starting ad watch...")
    try:
        print(f"[ad {idx}] Navigating to /earn...")
        sb.open(f"{MINET_BASE}/earn")
        
        if not wait_page_load(sb):
            print(f"[ad {idx}] Page load timeout")
            return False
        
        time.sleep(3)
        dismiss_alerts(sb)
        
        try:
            body_text = sb.get_text("body")[:500]
            print(f"[ad {idx}] Page: {body_text[:200]}")
        except:
            body_text = ""
        
        btn = None
        try:
            btn = sb.find_element("#link4mBtn")
        except:
            pass
        
        if btn:
            print(f"[ad {idx}] Found button: {btn.text}")
            btn.click()
            time.sleep(3)
        else:
            print(f"[ad {idx}] #link4mBtn not found, trying other selectors...")
            all_btns = sb.find_elements("button, a")
            for b in all_btns:
                text = b.text.lower()
                if "watch" in text or "ad" in text or "link4m" in text or "claim" in text:
                    print(f"[ad {idx}] Found alternative: {b.text}")
                    b.click()
                    time.sleep(3)
                    break
            else:
                print(f"[ad {idx}] No ad button found")
                save_debug(sb, f"minet_ad_{idx}_no_button")
                return False
        
        print(f"[ad {idx}] Waiting for claim button...")
        for i in range(90):
            time.sleep(1)
            dismiss_alerts(sb)  # Handle any CF alerts during ad
            btns = sb.find_elements("button")
            for b in btns:
                if "claim" in b.text.lower():
                    print(f"[ad {idx}] Claim found! Clicking...")
                    time.sleep(2)
                    b.click()
                    time.sleep(2)
                    print(f"[ad {idx}] ✅ Claimed!")
                    return True
            if i % 10 == 0:
                print(f"[ad {idx}] Waiting... ({i}s)")
        
        print(f"[ad {idx}] Timeout - no claim button")
        return False
    except Exception as e:
        print(f"[ad {idx}] Error: {e}")
        return False

def run():
    print(f"\n{'='*50}")
    print(f"Minet.vn Auto Coin ({ACCOUNT_NAME})")
    print(f"DISCORD_TOKEN: {'✅' if DISCORD_TOKEN else '❌'}")
    print(f"CF_CLEARANCE: ❌ (disabled, was causing IP mismatch alert)")
    print(f"PROXY: {'✅' if PROXY else '❌'}")
    print(f"{'='*50}\n")
    
    if not DISCORD_TOKEN:
        print("ERROR: DISCORD_TOKEN not set")
        notify(f"❌ [{ACCOUNT_NAME}] DISCORD_TOKEN not set!")
        return 0
    
    sb_args = {"uc": True, "headless": True, "locale_code": "en"}
    if PROXY:
        sb_args["proxy"] = PROXY
    
    with SB(**sb_args) as sb:
        if not login(sb):
            return 0
        
        initial = get_balance(sb)
        print(f"Initial balance: {initial} coins")
        
        earned = 0
        for i in range(1, MAX_ADS+1):
            ok = watch_ad(sb, i)
            if ok:
                earned += 1
            else:
                print(f"[ad {i}] Failed, stopping...")
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
    earned = run()
    if earned <= 0:
        print("[exit] No ads earned or login failed; marking workflow as failed")
        sys.exit(1)
    sys.exit(0)
