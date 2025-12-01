#!/usr/bin/env python3
"""
天鑽 The Regent - Scraper v3 (Robust & Debug Mode)
"""

import json
import os
import sys
import traceback
import urllib.request
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
    # 這是你的目標 URL (天鑽)
    "URL": "https://www.28hse.com/buy/residential/property/16716" 
}

# --- Helpers ---
def log(msg):
    print(msg, flush=True)

def get_random_user_agent():
    agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0'
    ]
    return random.choice(agents)

# --- Scraper Logic ---
def fetch_html(url):
    log(f"🌍 Fetching URL: {url}")
    
    headers = {
        'User-Agent': get_random_user_agent(),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-HK,zh;q=0.9,en;q=0.8',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'Referer': 'https://www.28hse.com/',
        'Cookie': 'locale=zh-hk' # 嘗試強制中文
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        # 隨機延遲，看起來像真人
        time.sleep(2) 
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            return html
    except Exception as e:
        log(f"❌ Network Error: {e}")
        return None

def parse_listings(html):
    listings = []
    
    # 1. 檢查是否被擋 (Debug)
    title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
    page_title = title_match.group(1) if title_match else "No Title Found"
    log(f"📄 Page Title found: [{page_title}]")
    
    if "Security" in page_title or "Just a moment" in page_title or "Cloudflare" in page_title:
        log("⚠️ WARNING: GitHub IP might be blocked by Cloudflare.")
        return []

    # 2. 嘗試用簡單暴力的方式抓取 (Pattern A: 尋找包含 '座' 和 '萬' 的區塊)
    # 這種寫法會忽略 HTML 結構，直接在文字流中尋找 "數字+座 ... 數字+萬"
    # 例如: "8座 ... $800萬"
    
    log("🔍 Trying extraction pattern...")
    
    # 移除 HTML 標籤，轉成純文字來分析，減少結構干擾
    clean_text = re.sub(r'<[^>]+>', ' ', html)
    clean_text = re.sub(r'\s+', ' ', clean_text)
    
    # Pattern: 找尋 "第X座" 或 "X座"，後面跟著價錢
    # 容許中間間隔 100 個字元
    pattern = r'(\d+)\s*座.{0,100}?\$?([\d,]+(?:\.\d+)?)\s*萬'
    
    matches = re.findall(pattern, clean_text)
    log(f"   Found {len(matches)} raw matches")

    for match in matches:
        try:
            tower_str = match[0]
            price_str = match[1].replace(',', '')
            
            tower = int(tower_str)
            price = int(float(price_str) * 10000)
            
            # 過濾座數
            if tower not in CONFIG["TARGET_TOWERS"]:
                continue
                
            # 建立 ID
            listing_id = f"{tower}-{price}"
            
            listing = {
                "id": listing_id,
                "tower": tower,
                "floor": "??", # 寬鬆模式不強求樓層
                "unit": "?",
                "size": 0,
                "rooms": 0,
                "price": price,
                "pricePerFt": 0,
                "raw_desc": f"第{tower}座 (HK${price_str}萬)",
                "url": CONFIG["URL"],
                "source": "28hse",
                "sourceName": "28Hse",
                "scrapedAt": datetime.now().isoformat()
            }
            
            # 去重
            if not any(l["id"] == listing["id"] for l in listings):
                listings.append(listing)
                log(f"   ✅ Matched: Tower {tower} @ ${price_str}萬")

        except Exception as e:
            continue

    return listings

# --- Main Execution ---
def main():
    log("🚀 Starting Scraper v3...")
    
    # Load Cache
    seen_ids = set()
    try:
        if Path(CONFIG["CACHE_FILE"]).exists():
            data = json.loads(Path(CONFIG["CACHE_FILE"]).read_text())
            seen_ids = set(data.get("seen_ids", []))
    except:
        pass

    # Fetch & Parse
    html = fetch_html(CONFIG["URL"])
    current_listings = []
    
    if html:
        current_listings = parse_listings(html)
    else:
        log("❌ No HTML content retrieved.")

    log(f"📊 Total Listings Found: {len(current_listings)}")

    # Update Data Files
    # 確保資料夾存在
    Path("data").mkdir(exist_ok=True)
    
    # 1. Update JSON for Website (總是覆蓋，確保網站顯示最新)
    output_data = {
        "lastUpdate": datetime.now().isoformat(),
        "listings": current_listings
    }
    Path(CONFIG["OUTPUT_FILE"]).write_text(json.dumps(output_data, ensure_ascii=False, indent=2))
    
    # 2. Update Cache (保留歷史紀錄)
    new_ids = [l["id"] for l in current_listings]
    seen_ids.update(new_ids)
    
    cache_data = {
        "last_run": datetime.now().isoformat(),
        "seen_ids": list(seen_ids)
    }
    Path(CONFIG["CACHE_FILE"]).write_text(json.dumps(cache_data, indent=2))
    
    log("💾 Data saved successfully.")

    # Email Logic (Optional: 只有在真的有新盤時才在這裡加)
    # ... (保持你的 YAML 處理 email 或在此處加入，目前先專注於修復抓取)

if __name__ == "__main__":
    main()
