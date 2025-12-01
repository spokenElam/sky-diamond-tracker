#!/usr/bin/env python3
"""
天鑽 The Regent - Scraper v11 (No '座' Required + Full Tower List)
針對性：只要見到 8-18 數字 + 價錢，即刻抓取，無視格式！
"""

import json
import urllib.request
import re
from datetime import datetime
from pathlib import Path
import time
import random

# --- Configuration ---
CONFIG = {
    # 你指定的所有座數 (Towers)
    "TARGET_TOWERS": [8, 9, 10, 11, 12, 13, 15, 16, 18],
    "CACHE_FILE": "data/listings_cache.json",
    "OUTPUT_FILE": "data/listings.json",
    # 回歸最穩陣的大埔半山區網址 (包含天鑽)
    "URL": "https://www.28hse.com/utf8/buy/residential/a3/dg45/c22902"
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
    log("--- Scraping 28Hse (Flexible Mode) ---")
    log(f"🎯 Target Towers: {CONFIG['TARGET_TOWERS']}")
    
    html = fetch_url(CONFIG["URL"])
    if not html: return []

    listings = []
    
    # 策略：極度寬鬆 Regex
    # 1. (?:第|Block|T)? -> 前面可以有 第/Block/T，也可以沒有
    # 2. \s*(\d+)        -> 重點！抓取數字 (Group 1)
    # 3. (?:\s*座)?      -> 後面可以有 "座"，也可以沒有 (配合你話 "座都唔要")
    # 4. .{0,300}?       -> 中間隔 300 字
    # 5. \$              -> 直到見到價錢符號
    
    pattern = r'(?:第|Block|T)?\s*(\d+)(?:\s*座)?.{0,300}?\$\s*([\d,]+)\s*萬'
    
    clean_html = html.replace('\n', ' ').replace('\r', '')
    matches = re.finditer(pattern, clean_html)
    
    for match in matches:
        try:
            tower_str = match.group(1)
            price_str = match.group(2).replace(',', '')
            
            tower = int(tower_str)
            price = int(price_str) * 10000
            
            # 【關鍵過濾】
            # 因為 Regex 太寬鬆 (連 "2房" 嘅 "2" 都會抓到)，
            # 所以必須檢查個數字係咪你想要嘅座數 (8,9,10...18)
            if tower not in CONFIG["TARGET_TOWERS"]:
                continue

            # 建立 ID
            listing_id = f"28hse-{tower}-{price}"
            
            # 抓取前後文做描述
            raw_text = match.group(0)
            clean_desc = re.sub(r'<[^>]+>', ' ', raw_text)
            clean_desc = re.sub(r'\s+', ' ', clean_desc).strip()
            desc = f"第{tower}座 " + clean_desc[:40] + "..."

            listing = {
                "id": listing_id,
                "tower": tower,
                "floor": "??", 
                "unit": "?", 
                "size": 0, 
                "rooms": 0,
                "price": price, 
                "pricePerFt": 0,
                "raw_desc": desc,
                "url": CONFIG["URL"],
                "source": "hse28",
                "sourceName": "28Hse",
                "scrapedAt": datetime.now().isoformat()
            }
            
            if not any(l["id"] == listing["id"] for l in listings):
                listings.append(listing)
                log(f"   ✅ Found: T{tower} ${price/10000}萬")
                
        except Exception as e:
            continue
            
    return listings

def main():
    log("🚀 Starting Scraper v11...")
    all_listings = scrape_28hse()
    log(f"📊 Total Listings: {len(all_listings)}")
    
    all_listings.sort(key=lambda x: x['price'])

    Path("data").mkdir(exist_ok=True)
    output_data = {
        "lastUpdate": datetime.now().isoformat(),
        "listings": all_listings
    }
    Path(CONFIG["OUTPUT_FILE"]).write_text(json.dumps(output_data, ensure_ascii=False, indent=2))
    log("💾 Data saved.")

if __name__ == "__main__":
    main()
