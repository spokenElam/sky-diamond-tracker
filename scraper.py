#!/usr/bin/env python3
"""
天鑽 The Regent - Scraper v13 (No Filters + Email Notification)
全接收模式：不分座數，只要是天鑽放盤，有新野即刻 Email。
"""

import json
import os
import smtplib
import urllib.request
import re
import time
import random
from datetime import datetime
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- Configuration ---
CONFIG = {
    # 移除 TARGET_TOWERS，全部都係目標
    "CACHE_FILE": "data/listings_cache.json",
    "OUTPUT_FILE": "data/listings.json",
    "URL": "https://www.28hse.com/buy/a3/dg45/c22902",
    # Email 接收者
    "EMAIL_RECIPIENTS": ["acforgames9394@gmail.com"] 
}

def log(msg):
    print(msg, flush=True)

# --- Network ---
def fetch_url(url):
    log(f"🌍 Fetching: {url}")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Cookie': 'locale=zh-hk'
    }
    try:
        time.sleep(2)
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        log(f"❌ Fetch error: {e}")
        return None

# --- Scraper ---
def scrape_28hse():
    log("--- Scraping 28Hse (All Towers) ---")
    html = fetch_url(CONFIG["URL"])
    if not html: return []

    # Check blocked
    if "Security Check" in html or "Just a moment" in html:
        log("🚨 Blocked by Cloudflare.")
        return []

    listings = []
    chunks = re.split(r'class="item', html)
    
    for chunk in chunks[1:]:
        try:
            # 1. 抓座數 (任何數字+座)
            # 優先試 unit_desc (你截圖個位置)
            tower_match = re.search(r'unit_desc"[^>]*>\s*(\d+)\s*座', chunk)
            if not tower_match:
                # 後備通用抓法
                tower_match = re.search(r'(?:第|Block)?\s*(\d+)\s*座', chunk)
            
            if not tower_match: continue
            
            tower = int(tower_match.group(1))
            
            # 2. 抓價錢
            price_match = re.search(r'(?:\$|售)\s*([\d,]+)\s*萬', chunk)
            if not price_match: continue
            
            price = int(price_match.group(1).replace(',', '')) * 10000

            # 3. 抓描述 & 連結
            clean_text = re.sub(r'<[^>]+>', ' ', chunk)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            desc = f"第{tower}座 " + clean_text[:40] + "..."
            
            link_match = re.search(r'href="([^"]+)"', chunk)
            link = link_match.group(1) if link_match else CONFIG["URL"]

            listing = {
                "id": f"28hse-{tower}-{price}",
                "tower": tower,
                "price": price,
                "raw_desc": desc,
                "url": link,
                "scrapedAt": datetime.now().isoformat(),
                # 為了兼容 index.html，補返呢D欄位
                "floor": "??", "unit": "?", "size": 0, "rooms": 0, "pricePerFt": 0,
                "source": "hse28", "sourceName": "28Hse"
            }
            
            # 去重
            if not any(l["id"] == listing["id"] for l in listings):
                listings.append(listing)
                log(f"   ✅ Found: T{tower} ${price/10000}萬")

        except: continue
            
    return listings

# --- Email ---
def send_email(new_listings):
    sender = os.environ.get("EMAIL_SENDER")
    password = os.environ.get("EMAIL_PASSWORD")
    
    if not sender or not password:
        log("⚠️ Email secrets not set. Skipping email.")
        return

    subject = f"🔥 天鑽新消息 ({len(new_listings)}) - {datetime.now().strftime('%H:%M')}"
    
    body_lines = ["天鑽 The Regent - 最新放盤監控", "", f"發現 {len(new_listings)} 個新/變動放盤:", ""]
    
    for l in new_listings:
        body_lines.append(f"📍 第 {l['tower']} 座 | ${l['price']/10000:,.0f}萬")
        body_lines.append(f"   {l['raw_desc']}")
        body_lines.append(f"   🔗 {l['url']}")
        body_lines.append("-" * 20)
        
    body_lines.append("\n查看 Dashboard: https://spokenelam.github.io/sky-diamond-tracker/")
    
    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = ", ".join(CONFIG["EMAIL_RECIPIENTS"])
    msg['Subject'] = subject
    msg.attach(MIMEText("\n".join(body_lines), 'plain', 'utf-8'))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender, password)
            server.sendmail(sender, CONFIG["EMAIL_RECIPIENTS"], msg.as_string())
        log("📧 Email sent successfully!")
    except Exception as e:
        log(f"❌ Email failed: {e}")

# --- Main ---
def main():
    log("🚀 Starting Scraper v13 (No Filter)...")
    
    # Load Cache
    seen_ids = set()
    try:
        if Path(CONFIG["CACHE_FILE"]).exists():
            data = json.loads(Path(CONFIG["CACHE_FILE"]).read_text())
            seen_ids = set(data.get("seen_ids", []))
    except: pass

    # Scrape
    current_listings = scrape_28hse()
    log(f"📊 Total Found: {len(current_listings)}")
    
    # Identify New
    new_listings = [l for l in current_listings if l["id"] not in seen_ids]
    log(f"🆕 New Items: {len(new_listings)}")

    # Update Cache IDs
    current_ids = list(seen_ids)
    for l in current_listings:
        if l["id"] not in current_ids:
            current_ids.append(l["id"])

    # Send Email if NEW items found
    if new_listings:
        send_email(new_listings)
    else:
        log("💤 No new items, no email.")

    # Save Files
    Path("data").mkdir(exist_ok=True)
    
    # Listings for Website
    output_data = {
        "lastUpdate": datetime.now().isoformat(),
        "listings": current_listings
    }
    Path(CONFIG["OUTPUT_FILE"]).write_text(json.dumps(output_data, ensure_ascii=False, indent=2))
    
    # Cache
    cache_data = {
        "last_run": datetime.now().isoformat(),
        "seen_ids": current_ids
    }
    Path(CONFIG["CACHE_FILE"]).write_text(json.dumps(cache_data, indent=2))
    log("💾 Data saved.")

if __name__ == "__main__":
    main()
