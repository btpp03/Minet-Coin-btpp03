#!/usr/bin/env python3
"""
Minet.vn Login Streak Auto-Claim (Pure HTTP)
Uses connect.sid cookie + residential proxy
Daily: GET /api/streak/claim (no browser, no captcha needed)
"""
import os, sys, json, time, subprocess
from datetime import datetime, timezone
import urllib.request

TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID", "")
SESSION_COOKIE = os.environ.get("SESSION_COOKIE", "")
PROXY = os.environ.get("PROXY", "")  # socks5://user:pass@ip:port
ACCOUNT_NAME = os.environ.get("ACCOUNT_NAME", "btpp03")
MINET_BASE = "https://dashboard.minet.vn"

# Exit codes
EXIT_OK = 0
EXIT_NO_SESSION = 1
EXIT_API_FAIL = 2

def run_curl(args, timeout=30):
    """Run curl with SOCKS5/HTTP proxy + browser UA"""
    cmd = ["curl", "-s", "--max-time", str(timeout),
           "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"]
    
    if PROXY:
        if PROXY.startswith("socks5://"):
            # Strip socks5:// and extract user/pass/host:port
            stripped = PROXY[9:]
            if "@" in stripped:
                auth, hp = stripped.split("@", 1)
                cmd += ["--socks5-hostname", f"{auth}@{hp}"]
            else:
                cmd += ["--socks5-hostname", stripped]
        else:
            cmd += ["-x", PROXY]
    
    cmd += args
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout+5)
        return r.stdout, r.returncode
    except Exception as e:
        return f"ERR:{e}", -1

def notify(text):
    """Telegram notify"""
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        print(f"[notify] {text[:100]}")
        return
    try:
        data = json.dumps({"chat_id": TG_CHAT_ID, "text": text, "parse_mode": "HTML"}).encode()
        urllib.request.urlopen(urllib.request.Request(
            f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage",
            data=data,
            headers={"Content-Type": "application/json"}
        ), timeout=10)
        print(f"[notify] ✅ Sent: {text[:50]}")
    except Exception as e:
        print(f"[notify] ❌ Failed: {e}")

def log(m):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {m}", flush=True)

def get_streak_info():
    """GET /api/streak/info with safe diagnostics and retries."""
    for attempt in range(1, 4):
        body, rc = run_curl([
            "-H", f"Cookie: connect.sid={SESSION_COOKIE}",
            "-w", "\n__HTTP__:%{http_code}|%{url_effective}|%{time_total}",
            f"{MINET_BASE}/api/streak/info"
        ])
        marker = "\n__HTTP__:"
        payload, meta = (body.rsplit(marker, 1) + [""])[:2] if marker in body else (body, "")
        log(f"Streak info attempt {attempt}/3: curl_rc={rc}, http={meta or 'n/a'}, bytes={len(payload)}")
        try:
            return json.loads(payload)
        except Exception:
            # Never print cookies; response body is truncated and normally empty/HTML.
            preview = payload[:160].replace("\n", " ")
            log(f"Streak info parse fail: {preview!r}")
        if attempt < 3:
            time.sleep(attempt * 5)
    return None

def claim_streak():
    """GET /api/streak/claim - returns 302 redirect to /dashboard"""
    body, code = run_curl([
        "-H", f"Cookie: connect.sid={SESSION_COOKIE}",
        "-w", "\\n%{http_code}|%{redirect_url}",
        f"{MINET_BASE}/api/streak/claim"
    ])
    return body, code

def main():
    log(f"=== Minet Login Streak Auto-Claim ({ACCOUNT_NAME}) ===")
    log(f"PROXY: {'✅' if PROXY else '❌'}")
    log(f"SESSION: {'✅' if SESSION_COOKIE else '❌'}")
    
    if not SESSION_COOKIE:
        log("❌ SESSION_COOKIE not set")
        notify(f"❌ [{ACCOUNT_NAME}] SESSION_COOKIE not set")
        return EXIT_NO_SESSION
    
    # 1. Get current state
    log("Getting streak info...")
    info = get_streak_info()
    if not info:
        log("❌ Failed to get streak info (session invalid or proxy fail)")
        notify(f"❌ [{ACCOUNT_NAME}] Streak info failed (session may be expired)")
        return EXIT_API_FAIL
    
    log(f"Current streak: {info.get('currentStreak')} days")
    log(f"Best: {info.get('longestStreak')} days")
    log(f"Total logins: {info.get('totalLogins')}")
    log(f"Total rewards: {info.get('totalRewards')} coins")
    log(f"Can claim: {info.get('canClaim')}")
    
    can_claim = info.get("canClaim", False)
    if not can_claim:
        msg = f"[{ACCOUNT_NAME}] Minet Login Streak (HTTP) — already claimed today\nStreak: {info.get('currentStreak')}d (best {info.get('longestStreak')}d)\nTotal rewards: {info.get('totalRewards')} coins"
        log("Already claimed today")
        # Still notify so we have daily log
        notify(msg)
        return EXIT_OK
    
    # 2. Claim
    log("Claiming streak...")
    body, code = claim_streak()
    log(f"Claim response (code {code}): {body[:200]}")
    
    # 3. Verify
    time.sleep(2)
    info2 = get_streak_info()
    if info2:
        new_streak = info2.get("currentStreak")
        new_total = info2.get("totalRewards")
        can2 = info2.get("canClaim")
        
        # Calculate delta
        delta_streak = new_streak - info.get("currentStreak", 0)
        delta_coins = new_total - info.get("totalRewards", 0)
        
        if not can2 and delta_coins > 0:
            streak_note = ""
            if delta_streak < 0:
                streak_note = f"\n⚠️ Streak reset (was {info.get('currentStreak')}d, now {new_streak}d — missed a day)"
            msg = f"""[{ACCOUNT_NAME}] Minet Login Streak ✅
🎯 Claimed +{delta_coins} coins
📅 Streak: {info.get('currentStreak')}d → {new_streak}d (best {info2.get('longestStreak')}d){streak_note}
💰 Total rewards: {info.get('totalRewards')} → {new_total} coins"""
            log(f"✅ Claimed! +{delta_coins} coins, streak {info.get('currentStreak')} → {new_streak}")
            notify(msg)
            return EXIT_OK
        else:
            msg = f"❌ [{ACCOUNT_NAME}] Claim failed. Before: {info.get('currentStreak')}d/{info.get('totalRewards')}c, After: {new_streak}d/{new_total}c, canClaim={can2}, delta_coins={delta_coins}"
            log(msg)
            notify(msg)
            return EXIT_API_FAIL
    
    log("❌ Failed to verify claim")
    return EXIT_API_FAIL

if __name__ == "__main__":
    sys.exit(main())
