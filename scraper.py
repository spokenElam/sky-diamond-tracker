#!/usr/bin/env python3
"""
天鑽 The Regent - Scraper v4 (Fix URL & Loose Regex)
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
    # [修正] 改回原本有效的搜尋結果連結 (天鑽專頁)
    "URL": "https://www.28hse.com/utf8/buy/residential/a3/dg45/c22902"
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
        'Referer': 'https://www.28hse.com/',
        'Cookie': 'locale=zh-hk'
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        time.sleep(2) 
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            return html
    except Exception as e:
        log(f"❌ Network Error: {e}")
        # 如果是 404，印出更多資訊
        if hasattr(e, 'code'):
            log(f"   Status Code: {e.code}")
        return None

def parse_listings(html):
    listings = []
    
    # 1. 檢查標題
    title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
    page_title = title_match.group(1) if title_match else "No Title Found"
    log(f"📄 Page Title: [{page_title}]")
    
    if "Security" in page_title or "Just a moment" in page_title:
        log("⚠️ WARNING: GitHub IP blocked by Cloudflare.")
        return []

    # 2. 寬鬆抓取 (Pattern: 第X座 ... 價錢)
    log("🔍 Extracting data...")
    
    # 清理 HTML 標籤，變成純文字
    clean_text = re.sub(r'<[^>]+>', ' ', html)
    clean_text = re.sub(r'\s+', ' ', clean_text) # 把多餘空白變成單一空白
    
    # 抓取邏輯：找 "第X座" 或 "X座"，後面跟著 "數字+萬"
    # 例如: "第 8 座 ... $ 638 萬"
    # Group 1: 座數
    # Group 2: 價錢
    pattern = r'第?\s*(\d+)\s*座.{0,150}?\$?([\d,]+(?:\.\d+)?)\s*萬'
    
    matches = re.findall(pattern, clean_text)
    log(f"   Found {len(matches)} potential matches")

    for match in matches:
        try:
            tower_str = match[0]
            price_str = match[1].replace(',', '').replace(' ', '')
            
            tower = int(tower_str)
            price = int(float(price_str) * 10000)
            
            # 過濾
            if tower not in CONFIG["TARGET_TOWERS"]:
                continue
                
            # 建立資料
            # 因為是從純文字抓，沒有準確的 URL 對應到該盤，所以用主搜尋頁面 URL
            listing_id = f"{tower}-{price}" 
            
            listing = {
                "id": listing_id,
                "tower": tower,
                "floor": "??", 
                "unit": "?",
                "size": 0,    # 暫時設為 0，避免 regex 錯誤
                "rooms": 0,
                "price": price,
                "pricePerFt": 0,
                "raw_desc": f"第{tower}座 (HK${price_str}萬)",
                "url": CONFIG["URL"],
                "source": "28hse",
                "sourceName": "28Hse",
                "scrapedAt": datetime.now().isoformat()
            }
            
            # 去除重複
            if not any(l["id"] == listing["id"] for l in listings):
                listings.append(listing)
                log(f"   ✅ Matched: Tower {tower} @ ${price_str}萬")

        except Exception as e:
            # log(f"   Parse Error: {e}")
            continue

    return listings

# --- Main ---
def main():
    log("🚀 Starting Scraper v4...")
    
    # Fetch
    html = fetch_html(CONFIG["URL"])
    current_listings = []
    
    if html:
        current_listings = parse_listings(html)
    else:
        log("❌ No HTML content retrieved.")

    log(f"📊 Total Listings Found: {len(current_listings)}")

    # Update Data
    Path("data").mkdir(exist_ok=True)
    
    output_data = {
        "lastUpdate": datetime.now().isoformat(),
        "listings": current_listings
    }
    Path(CONFIG["OUTPUT_FILE"]).write_text(json.dumps(output_data, ensure_ascii=False, indent=2))
    
    # 這裡我們不寫 cache，因為每次都重新抓取最新的狀態
    # 你的 tracker.py 原本有用 cache，但如果是 v4 純顯示模式，可以簡化
    
    log("💾 Data saved.")

if __name__ == "__main__":
    main()
