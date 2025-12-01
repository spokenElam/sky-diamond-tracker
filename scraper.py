#!/usr/bin/env python3
"""
天鑽 The Regent - Property Listing Tracker
==========================================
"""

import json
import hashlib
import smtplib
import os
import sys
import traceback
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path

# Force unbuffered output
def log(msg):
    print(msg, flush=True)

log("=" * 50)
log("天鑽放盤追蹤器 The Regent Listing Tracker")
log(f"時間 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
log("=" * 50)
log("")

# =============================================================================
# CONFIGURATION 設定
# =============================================================================

CONFIG = {
    "TARGET_TOWERS": [8, 9, 10, 11, 12, 13, 15, 16, 18],
    "MAX_SIZE": 600,
    "TARGET_ROOMS": [1, 2],
    "EMAIL_RECIPIENTS": [
        "acforgames9394@gmail.com",
        "antonicsasaa@gmail.com"
    ],
    "SOURCES": {
        "centanet": {"name_zh": "中原地產", "name_en": "Centaline"},
        "midland": {"name_zh": "美聯物業", "name_en": "Midland"},
        "28hse": {"name_zh": "28Hse", "name_en": "28Hse"},
        "hkp": {"name_zh": "香港置業", "name_en": "HK Property"}
    },
    "CACHE_FILE": "data/listings_cache.json",
    "OUTPUT_FILE": "data/listings.json"
}

log("Configuration loaded ✓")
log(f"Target towers: {CONFIG['TARGET_TOWERS']}")
log(f"Email recipients: {CONFIG['EMAIL_RECIPIENTS']}")
log("")

# =============================================================================
# EMAIL FUNCTION
# =============================================================================

def send_test_email():
    """Send a test email to verify setup"""
    
    sender_email = os.environ.get("EMAIL_SENDER", "").strip()
    sender_password = os.environ.get("EMAIL_PASSWORD", "").strip()
    
    log("=" * 50)
    log("EMAIL SETUP CHECK")
    log("=" * 50)
    
    if not sender_email:
        log("❌ EMAIL_SENDER not set")
        return False
    else:
        log(f"✅ EMAIL_SENDER: {sender_email}")
    
    if not sender_password:
        log("❌ EMAIL_PASSWORD not set")
        return False
    else:
        log(f"✅ EMAIL_PASSWORD: {'*' * 4}...{'*' * 4} ({len(sender_password)} chars)")
    
    log("")
    log("Sending test email...")
    
    subject = f"🏠 天鑽監控測試 Test - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    body = f"""
==================================================
天鑽 The Regent - 系統測試成功！
System Test Successful!
==================================================

✅ 你嘅郵件設定正確！
✅ Your email setup is working!

監控設定 Settings:
- 座數 Towers: {CONFIG['TARGET_TOWERS']}
- 房數 Rooms: {CONFIG['TARGET_ROOMS']}
- 面積 Size: <{CONFIG['MAX_SIZE']} sq.ft.
- 頻率: Every 2 hours

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
            log("Connected. Logging in...")
            server.login(sender_email, sender_password)
            log("Logged in. Sending email...")
            server.sendmail(sender_email, CONFIG["EMAIL_RECIPIENTS"], msg.as_string())
        
        log("")
        log("✅✅✅ EMAIL SENT SUCCESSFULLY! ✅✅✅")
        log(f"Sent to: {CONFIG['EMAIL_RECIPIENTS']}")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        log("")
        log("❌❌❌ AUTHENTICATION FAILED ❌❌❌")
        log(f"Error: {e}")
        log("")
        log("Please check:")
        log("1. EMAIL_PASSWORD should be 16-char App Password WITHOUT spaces")
        log("2. Generate at: https://myaccount.google.com/apppasswords")
        return False
        
    except Exception as e:
        log("")
        log(f"❌❌❌ EMAIL FAILED ❌❌❌")
        log(f"Error: {type(e).__name__}: {e}")
        traceback.print_exc()
        return False


# =============================================================================
# CACHE FUNCTIONS
# =============================================================================

def save_data():
    """Save data files"""
    Path("data").mkdir(exist_ok=True)
    
    cache_data = {
        "last_run": datetime.now().isoformat(),
        "seen_ids": []
    }
    Path(CONFIG["CACHE_FILE"]).write_text(json.dumps(cache_data, indent=2))
    
    output_data = {
        "lastUpdate": datetime.now().isoformat(),
        "listings": []
    }
    Path(CONFIG["OUTPUT_FILE"]).write_text(json.dumps(output_data, ensure_ascii=False, indent=2))
    
    log(f"Data saved ✓")


# =============================================================================
# MAIN
# =============================================================================

def main():
    try:
        log("Starting...")
        log("")
        
        # Send test email
        send_test_email()
        
        log("")
        
        # Save data
        save_data()
        
        log("")
        log("=" * 50)
        log("Done! 完成！")
        log("=" * 50)
        
    except Exception as e:
        log(f"❌ ERROR: {type(e).__name__}: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
