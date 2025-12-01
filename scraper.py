#!/usr/bin/env python3
"""
天鑽 The Regent - Scraper v8 (Search Query + Proximity Regex)
"""

import json
import urllib.request
import urllib.parse
import re
import random
import time
from datetime import datetime
from pathlib import Path

# --- Configuration ---
CONFIG = {
    "TARGET_TOWERS": [8, 9, 10, 11, 12, 13, 15, 16, 18],
    "CACHE_FILE": "data/listings_cache.json",
    "OUTPUT_FILE": "data/listings.json",
}

def log(msg):
    print(msg, flush=True)

def get_headers():
    agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/123.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15',
    ]
    return {
        'User-Agent': random.choice(agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Cookie': 'locale=zh-hk', # 強制中文
    }

def fetch_url(url):
    log(f"🌍 Fetching: {url}")
    try:
        time.sleep(random.uniform(2, 4)) # 休息久一點
        req = urllib.request.Request(url, headers=get_headers())
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        log(f"❌ Error fetching {url}: {e}")
        return None

# =============================================================================
# 1. 28Hse (Search Query Mode)
# =============================================================================
def scrape_28hse():
    log("--- Scraping 28Hse (Search Mode) ---")
    
    # 使用搜尋 URL (天鑽 encoded)
    # q=天鑽
    search_url = "https://www.28hse.com/buy?q=%E5%A4%A9%E9%91%BD"
    
    html = fetch_url(search_url)
    if not html: return []

    # Check Title
    title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
    log(f"   Page Title: {title_match.group(1) if title_match else 'Unknown'}")

    listings = []
    
    # 策略：不再切割區塊，直接找所有 "座" 的位置
    # 然後往後找 200 個字元內的 "價錢"
    
    # 1. 找出所有 "X座" 的位置
    # pattern: 數字 + 座 (忽略前面的 第/Block)
    # 使用 finditer 獲取位置
    tower_iter = re.finditer(r'(?:第|Block|T)?\s*(\d+)\s*座', html)
    
    for match in tower_iter:
        try:
            tower = int(match.group(1))
            start_pos = match.end()
            
            # 只處理目標座數
            if tower not in CONFIG["TARGET_TOWERS"]:
                continue
                
            # 在這個 "座" 之後的 300 個字元內找價錢
            # 這是 "Proximity Search" (鄰近搜尋)
            search_window = html[start_pos : start_pos + 300]
            
            # 找價錢 ($xxx萬 or 售xxx萬)
            price_match = re.search(r'(?:\$|售)\s*([\d,]+)\s*萬', search_window)
            
            if price_match:
                price = int(price_match.group(1).replace(',', '')) * 10000
                
                # 建立 ID
                listing_id = f"28hse-{tower}-{price}"
                
                # 嘗試在 window 內找描述
                clean_text = re.sub(r'<[^>]+>', ' ', search_window)
                desc = f"第{tower}座 " + clean_text[:30].strip() + "..."

                # 嘗試找 Link (通常在前面)
                # 往回找 href
                link = search_url # Default
                
                listing = {
                    "id": listing_id,
                    "tower": tower,
                    "floor": "??", "unit": "?", "size": 0, "rooms": 0,
                    "price": price, "pricePerFt": 0,
                    "raw_desc": desc,
                    "url": link,
                    "source": "hse28",
                    "sourceName": "28Hse",
                    "scrapedAt": datetime.now().isoformat()
                }
                
                if not any(l["id"] == listing["id"] for l in listings):
                    listings.append(listing)
                    log(f"   ✅ Found: T{tower} ${price/10000}萬")
        except:
            continue
            
    return listings

# =============================================================================
# 2. Property.hk (Robust Regex)
# =============================================================================
def scrape_property_hk():
    log("--- Scraping Property.hk ---")
    url = "https://www.property.hk/buy/search/%E5%A4%A9%E9%91%BD/"
    html = fetch_url(url)
    if not html: return []
    
    listings = []
    
    # 同樣使用鄰近搜尋法
    tower_iter = re.finditer(r'第\s*(\d+)\s*座', html)
    
    for match in tower_iter:
        try:
            tower = int(match.group(1))
            if tower not in CONFIG["TARGET_TOWERS"]: continue
            
            start_pos = match.end()
            search_window = html[start_pos : start_pos + 300]
            
            price_match = re.search(r'(\d{3,5})\s*萬', search_window)
            
            if price_match:
                price = int(price_match.group(1)) * 10000
                
                listing = {
                    "id": f"phk-{tower}-{price}",
                    "tower": tower,
                    "floor": "??", "unit": "?", "size": 0, "rooms": 0,
                    "price": price, "pricePerFt": 0,
                    "raw_desc": f"第{tower}座 (Property.hk)",
                    "url": url,
                    "source": "hkp",
                    "sourceName": "Property.hk",
                    "scrapedAt": datetime.now().isoformat()
                }
                
                if not any(l["id"] == listing["id"] for l in listings):
                    listings.append(listing)
                    log(f"   ✅ Found: T{tower} ${price/10000}萬")
        except: continue
            
    return listings

# =============================================================================
# MAIN
# =============================================================================
def main():
    log("🚀 Starting Scraper v8 (Search Query Mode)...")
    all_listings = []
    
    all_listings.extend(scrape_28hse())
    all_listings.extend(scrape_property_hk())
    
    log(f"📊 Total Combined Listings: {len(all_listings)}")
    
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
