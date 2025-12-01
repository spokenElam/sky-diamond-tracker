#!/usr/bin/env python3
"""
天鑽 The Regent - Scraper v10 (Direct Estate ID + No PropertyHK)
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
    "TARGET_TOWERS": [8, 9, 10, 11, 12, 13, 15, 16, 18],
    "CACHE_FILE": "data/listings_cache.json",
    "OUTPUT_FILE": "data/listings.json",
    # [修正] 使用天鑽專屬 ID (16716) 直連頁面，確保一定係天鑽
    "URL": "https://www.28hse.com/buy/residential/property/16716"
}

def log(msg):
    print(msg, flush=True)

def fetch_url(url):
    log(f"🌍 Fetching: {url}")
    # 模擬簡單瀏覽器
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-HK,zh;q=0.9,en;q=0.8',
        'Referer': 'https://www.28hse.com/',
        'Cookie': 'locale=zh-hk'
    }
    try:
        # 隨機等待 2 秒，扮真人
        time.sleep(2)
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        log(f"❌ Fetch error: {e}")
        return None

def scrape_28hse():
    log("--- Scraping 28Hse (Direct Estate ID Mode) ---")
    
    html = fetch_url(CONFIG["URL"])
    if not html: return []

    # Debug: 印出標題確認係咪天鑽頁面
    title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
    if title_match:
        log(f"   Page Title: {title_match.group(1)}")

    listings = []
    
    # 策略：暴力搜尋整頁文字
    # 尋找： (第/Block/T)? + 數字 + 座 ......(中間隨便隔 300字)...... $ + 數字 + 萬
    
    # regex: 
    # (?:第|Block|T)?  -> 前面可能有 "第" 字，也可能無 (例如 "13座")
    # \s*(\d+)\s*座    -> 找座號
    
    pattern = r'(?:第|Block|T)?\s*(\d+)\s*座.{0,300}?\$\s*([\d,]+)\s*萬'
    
    # 移除換行符號，變成一行過方便搜尋
    clean_html = html.replace('\n', ' ').replace('\r', '')
    
    matches = re.finditer(pattern, clean_html)
    
    for match in matches:
        try:
            tower = int(match.group(1))
            price_str = match.group(2).replace(',', '')
            price = int(price_str) * 10000
            
            # 篩選座數
            if tower not in CONFIG["TARGET_TOWERS"]:
                continue

            # 建立 ID
            listing_id = f"28hse-{tower}-{price}"
            
            # 抓取描述 (前後文)
            raw_text = match.group(0)
            # 移除 HTML tag
            clean_desc = re.sub(r'<[^>]+>', ' ', raw_text)
            clean_desc = re.sub(r'\s+', ' ', clean_desc).strip()
            desc = clean_desc[:60] + "..."

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

# =============================================================================
# MAIN
# =============================================================================
def main():
    log("🚀 Starting Scraper v10...")
    
    all_listings = scrape_28hse()
    
    log(f"📊 Total Listings: {len(all_listings)}")
    
    # Sort
    all_listings.sort(key=lambda x: x['price'])

    # Save
    Path("data").mkdir(exist_ok=True)
    output_data = {
        "lastUpdate": datetime.now().isoformat(),
        "listings": all_listings
    }
    Path(CONFIG["OUTPUT_FILE"]).write_text(json.dumps(output_data, ensure_ascii=False, indent=2))
    log("💾 Data saved.")

if __name__ == "__main__":
    main()
