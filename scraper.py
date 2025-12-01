#!/usr/bin/env python3
"""
天鑽 The Regent - Scraper v7 (Fix: Optional Prefix for 'Block/Tower')
"""

import json
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
}

def log(msg):
    print(msg, flush=True)

def get_headers():
    agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15',
    ]
    return {
        'User-Agent': random.choice(agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Cookie': 'locale=zh-hk', # 強制中文
    }

def fetch_url(url):
    log(f"🌍 Fetching: {url}")
    try:
        # 隨機延遲
        time.sleep(random.uniform(1.5, 3))
        req = urllib.request.Request(url, headers=get_headers())
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        log(f"❌ Error fetching {url}: {e}")
        return None

# =============================================================================
# 1. 28Hse (Targeted Regex)
# =============================================================================
def scrape_28hse():
    log("--- Scraping 28Hse ---")
    base_url = "https://www.28hse.com/utf8/buy/residential/a3/dg45/c22902"
    listings = []
    
    for page in range(1, 4):
        url = base_url if page == 1 else f"{base_url}/page-{page}"
        html = fetch_url(url)
        if not html: continue

        # Debug: 檢查是否被擋
        if "Security Check" in html or "Just a moment" in html:
            log(f"⚠️ Page {page}: Blocked by Cloudflare/Security Check")
            continue

        # 切割 chunks
        chunks = re.split(r'class="item', html)
        found_in_page = 0
        
        for chunk in chunks[1:]:
            try:
                # [修正重點] 
                # 舊 regex: (?:第|Block|T)\s*(\d+)  <-- 強制要有 "第"
                # 新 regex: (?:第|Block|T)?\s*(\d+)\s*座 <-- "第" 可有可無 (?)
                # 另外直接針對你的截圖 "unit_desc">13座
                
                tower = 0
                price = 0
                
                # 嘗試方法 A: 針對 unit_desc (你截圖見到的)
                desc_match = re.search(r'unit_desc">\s*(?:第)?\s*(\d+)\s*座', chunk)
                if desc_match:
                    tower = int(desc_match.group(1))
                else:
                    # 嘗試方法 B: 通用搜索 "13座"
                    # look for digits followed by "座", ignoring "第"
                    general_match = re.search(r'(\d+)\s*座', chunk)
                    if general_match:
                        tower = int(general_match.group(1))

                # 找價錢 (紅色框個舊)
                # pattern: $578 萬 or 售 $578 萬
                price_match = re.search(r'\$\s*([\d,]+)\s*萬', chunk)
                if price_match:
                    price = int(price_match.group(1).replace(',', '')) * 10000

                if tower in CONFIG["TARGET_TOWERS"] and price > 0:
                    # 描述
                    clean_text = re.sub(r'<[^>]+>', ' ', chunk)
                    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                    desc = clean_text[:50] + "..."
                    
                    # 連結
                    link_match = re.search(r'href="([^"]+)"', chunk)
                    link = link_match.group(1) if link_match else url

                    listing = {
                        "id": f"28hse-{tower}-{price}-{page}",
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
                        found_in_page += 1
                        log(f"   ✅ Found: T{tower} ${price/10000}萬")
            except Exception as e:
                # log(f"Debug error: {e}")
                continue
        
        log(f"   > Page {page}: Found {found_in_page} items")
        if found_in_page == 0 and page == 1:
            # 如果第一頁都係 0，可能係 HTML 結構變左，印少少出來睇
            log(f"   ⚠️ DEBUG HTML snippet: {html[:200]}")

    return listings

# =============================================================================
# 2. Property.hk (Backup)
# =============================================================================
def scrape_property_hk():
    log("--- Scraping Property.hk ---")
    url = "https://www.property.hk/buy/search/%E5%A4%A9%E9%91%BD/"
    html = fetch_url(url)
    if not html: return []
    listings = []
    
    rows = html.split('</tr>')
    for row in rows:
        try:
            # Property.hk 通常格式: "第10座"
            tower_match = re.search(r'第\s*(\d+)\s*座', row)
            price_match = re.search(r'(\d{3,5})\s*萬', row)
            
            if tower_match and price_match:
                tower = int(tower_match.group(1))
                price = int(price_match.group(1)) * 10000
                
                if tower in CONFIG["TARGET_TOWERS"]:
                    link_match = re.search(r'href="([^"]+)"', row)
                    link = "https://www.property.hk" + link_match.group(1) if link_match else url
                    
                    listing = {
                        "id": f"phk-{tower}-{price}",
                        "tower": tower, "floor": "??", "unit": "?", "size": 0, "rooms": 0,
                        "price": price, "pricePerFt": 0,
                        "raw_desc": f"第{tower}座 (Property.hk)",
                        "url": link, "source": "hkp", "sourceName": "Property.hk",
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
    log("🚀 Starting Scraper v7 (Fix Prefix)...")
    all_listings = []
    
    all_listings.extend(scrape_28hse())
    all_listings.extend(scrape_property_hk())
    # Centaline 暫時移除，因為 SSL 錯誤會拖慢成個 process 兼且抓唔到
    
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
