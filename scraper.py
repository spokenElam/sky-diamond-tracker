#!/usr/bin/env python3
"""
天鑽 The Regent - Scraper v14 (Successful Version)
包含：自動清理資料、提取樓層室號、Email通知
"""

import json
import os
import smtplib
import urllib.request
import re
import time
from datetime import datetime
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- Configuration ---
CONFIG = {
    "CACHE_FILE": "data/listings_cache.json",
    "OUTPUT_FILE": "data/listings.json",
    # 這是正確的網址
    "URL": "https://www.28hse.com/buy/a3/dg45/c22902",
    "EMAIL_RECIPIENTS": ["acforgames9394@gmail.com"] 
}

def log(msg):
    print(msg, flush=True)

def fetch_url(url):
    log(f"🌍 Fetching: {url}")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml',
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

def scrape_28hse():
    log("--- Scraping 28Hse (v14 Cleaner) ---")
    html = fetch_url(CONFIG["URL"])
    if not html: return []

    if "Security Check" in html or "Just a moment" in html:
        log("🚨 Blocked by Cloudflare.")
        return []

    listings = []
    chunks = re.split(r'class="item', html)
    
    for chunk in chunks[1:]:
        try:
            tower = 0
            floor = "??"
            unit = "?"
            
            # 1. 嘗試抓取完整描述 (e.g. "13座 低層 C室")
            full_desc_match = re.search(r'unit_desc"[^>]*>\s*(.*?)\s*<', chunk)
            
            if full_desc_match:
                full_text = full_desc_match.group(1)
                
                # 抓座數
                t_match = re.search(r'(\d+)\s*座', full_text)
                if t_match: tower = int(t_match.group(1))
                
                # 抓樓層
                f_match = re.search(r'(低|中|高)層', full_text)
                if f_match: floor = f_match.group(1)
                
                # 抓室號
                u_match = re.search(r'([A-H])室', full_text, re.IGNORECASE)
                if u_match: unit = u_match.group(1).upper()
            
            # 後備座數抓取
            if tower == 0:
                t_match_backup = re.search(r'(?:第|Block)?\s*(\d+)\s*座', chunk)
                if t_match_backup: tower = int(t_match_backup.group(1))

            if tower == 0: continue

            # 2. 抓價錢
            price_match = re.search(r'(?:\$|售)\s*([\d,]+)\s*萬', chunk)
            if not price_match: continue
            price = int(price_match.group(1).replace(',', '')) * 10000

            # 3. 描述處理
            clean_text = re.sub(r'<[^>]+>', ' ', chunk)
            clean_text = clean_text.replace('property_item', '').replace('"', '').replace('>', '')
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            desc = clean_text[10:60] + "..."

            # 4. 連結
            link_match = re.search(r'href="([^"]+)"', chunk)
            link = link_match.group(1) if link_match else CONFIG["URL"]

            listing = {
                "id": f"28hse-{tower}-{price}",
                "tower": tower,
                "floor": floor,
                "unit": unit,
                "size": 0, "rooms": 0,
                "price": price, "pricePerFt": 0,
                "raw_desc": desc,
                "url": link,
                "source": "hse28",
                "sourceName": "28Hse",
                "scrapedAt": datetime.now().isoformat()
            }
            
            if not any(l["id"] == listing["id"] for l in listings):
                listings.append(listing)
                log(f"   ✅ Found: T{tower} {floor} {unit}室 ${price/10000}萬")

        except: continue
            
    return listings

def send_email(new_listings):
    sender = os.environ.get("EMAIL_SENDER")
    password = os.environ.get("EMAIL_PASSWORD")
    if not sender or not password: return

    subject = f"🔥 天鑽新盤通報 ({len(new_listings)})"
    lines = ["最新放盤:", ""]
    for l in new_listings:
        loc = f"{l['floor']}層 {l['unit']}室" if l['unit'] != "?" else ""
        lines.append(f"📍 第 {l['tower']} 座 {loc} | ${l['price']/10000:,.0f}萬")
        lines.append(f"   {l['url']}")
        lines.append("")
    lines.append("Dashboard: https://spokenelam.github.io/sky-diamond-tracker/")
    
    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = ", ".join(CONFIG["EMAIL_RECIPIENTS"])
    msg['Subject'] = subject
    msg.attach(MIMEText("\n".join(lines), 'plain', 'utf-8'))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender, password)
            server.sendmail(sender, CONFIG["EMAIL_RECIPIENTS"], msg.as_string())
        log("📧 Email sent.")
    except: pass

def main():
    log("🚀 Starting Scraper v14 (Restored)...")
    
    seen_ids = set()
    try:
        if Path(CONFIG["CACHE_FILE"]).exists():
            data = json.loads(Path(CONFIG["CACHE_FILE"]).read_text())
            seen_ids = set(data.get("seen_ids", []))
    except: pass

    current_listings = scrape_28hse()
    log(f"📊 Total Found: {len(current_listings)}")
    
    current_listings.sort(key=lambda x: (x['tower'], x['price']))

    new_listings = [l for l in current_listings if l["id"] not in seen_ids]
    
    current_ids = list(seen_ids)
    for l in current_listings:
        if l["id"] not in current_ids:
            current_ids.append(l["id"])

    if new_listings:
        send_email(new_listings)

    Path("data").mkdir(exist_ok=True)
    output_data = {"lastUpdate": datetime.now().isoformat(), "listings": current_listings}
    Path(CONFIG["OUTPUT_FILE"]).write_text(json.dumps(output_data, ensure_ascii=False, indent=2))
    
    cache_data = {"last_run": datetime.now().isoformat(), "seen_ids": current_ids}
    Path(CONFIG["CACHE_FILE"]).write_text(json.dumps(cache_data, indent=2))
    log("💾 Data saved.")

if __name__ == "__main__":
    main()
