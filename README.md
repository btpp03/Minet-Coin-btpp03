# Minet Login Streak Auto-Claim 🤖

Auto-claim daily Minet.vn login streak rewards via GitHub Actions. Pure HTTP, no browser, no captcha.

## 🎯 What it does

- Auto-claims the daily login streak on [Minet.vn](https://dashboard.minet.vn)
- Runs twice daily (00:07 + 12:07 UTC) via GitHub Actions cron
- Sends Telegram notification on each run

## 💰 Rewards

| Streak | Daily Bonus | Notes |
|--------|------------|-------|
| 1 day | 10 coins | Every day |
| 3 days | 100 coins | Milestone 🔥 |
| 7 days | 350 coins | Milestone ⚡ |
| 14 days | 950 coins | Milestone 💪 |
| 30 days | 1,600 coins | Milestone 👑 |
| 60 days | 8,000 coins | Milestone 🌟 |
| **100 days** | **18,020 coins** | Milestone 🏆 |

**Timezone**: Minet uses `Asia/Ho_Chi_Minh` (UTC+7). The 00:07 UTC cron = 07:07 ICT, and 12:07 UTC = 19:07 ICT.

## 🛠️ How it works

1. **GET `/api/streak/info`** — check current streak state
2. **GET `/api/streak/claim`** — claim today's 10 coins (returns 302 → `/dashboard?success=STREAKCLAIMED`)
3. **Verify** the delta on streak/totalRewards
4. **Notify** via Telegram

**Key insight**: Minet's `/api/*` endpoints don't require Cloudflare challenge. Only `/`, `/earn`, `/gift` page loads need `cf_clearance`. So we can claim directly with just `connect.sid` cookie + residential proxy — no browser, no captcha.

## 📦 Files

- `minet_streak.py` — main script (5.6KB, pure stdlib + curl)
- `.github/workflows/streak.yml` — cron schedule
- `requirements.txt` — empty (no Python deps needed)

## 🔐 Required Secrets

Set these in **Settings → Secrets and variables → Actions**:

| Secret | Example | Where to get it |
|--------|---------|-----------------|
| `SESSION_COOKIE` | `s%3Aabc123...XYZ` | Browser DevTools → Application → Cookies → `connect.sid` on `dashboard.minet.vn` |
| `PROXY` | `socks5://user:pass@ip:port` | Residential SOCKS5 proxy (datacenter IPs get blocked) |
| `TG_BOT_TOKEN` | `123456:ABC-DEF...` | From [@BotFather](https://t.me/BotFather) |
| `TG_CHAT_ID` | `6503411367` | Your Telegram chat ID (or group ID) |

### Getting `connect.sid`

1. Log in to [dashboard.minet.vn](https://dashboard.minet.vn) in your browser
2. Open DevTools (F12) → **Application** tab → **Cookies** → `https://dashboard.minet.vn`
3. Find `connect.sid` → copy the **Value** (URL-encoded)
4. The session typically lasts 1-7 days; refresh it when you get "session invalid" notifications

### Getting a residential proxy

CloudFlare blocks datacenter IPs, so you need a residential or home proxy. Free SOCKS5 proxies usually don't work — use a paid service like:
- [IPRoyal](https://iproyal.com) (~$2-3/GB)
- [BrightData](https://brightdata.com)
- Or run your own home VPN (WireGuard, OpenVPN, etc.)

The proxy must support SOCKS5 with authentication. Format: `socks5://username:password@host:port`

## 📊 Exit codes

| Code | Meaning | Action |
|------|---------|--------|
| 0 | Success (claimed or already claimed today) | None |
| 1 | `SESSION_COOKIE` not set | Add secret |
| 2 | API call failed (session expired or proxy down) | Refresh cookie / check proxy |

## 🔄 Maintenance

- **Session refresh**: When you get a "session invalid" TG message, log into Minet again and update the `SESSION_COOKIE` secret.
- **Proxy rotation**: If your proxy dies, update the `PROXY` secret.
- **Manual trigger**: Actions tab → "Minet Login Streak (HTTP)" → "Run workflow"

## ⚠️ Why no shortlink/Linkvertise automation?

We tried. The defenses are too strong:
- **link4m**: reCAPTCHA v2 + hCaptcha (needs paid solver)
- **linkvertise**: Anti-bot behavior analysis — even manual users get kicked at stage 3 if clicking too fast

The 10 coins/day + milestone rewards are more reliable and 100% passive.

## 📝 License

Personal use only. Not affiliated with Minet.vn.
