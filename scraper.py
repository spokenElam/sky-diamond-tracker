"""
天鑽 The Regent - Property Listing Tracker
==========================================
Scrapes property listings from major HK real estate websites
and sends email notifications for new listings.

Target: Towers 8,9,10,11,12,13,15,16,18 | 1-2 Rooms | <600 sq.ft.
"""

import json
import hashlib
import smtplib
import os
import re
import urllib.request
import urllib.parse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path

# =============================================================================
# CONFIGURATION 設定
# =============================================================================

CONFIG = {
    # Target towers 目標座數
    "TARGET_TOWERS": [8, 9, 10, 11, 12, 13, 15, 16, 18],
    
    # Max size 最大面積
    "MAX_SIZE": 600,
    
    # Target rooms 目標房數
    "TARGET_ROOMS": [1, 2],
    
    # Email recipients 收件人
    "EMAIL_RECIPIENTS": [
        "acforgames9394@gmail.com"
    ],
    
    # Data sources 數據來源
    "SOURCES": {
        "centanet": {
            "name_zh": "中原地產",
            "name_en": "Centaline",
            "url": "https://hk.centanet.com/findproperty/zh-hk/list/sale?q=jvFU4YmBUU9HvXL6MvXU",
            "estate_url": "https://hk.centanet.com/estate/The-Regent/2-DEPPWPPJPB"
        },
        "midland": {
            "name_zh": "美聯物業", 
            "name_en": "Midland",
            "url": "https://www.midland.com.hk/zh-hk/list/sale/大埔半山-天鑽-E000016716",
            "estate_url": "https://www.midland.com.hk/zh-hk/estate/New-Territories-大埔半山-The-Regent-E000016716"
        },
        "28hse": {
            "name_zh": "28Hse",
            "name_en": "28Hse",
            "url": "https://www.28hse.com/buy/residential/a3/dg45/c22902",
            "estate_url": "https://www.28hse.com/en/estate/detail/the-regent-22902"
        },
        "hkp": {
            "name_zh": "香港置業",
            "name_en": "HK Property",
            "url": "https://www.hkp.com.hk/zh-hk/list/sale/大埔-天鑽-E000016716",
            "estate_url": "https://www.hkp.com.hk/zh-hk/estate/New-Territories-Tai-Po-The-Regent-E000016716"
        }
    },
    
    # Cache file 快取檔案
    "CACHE_FILE": "data/listings_cache.json",
    "OUTPUT_FILE": "data/listings.json"
}


# =============================================================================
# LISTING CLASS 放盤類
# =============================================================================

class Listing:
    def __init__(self, tower, floor, unit, size, rooms, price, source, url):
        self.tower = tower
        self.floor = floor
        self.unit = unit
        self.size = size
        self.rooms = rooms
        self.price = price
        self.price_per_ft = price // size if size > 0 else 0
        self.source = source
        self.url = url
        self.scraped_at = datetime.now().isoformat()
        self.id = self._generate_id()
    
    def _generate_id(self):
        key = f"{self.tower}-{self.floor}-{self.unit}-{self.source}"
        return hashlib.md5(key.encode()).hexdigest()[:12]
    
    def matches_criteria(self):
        """Check if listing matches target criteria"""
        return (
            self.tower in CONFIG["TARGET_TOWERS"] and
            self.size < CONFIG["MAX_SIZE"] and
            self.rooms in CONFIG["TARGET_ROOMS"]
        )
    
    def to_dict(self):
        return {
            "id": self.id,
            "tower": self.tower,
            "floor": self.floor,
            "unit": self.unit,
            "size": self.size,
            "rooms": self.rooms,
            "price": self.price,
            "pricePerFt": self.price_per_ft,
            "source": self.source,
            "sourceName": CONFIG["SOURCES"][self.source]["name_zh"],
            "sourceNameEn": CONFIG["SOURCES"][self.source]["name_en"],
            "url": self.url,
            "scrapedAt": self.scraped_at
        }


# =============================================================================
# SCRAPER FUNCTIONS 爬蟲函數
# =============================================================================

