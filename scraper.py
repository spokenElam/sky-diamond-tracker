#!/usr/bin/env python3
"""
天鑽 The Regent - Property Listing Tracker
"""

import json
import smtplib
import os
import sys
import traceback
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path

def log(msg):
    print(msg, flush=True)

log("=" * 50)
log("天鑽放盤追蹤器 The Regent Listing Tracker")
log(f"時間 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
log("=" * 50)
log("")

CONFIG = {
    "TARGET_TOWERS": [8, 9, 10, 11, 12, 13, 15, 16, 18],
    "MAX_SIZE": 600,
    "TARGET_ROOMS": [1, 2],
    "EMAIL_RECIPIENTS": [
        "acforgames9394@gmail.com"
    ],
    "CACHE_FILE": "data/listings_cache.json",
    "OUTPUT_FILE": "data/listings.json"
}

log(f"Target towers: {CONFIG['TARGET_TOWERS']}")
log(f"Email recipients: {CONFIG['EMAIL_RECIPIENTS']}")
log("")

def send_test_email():
    sender_email = os.environ.get("EMAIL_SENDER", "").strip()
    sender_password = os.environ.get("EMAIL_PASSWORD", "").strip()
    
    log("=" * 50)
    log("EMAIL SETUP CHECK")
    log("=" * 50)
    
    if not sender_email:
        log("❌ EMAIL_SENDER not set")
        return False
    log(f"✅ EMAIL_SENDER: {sender_email}")
    
    if not sender_password:
        log("❌ EMAIL_PASSWORD not set")
        return False
    log(f"✅ EMAIL_PASSWORD: ({len(sender_password)} chars)")
    
    log("")
    log("Sending test email...")
    
    subject = f"🏠 天鑽監控測試 Test - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    body = f"""
==================================================
天鑽 The Regent - 系統測試成功！
==================================================

✅ 郵件設定正確！Email setup working!

監控設定:
- 座數 Towers: {CONFIG['TARGET_TOWERS']}
- 房數 Rooms: {CONFIG['TARGET_ROOMS']}
- 面積: <{CONFIG['MAX_SIZE']} sq.ft.

Dashboard: https://spokenelam.github.io/sky-diamond-tracker/

---
發送時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = ", ".join(CONFIG["EMAIL_RECIPIENTS"])
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        log("Connecting to smtp.gmail.com:465...")
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            log("Logging in...")
            server.login(sender_email, sender_password)
            log("Sending...")
            server.sendmail(sender_email, CONFIG["EMAIL_RECIPIENTS"], msg.as_string())
        
        log("")
        log("✅✅✅ EMAIL SENT SUCCESSFULLY! ✅✅✅")
        log(f"Sent to: {CONFIG['EMAIL_RECIPIENTS']}")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        log("")
        log("❌❌❌ AUTHENTICATION FAILED ❌❌❌")
        log(f"Error: {e}")
        log("Check: App Password should be 16 chars WITHOUT spaces")
        return False
        
    except Exception as e:
        log(f"❌ EMAIL FAILED: {e}")
        traceback.print_exc()
        return False

def save_data():
    Path("data").mkdir(exist_ok=True)
    cache = {"last_run": datetime.now().isoformat(), "seen_ids": []}
    Path(CONFIG["CACHE_FILE"]).write_text(json.dumps(cache, indent=2))
    output = {"lastUpdate": datetime.now().isoformat(), "listings": []}
    Path(CONFIG["OUTPUT_FILE"]).write_text(json.dumps(output, indent=2))
    log("Data saved ✓")

def main():
    try:
        send_test_email()
        log("")
        save_data()
        log("")
        log("=" * 50)
        log("Done! 完成！")
        log("=" * 50)
    except Exception as e:
        log(f"❌ ERROR: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
