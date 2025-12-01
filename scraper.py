#!/usr/bin/env python3
"""
天鑽 The Regent - Scraper v6 (All-in-One: 28Hse Pages + Ricacorp + Centaline + PropertyHK)
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
    # 目標座數 (Target Towers)
    "TARGET_TOWERS": [8, 9, 10, 11, 12, 13, 15, 16, 18],
    "CACHE_FILE": "data/listings_cache.json",
    "OUTPUT_FILE": "data/listings.json",
}

def log(msg):
    print(msg, flush=True)

def get_headers():
    # 隨機換 User-Agent 扮真人
    agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Edge/121.0.0.0',
    ]
    return {
        'User-Agent': random.choice(agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-HK,zh;q=0.9,en;q=0.8',
        'Cookie': 'locale=zh-hk', # 強制中文
        'Referer': 'https://www.google.com/'
    }

def fetch_url(url):
    log(f"🌍 Fetching: {url}")
    try:
        # 隨機延遲 1-3 秒，減低被封機會
        time.sleep(random.uniform(1, 3))
        
        req = urllib.request.Request(url, headers=get_headers())
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        # 如果是 403 Forbidden，通常是被防毒牆擋了
        error_msg = str(e)
        if "403" in error_msg:
            log(f"⚠️ Access Denied (403) by {url} - IP Blocked")
        else:
            log(f"❌ Error fetching {url}: {e}")
        return None

# =============================================================================
# 1. 28Hse (支援分頁)
# =============================================================================
def scrape_28hse():
    log("--- Scraping 28Hse (Pages 1-3) ---")
    base_url = "https://www.28hse.com/utf8/buy/residential/a3/dg45/c22902"
    listings = []
    
    # 抓取 1 到 3 頁
    for page in range(1, 4):
        # 組合 URL: 第一頁不用加 page
        url = base_url if page == 1 else f"{base_url}/page-{page}"
        log(f"   > Processing Page {page}...")
        
        html = fetch_url(url)
        if not html: continue

        # 檢查是否最後一頁 (如果頁面沒有放盤 item)
        if 'class="item' not in html:
            log("   > No more items, stopping.")
            break

        chunks = re.split(r'class="item', html)
        found_on_page = 0
        
        for chunk in chunks[1:]:
            try:
                # 找座數
                tower_match = re.search(r'(?:第|Block|T)\s*(\d+)\s*座?', chunk, re.IGNORECASE)
                # 找價錢
                price_match = re.search(r'\$\s*([\d,]+(?:\.\d+)?)\s*萬', chunk)
                if not price_match: # 後備價錢格式
                    price_match = re.search(r'售\s*([\d,]+(?:\.\d+)?)\s*萬', chunk)

                if tower_match and price_match:
                    tower = int(tower_match.group(1))
                    price_str = price_match.group(1).replace(',', '')
                    price = int(float(price_str) * 10000)

                    if tower in CONFIG["TARGET_TOWERS"]:
                        # 找描述
                        clean_text = re.sub(r'<[^>]+>', ' ', chunk)
                        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                        desc = clean_text[:60] + "..."
                        
                        # 找詳細連結
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
                            found_on_page += 1
            except:
                continue
        log(f"   > Found {found_on_page} items on page {page}")

    return listings

# =============================================================================
# 2. 利嘉閣 Ricacorp
# =============================================================================
def scrape_ricacorp():
    log("--- Scraping Ricacorp ---")
    url = "https://www.ricacorp.com/zh-hk/property/list/buy/%E5%A4%A9%E9%91%BD-estate-%E5%A4%A7%E5%9F%94%E5%8D%8A%E5%B1%B1-hma-hk"
    html = fetch_url(url)
    if not html: return []
    
    listings = []
    # 切割區塊
    chunks = re.split(r'class="property-card', html)
    
    for chunk in chunks[1:]:
        try:
            # 利嘉閣格式: "第8座"
            tower_match = re.search(r'第\s*(\d+)\s*座', chunk)
            
            # 價錢: $ 638 萬
            price_match = re.search(r'\$\s*([\d,]+)\s*萬', chunk)
            
            # 呎數
            size_match = re.search(r'(\d+)\s*呎', chunk)
            
            if tower_match and price_match:
                tower = int(tower_match.group(1))
                price_str = price_match.group(1).replace(',', '')
                price = int(price_str) * 10000
                size = int(size_match.group(1)) if size_match else 0
                
                if tower in CONFIG["TARGET_TOWERS"]:
                    # 找連結
                    link_match = re.search(r'href="([^"]+)"', chunk)
                    link = "https://www.ricacorp.com" + link_match.group(1) if link_match else url
                    
                    listing = {
                        "id": f"rica-{tower}-{price}",
                        "tower": tower,
                        "floor": "??", "unit": "?",
                        "size": size,
                        "rooms": 0,
                        "price": price,
                        "pricePerFt": price // size if size > 0 else 0,
                        "raw_desc": f"第{tower}座 (利嘉閣)",
                        "url": link,
                        "source": "centanet", # 借用橙色 style (或改用 hkp 紫色)
                        "sourceName": "Ricacorp",
                        "scrapedAt": datetime.now().isoformat()
                    }
                    if not any(l["id"] == listing["id"] for l in listings):
                        listings.append(listing)
                        log(f"   ✅ Ricacorp Found: T{tower} ${price_str}萬")
        except:
            continue
            
    return listings

# =============================================================================
# 3. 中原 Centaline (極難抓，Best Effort)
# =============================================================================
def scrape_centaline():
    log("--- Scraping Centaline ---")
    url = "https://hk.centanet.com/findproperty/list/buy/%E5%A4%A9%E9%91%BD_2-DEPPWPPJPB"
    html = fetch_url(url)
    if not html: return []
    
    listings = []
    # 中原是 React App，HTML 裡面通常只有一堆 JSON data 在 <script> 標籤裡
    # 我們嘗試在源代碼裡找 "第X座" 的蹤跡
    
    # 簡單 Regex 掃描全文
    # 格式可能係: "title":"第8座..." 或者純文字
    matches = re.findall(r'第\s*(\d+)\s*座.{0,100}?\$([\d,]+)萬', html)
    
    for match in matches:
        try:
            tower = int(match[0])
            price_str = match[1].replace(',', '')
            price = int(price_str) * 10000
            
            if tower in CONFIG["TARGET_TOWERS"]:
                listing = {
                    "id": f"centa-{tower}-{price}",
                    "tower": tower,
                    "floor": "??", "unit": "?", "size": 0, "rooms": 0,
                    "price": price, "pricePerFt": 0,
                    "raw_desc": f"第{tower}座 (中原)",
                    "url": url,
                    "source": "centanet",
                    "sourceName": "Centaline",
                    "scrapedAt": datetime.now().isoformat()
                }
                if not any(l["id"] == listing["id"] for l in listings):
                    listings.append(listing)
                    log(f"   ✅ Centaline Found: T{tower} ${price_str}萬")
        except:
            continue
            
    return listings

# =============================================================================
# 4. Property.hk (保底)
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
            tower_match = re.search(r'第\s*(\d+)\s*座', row)
            price_match = re.search(r'(\d{3,5})\s*萬', row)
            size_match = re.search(r'(\d{3,4})\s*呎', row)
            if tower_match and price_match:
                tower = int(tower_match.group(1))
                price = int(price_match.group(1)) * 10000
                size = int(size_match.group(1)) if size_match else 0
                if tower in CONFIG["TARGET_TOWERS"]:
                    link_match = re.search(r'href="([^"]+)"', row)
                    link = "https://www.property.hk" + link_match.group(1) if link_match else url
                    listing = {
                        "id": f"phk-{tower}-{price}",
                        "tower": tower, "floor": "??", "unit": "?", "size": size, "rooms": 0,
                        "price": price, "pricePerFt": price // size if size > 0 else 0,
                        "raw_desc": f"第{tower}座 (Property.hk)",
                        "url": link, "source": "hkp", "sourceName": "Property.hk",
                        "scrapedAt": datetime.now().isoformat()
                    }
                    if not any(l["id"] == listing["id"] for l in listings):
                        listings.append(listing)
                        log(f"   ✅ Property.hk Found: T{tower} ${listing['price']//10000}萬")
        except: continue
    return listings

# =============================================================================
# MAIN
# =============================================================================
def main():
    log("🚀 Starting Scraper v6 (All-in-One)...")
    all_listings = []
    
    # 執行所有 Scraper
    all_listings.extend(scrape_28hse())     # 28Hse (多頁)
    all_listings.extend(scrape_ricacorp())  # 利嘉閣
    all_listings.extend(scrape_centaline()) # 中原 (可能403)
    all_listings.extend(scrape_property_hk()) # Property.hk (保底)
    
    log(f"📊 Total Combined Listings: {len(all_listings)}")

    # 排序：價錢低到高
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