def fetch_url(url):
    """Fetch URL content with headers"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-HK,zh;q=0.9,en;q=0.8',
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None


def parse_tower(text):
    """Extract tower number from text"""
    patterns = [
        r'第(\d+)座',
        r'Tower\s*(\d+)',
        r'T(\d+)',
        r'(\d+)座'
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def parse_floor(text):
    """Extract floor from text"""
    patterns = [
        r'(\d+)樓',
        r'(\d+)/F',
        r'(\d+)F',
        r'(\d+)層'
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    # Try to find standalone floor like "高層" "中層" "低層"
    if '高層' in text or 'High' in text:
        return 'High'
    if '中層' in text or 'Mid' in text:
        return 'Mid'
    if '低層' in text or 'Low' in text:
        return 'Low'
    return None


def parse_unit(text):
    """Extract unit letter from text"""
    patterns = [
        r'([A-H])室',
        r'Flat\s*([A-H])',
        r'Unit\s*([A-H])',
        r'\b([A-H])\b(?=\s|$|室)'
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    return None


def parse_size(text):
    """Extract size in sq.ft."""
    patterns = [
        r'(\d{2,4})\s*(?:呎|尺|ft|sq)',
        r'實用[：:]\s*(\d{2,4})',
        r'SFA\s*(\d{2,4})',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def parse_rooms(text):
    """Extract number of rooms"""
    patterns = [
        r'(\d)\s*房',
        r'(\d)\s*[Rr]oom',
        r'(\d)\s*[Bb]ed',
        r'(\d)廳',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return int(match.group(1))
    return None


def parse_price(text):
    """Extract price in HKD"""
    # 萬 (wan = 10,000)
    match = re.search(r'\$?\s*([\d,\.]+)\s*萬', text)
    if match:
        return int(float(match.group(1).replace(',', '')) * 10000)
    
    # 億 (yi = 100,000,000)
    match = re.search(r'\$?\s*([\d,\.]+)\s*億', text)
    if match:
        return int(float(match.group(1).replace(',', '')) * 100000000)
    
    # M (million)
    match = re.search(r'\$?\s*([\d,\.]+)\s*[Mm]', text)
    if match:
        return int(float(match.group(1).replace(',', '')) * 1000000)
    
    # Plain number (assume already in HKD)
    match = re.search(r'\$?\s*([\d,]+)', text)
    if match:
        val = int(match.group(1).replace(',', ''))
        if val > 100000:  # Likely full price
            return val
    
    return None


def scrape_listings():
    """
    Scrape listings from all sources
    Note: Due to anti-scraping measures, this uses a simplified approach.
    In production, you may need Playwright or similar tools.
    """
    listings = []
    
    # For demo/testing, we'll create sample data structure
    # Real implementation would parse actual HTML
    
    print("=" * 50)
    print("天鑽放盤追蹤器 The Regent Listing Tracker")
    print(f"時間 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    for source_id, source_info in CONFIG["SOURCES"].items():
        print(f"\n[{source_info['name_en']}] Checking {source_info['name_zh']}...")
        
        try:
            html = fetch_url(source_info["estate_url"])
            if html:
                # Parse listings from HTML
                # This is a simplified parser - real sites need specific parsing
                parsed = parse_source_html(html, source_id)
                listings.extend(parsed)
                print(f"  Found {len(parsed)} listings")
            else:
                print(f"  Could not fetch data")
        except Exception as e:
            print(f"  Error: {e}")
    
    return listings


def parse_source_html(html, source_id):
    """Parse HTML to extract listings - simplified version"""
    listings = []
    
    # Look for common patterns in property listings
    # This is a basic implementation - real sites need tailored parsing
    
    # Pattern to find property blocks (very simplified)
    # Real implementation needs site-specific parsing
    
    # Try to find tower + floor + unit patterns
    blocks = re.findall(
        r'第?(\d+)座[^<]*?(\d+|高|中|低)[樓層/F][^<]*?([A-H])室?[^<]*?(\d{3,4})[呎尺][^<]*?(\d+)[房室][^<]*?\$?([\d,\.]+)[萬M]',
        html,
        re.IGNORECASE | re.DOTALL
    )
    
    for block in blocks:
        try:
            tower = int(block[0])
            floor = block[1]
            unit = block[2].upper()
            size = int(block[3])
            rooms = int(block[4])
            price_raw = block[5].replace(',', '')
            price = int(float(price_raw) * 10000)  # Assume 萬
            
            listing = Listing(
                tower=tower,
                floor=floor,
                unit=unit,
                size=size,
                rooms=rooms,
                price=price,
                source=source_id,
                url=CONFIG["SOURCES"][source_id]["estate_url"]
            )
            
            if listing.matches_criteria():
                listings.append(listing)
                
        except (ValueError, IndexError) as e:
            continue
    
    return listings


# =============================================================================
# EMAIL FUNCTIONS 郵件函數
# =============================================================================

def send_email(new_listings):
    """Send email notification for new listings"""
    
    if not new_listings:
        print("\nNo new listings to notify")
        return
    
    # Get email credentials from environment
    sender_email = os.environ.get("EMAIL_SENDER")
    sender_password = os.environ.get("EMAIL_PASSWORD")
    
    if not sender_email or not sender_password:
        print("\n⚠️ Email credentials not set. Skipping email notification.")
        print("Set EMAIL_SENDER and EMAIL_PASSWORD environment variables.")
        return
    
    # Build email content
    subject = f"🏠 天鑽新放盤 New Listings ({len(new_listings)}) - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    body_lines = [
        "=" * 50,
        "天鑽 The Regent - 新放盤通知 New Listing Alert",
        "=" * 50,
        "",
        f"發現 {len(new_listings)} 個新放盤",
        f"Found {len(new_listings)} new listing(s)",
        "",
        "-" * 50,
    ]
    
    for i, listing in enumerate(new_listings, 1):
        source = CONFIG["SOURCES"][listing.source]
        body_lines.extend([
            "",
            f"【{i}】",
            f"📍 第{listing.tower}座 {listing.floor}樓 {listing.unit}室",
            f"   Tower {listing.tower}, {listing.floor}/F, Flat {listing.unit}",
            "",
            f"📐 {listing.size}呎 / {listing.size} sq.ft.",
            f"🛏️ {listing.rooms}房 / {listing.rooms} Room(s)",
            f"💰 ${listing.price:,} (${listing.price_per_ft:,}/呎)",
            f"🏢 {source['name_zh']} {source['name_en']}",
            "",
            f"🔗 Link: {listing.url}",
            "",
            "-" * 50,
        ])
    
    body_lines.extend([
        "",
        "篩選條件 Filter Criteria:",
        f"- 座數 Towers: {CONFIG['TARGET_TOWERS']}",
        f"- 房數 Rooms: {CONFIG['TARGET_ROOMS']}",
        f"- 面積 Size: <{CONFIG['MAX_SIZE']} sq.ft.",
        "",
        "---",
        "此郵件由天鑽放盤監控系統自動發送",
        "This email was sent automatically by Sky Diamond Tracker",
        f"Dashboard: https://YOUR_GITHUB_USERNAME.github.io/sky-diamond-tracker/",
    ])
    
    body = "\n".join(body_lines)
    
    # Send email
    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = ", ".join(CONFIG["EMAIL_RECIPIENTS"])
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, CONFIG["EMAIL_RECIPIENTS"], msg.as_string())
        
        print(f"\n✅ Email sent to {len(CONFIG['EMAIL_RECIPIENTS'])} recipients")
        
    except Exception as e:
        print(f"\n❌ Failed to send email: {e}")


# =============================================================================
# CACHE FUNCTIONS 快取函數
# =============================================================================

def load_cache():
    """Load previously seen listing IDs"""
    cache_path = Path(CONFIG["CACHE_FILE"])
    if cache_path.exists():
        try:
            data = json.loads(cache_path.read_text())
            return set(data.get("seen_ids", []))
        except:
            pass
    return set()


def save_cache(seen_ids, listings):
    """Save seen listing IDs and current listings"""
    cache_path = Path(CONFIG["CACHE_FILE"])
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    
    data = {
        "seen_ids": list(seen_ids),
        "last_run": datetime.now().isoformat(),
        "count": len(listings)
    }
    cache_path.write_text(json.dumps(data, indent=2))
    
    # Also save listings for dashboard
    output_path = Path(CONFIG["OUTPUT_FILE"])
    output_data = {
        "lastUpdate": datetime.now().isoformat(),
        "listings": [l.to_dict() for l in listings]
    }
    output_path.write_text(json.dumps(output_data, ensure_ascii=False, indent=2))


# =============================================================================
# MAIN 主程式
# =============================================================================

def main():
    """Main function"""
    
    # Load previous cache
    seen_ids = load_cache()
    print(f"Previously seen: {len(seen_ids)} listings")
    
    # Scrape current listings
    all_listings = scrape_listings()
    
    # Filter by criteria
    matching = [l for l in all_listings if l.matches_criteria()]
    print(f"\nTotal scraped: {len(all_listings)}")
    print(f"Matching criteria: {len(matching)}")
    
    # Find new listings
    new_listings = [l for l in matching if l.id not in seen_ids]
    print(f"New listings: {len(new_listings)}")
    
    # Update seen IDs
    for listing in matching:
        seen_ids.add(listing.id)
    
    # Send email notification
    if new_listings:
        print("\n📧 Sending email notification...")
        send_email(new_listings)
    
    # Save cache
    save_cache(seen_ids, matching)
    
    print("\n" + "=" * 50)
    print("Done! 完成！")
    print("=" * 50)


if __name__ == "__main__":
    main()
