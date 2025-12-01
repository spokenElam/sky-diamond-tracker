#!/usr/bin/env python3
"""
天鑽 The Regent - Property Listing Tracker
"""

import json
import smtplib
import os
import sys
import traceback
import urllib.request
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path

def log(msg):
    print(msg, flush=True)

log("=" * 60)
log("天鑽放盤追蹤器 The Regent Listing Tracker")
log(f"時間 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
log("=" * 60)
log("")

CONFIG = {
    "TARGET_TOWERS": [8, 9, 10, 11, 12, 13, 15, 16, 18],
    "MAX_SIZE": 600,
    "TARGET_ROOMS": [1, 2],
    "EMAIL_RECIPIENTS": ["acforgames9394@gmail.com"],
    "CACHE_FILE": "data/listings_cache.json",
    "OUTPUT_FILE": "data/listings.json",
}

log(f"篩選條件 Filter:")
log(f"  座數 Towers: {CONFIG['TARGET_TOWERS']}")
log(f"  房數 Rooms: {CONFIG['TARGET_ROOMS']}")  
log(f"  面積 Size: < {CONFIG['MAX_SIZE']} sq.ft.")
log("")

# =============================================================================
# SCRAPER
# =============================================================================

def fetch_url(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0',
        'Accept': 'text/html,application/xhtml+xml',
        'Accept-Language': 'zh-HK,zh;q=0.9,en;q=0.8',
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        log(f"  ❌ Fetch error: {e}")
        return None

def scrape_28hse():
    log("[28Hse] 抓取中 Scraping...")
    
    url = "https://www.28hse.com/utf8/buy/residential/a3/dg45/c22902"
    html = fetch_url(url)
    
    if not html:
        return []
    
    log(f"  ✅ Fetched {len(html)} bytes")
    
    listings = []
    
    # Pattern: 第X座 + 樓層 + 室 + 呎數 + 房數 + 價錢
    pattern = r'第(\d+)座[^第]*?(\d+|高|中|低)[樓層][^第]*?([A-H])室[^第]*?(\d{3,4})[呎尺][^第]*?(\d)[房室][^第]*?([\d\.]+)萬'
    
    matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
    
    for match in matches:
        try:
            tower = int(match[0])
            floor = match[1]
            unit = match[2].upper()
            size = int(match[3])
            rooms = int(match[4])
            price = int(float(match[5]) * 10000)
            
            # Apply filters
            if tower not in CONFIG["TARGET_TOWERS"]:
                continue
            if size >= CONFIG["MAX_SIZE"]:
                continue
            if rooms not in CONFIG["TARGET_ROOMS"]:
                continue
            
            listing = {
                "id": f"{tower}-{floor}-{unit}",
                "tower": tower,
                "floor": floor,
                "unit": unit,
                "size": size,
                "rooms": rooms,
                "price": price,
                "pricePerFt": price // size if size > 0 else 0,
                "source": "28hse",
                "sourceName": "28Hse",
                "sourceNameEn": "28Hse",
                "url": url,
                "scrapedAt": datetime.now().isoformat()
            }
            
            if not any(l["id"] == listing["id"] for l in listings):
                listings.append(listing)
                log(f"  📍 第{tower}座 {floor}樓 {unit}室 | {size}呎 {rooms}房 | ${price:,}")
                
        except:
            continue
    
    log(f"  Found: {len(listings)} listings")
    return listings

# =============================================================================
# EMAIL
# =============================================================================

def send_email(subject, body):
    sender = os.environ.get("EMAIL_SENDER", "").strip()
    password = os.environ.get("EMAIL_PASSWORD", "").strip()
    
    if not sender or not password:
        log("⚠️ Email not configured")
        return False
    
    try:
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = ", ".join(CONFIG["EMAIL_RECIPIENTS"])
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender, password)
            server.sendmail(sender, CONFIG["EMAIL_RECIPIENTS"], msg.as_string())
        
        log("✅ Email sent!")
        return True
        
    except smtplib.SMTPAuthenticationError:
        log("❌ Email AUTHENTICATION FAILED")
        log("   App Password must be 16 chars, no spaces")
        return False
    except Exception as e:
        log(f"❌ Email error: {e}")
        return False

def send_test_email():
    log("=" * 60)
    log("EMAIL TEST")
    log("=" * 60)
    
    sender = os.environ.get("EMAIL_SENDER", "").strip()
    password = os.environ.get("EMAIL_PASSWORD", "").strip()
    
    log(f"EMAIL_SENDER: {sender if sender else '❌ NOT SET'}")
    log(f"EMAIL_PASSWORD: {len(password)} chars" if password else "❌ NOT SET")
    
    if password and len(password) != 16:
        log(f"⚠️ Password is {len(password)} chars, should be 16!")
    
    subject = f"🏠 天鑽測試 Test - {datetime.now().strftime('%m/%d %H:%M')}"
    body = f"""
天鑽 The Regent - 測試成功！Test OK!

✅ Email 正常運作！

Dashboard: https://spokenelam.github.io/sky-diamond-tracker/

{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    return send_email(subject, body)

def send_listings_email(listings):
    if not listings:
        return
    
    subject = f"🏠 天鑽新放盤 ({len(listings)}) - {datetime.now().strftime('%m/%d %H:%M')}"
    
    lines = ["天鑽 The Regent - 新放盤!", "", f"發現 {len(listings)} 個:", ""]
    
    for i, l in enumerate(listings, 1):
        lines.append(f"【{i}】第{l['tower']}座 {l['floor']}樓 {l['unit']}室")
        lines.append(f"    {l['size']}呎 | {l['rooms']}房 | ${l['price']:,}")
        lines.append(f"    {l['url']}")
        lines.append("")
    
    lines.append("Dashboard: https://spokenelam.github.io/sky-diamond-tracker/")
    
    send_email(subject, "\n".join(lines))

# =============================================================================
# CACHE
# =============================================================================

def load_cache():
    try:
        path = Path(CONFIG["CACHE_FILE"])
        if path.exists():
            return set(json.loads(path.read_text()).get("seen_ids", []))
    except:
        pass
    return set()

def save_data(seen_ids, listings):
    Path("data").mkdir(exist_ok=True)
    
    Path(CONFIG["CACHE_FILE"]).write_text(json.dumps({
        "last_run": datetime.now().isoformat(),
        "seen_ids": list(seen_ids)
    }, indent=2))
    
    Path(CONFIG["OUTPUT_FILE"]).write_text(json.dumps({
        "lastUpdate": datetime.now().isoformat(),
        "listings": listings
    }, ensure_ascii=False, indent=2))
    
    log("💾 Data saved")

# =============================================================================
# MAIN
# =============================================================================

def main():
    try:
        seen_ids = load_cache()
        log(f"Cache: {len(seen_ids)} seen")
        log("")
        
        # Scrape
        listings = scrape_28hse()
        log("")
        log(f"📊 Total: {len(listings)} matching listings")
        
        # New listings
        new_listings = [l for l in listings if l["id"] not in seen_ids]
        log(f"🆕 New: {len(new_listings)}")
        log("")
        
        # Update cache
        for l in listings:
            seen_ids.add(l["id"])
        
        # Email
        if new_listings:
            log("📧 Sending new listings email...")
            send_listings_email(new_listings)
        else:
            send_test_email()
        
        log("")
        save_data(seen_ids, listings)
        
        log("")
        log("=" * 60)
        log("✅ Done!")
        log("=" * 60)
        
    except Exception as e:
        log(f"❌ ERROR: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
