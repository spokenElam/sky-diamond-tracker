#!/usr/bin/env python3
"""
天鑽 The Regent - Scraper v15 (28Hse + Ricacorp)
嘗試加入利嘉閣 (Ricacorp) 作為第二來源
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
    "CACHE_FILE": "data/listings_cache.json",
    "OUTPUT_FILE": "data/listings.json",
    "EMAIL_RECIPIENTS": ["acforgames9394@gmail.com"],
    # 網址設定
    "URL_28HSE": "https://www.28hse.com/buy/a3/dg45/c22902",
    "URL_RICA": "https://www.ricacorp.com/zh-hk/property/list/buy/%E5%A4%A9%E9%91%BD-estate-%E5%A4%A7%E5%9F%94%E5%8D%8A%E5%B1%B1-hma-hk"
}

def log(msg):
    print(msg, flush=True)

def get_random_headers():
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Version/17.2 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0'
    ]
    return {
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Cookie': 'locale=zh-hk'
    }

def fetch_url(url):
    log(f"🌍 Fetching: {url}")
    try:
        time.sleep(random.uniform(2, 4)) # 休息耐少少，避開封鎖
        req = urllib.request.Request(url, headers=get_random_headers())
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        log(f"❌ Fetch error ({url}): {e}")
        return None

# =============================================================================
# 1. 28Hse Scraper (原本成功的邏輯)
# =============================================================================
def scrape_28hse():
    log("--- Scraping 28Hse ---")
    html = fetch_url(CONFIG["URL_28HSE"])
    if not html: return []
    if "Security Check" in html: return []

    listings = []
    chunks = re.split(r'class="item', html)
    
    for chunk in chunks[1:]:
        try:
            tower = 0; floor = "??"; unit = "?"
            
            # 抓座數/樓層/室
            full_desc_match = re.search(r'unit_desc"[^>]*>\s*(.*?)\s*<', chunk)
            if full_desc_match:
                full_text = full_desc_match.group(1)
                t_match = re.search(r'(\d+)\s*座', full_text)
                if t_match: tower = int(t_match.group(1))
                f_match = re.search(r'(低|中|高)層', full_text)
                if f_match: floor = f_match.group(1)
                u_match = re.search(r'([A-H])室', full_text, re.IGNORECASE)
                if u_match: unit = u_match.group(1).upper()
            
            # 後備座數
            if tower == 0:
                t_match_backup = re.search(r'(?:第|Block)?\s*(\d+)\s*座', chunk)
                if t_match_backup: tower = int(t_match_backup.group(1))

            if tower == 0: continue

            # 抓價錢
            price_match = re.search(r'(?:\$|售)\s*([\d,]+)\s*萬', chunk)
            if not price_match: continue
            price = int(price_match.group(1).replace(',', '')) * 10000

            # 描述
            clean_text = re.sub(r'<[^>]+>', ' ', chunk)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            desc = clean_text[10:60] + "..."
            
            # 連結
            link_match = re.search(r'href="([^"]+)"', chunk)
            link = link_match.group(1) if link_match else CONFIG["URL_28HSE"]

            listing = {
                "id": f"28hse-{tower}-{price}",
                "tower": tower, "floor": floor, "unit": unit,
                "price": price, "raw_desc": desc, "url": link,
                "source": "hse28", "sourceName": "28Hse",
                "scrapedAt": datetime.now().isoformat()
            }
            if not any(l["id"] == listing["id"] for l in listings):
                listings.append(listing)
                log(f"   ✅ 28Hse: T{tower} {floor} {unit} ${price/10000}萬")
        except: continue
    return listings

# =============================================================================
# 2. Ricacorp (利嘉閣) Scraper
# =============================================================================
def scrape_ricacorp():
    log("--- Scraping Ricacorp ---")
    html = fetch_url(CONFIG["URL_RICA"])
    if not html: return []
    
    listings = []
    # 利嘉閣通常將資料放係 class="property-card"
    chunks = re.split(r'class="property-card', html)
    
    for chunk in chunks[1:]:
        try:
            # 抓座數 (利嘉閣格式: 第8座)
            tower = 0
            t_match = re.search(r'第\s*(\d+)\s*座', chunk)
            if t_match: tower = int(t_match.group(1))
            else: continue # 找不到座數就 skip
            
            # 抓樓層 (通常係: 高層)
            floor = "??"
            f_match = re.search(r'(高|中|低)層', chunk)
            if f_match: floor = f_match.group(1)
            
            # 抓室號
            unit = "?"
            u_match = re.search(r'([A-H])室', chunk)
            if u_match: unit = u_match.group(1)
            
            # 抓價錢 ($ 638 萬)
            price = 0
            p_match = re.search(r'\$\s*([\d,]+)\s*萬', chunk)
            if p_match: price = int(p_match.group(1).replace(',', '')) * 10000
            else: continue

            # 抓連結
            link = CONFIG["URL_RICA"]
            l_match = re.search(r'href="([^"]+)"', chunk)
            if l_match: link = "https://www.ricacorp.com" + l_match.group(1)
            
            # 描述
            desc = f"第{tower}座 (利嘉閣盤源)"

            listing = {
                "id": f"rica-{tower}-{price}",
                "tower": tower, "floor": floor, "unit": unit,
                "price": price, "raw_desc": desc, "url": link,
                "source": "centanet", # 用橙色標籤 (借用 index.html 現有 class)
                "sourceName": "利嘉閣",
                "scrapedAt": datetime.now().isoformat()
            }
            if not any(l["id"] == listing["id"] for l in listings):
                listings.append(listing)
                log(f"   ✅ Ricacorp: T{tower} ${price/10000}萬")

        except: continue
        
    return listings

# --- Main ---
def main():
    log("🚀 Starting Scraper v15 (Multi-Source)...")
    
    seen_ids = set()
    try:
        if Path(CONFIG["CACHE_FILE"]).exists():
            data = json.loads(Path(CONFIG["CACHE_FILE"]).read_text())
            seen_ids = set(data.get("seen_ids", []))
    except: pass

    all_listings = []
    
    # 執行所有 Scraper
    all_listings.extend(scrape_28hse())   # 28Hse
    all_listings.extend(scrape_ricacorp()) # 利嘉閣
    
    log(f"📊 Total Found: {len(all_listings)}")
    
    # Sort
    all_listings.sort(key=lambda x: (x['tower'], x['price']))

    # Email Logic
    new_listings = [l for l in all_listings if l["id"] not in seen_ids]
    
    # Email Function (Condensed)
    sender = os.environ.get("EMAIL_SENDER")
    password = os.environ.get("EMAIL_PASSWORD")
    if new_listings and sender and password:
        subject = f"🔥 天鑽新盤通報 ({len(new_listings)})"
        lines = ["最新放盤 (包含利嘉閣/28Hse):", ""]
        for l in new_listings:
            loc = f"{l['floor']}層 {l['unit']}室" if l['unit'] != "?" else ""
            lines.append(f"📍 第 {l['tower']} 座 {loc} | ${l['price']/10000:,.0f}萬 | {l['sourceName']}")
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

    # Save Data
    current_ids = list(seen_ids)
    for l in all_listings:
        if l["id"] not in current_ids:
            current_ids.append(l["id"])
            
    Path("data").mkdir(exist_ok=True)
    output_data = {"lastUpdate": datetime.now().isoformat(), "listings": all_listings}
    Path(CONFIG["OUTPUT_FILE"]).write_text(json.dumps(output_data, ensure_ascii=False, indent=2))
    
    cache_data = {"last_run": datetime.now().isoformat(), "seen_ids": current_ids}
    Path(CONFIG["CACHE_FILE"]).write_text(json.dumps(cache_data, indent=2))
    log("💾 Data saved.")

if __name__ == "__main__":
    main()
