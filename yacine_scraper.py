import base64
import requests
import json
import time
import os
import re
import random
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

# جلب معلومات الـ Gist من متغيرات البيئة الآمنة (GitHub Secrets)
GIST_ID = os.environ.get("GIST_ID")
GITHUB_TOKEN = os.environ.get("GIST_TOKEN")

# قائمة النطاقات المستقرة والفعالة لتطبيق ياسين تيفي
YACINE_DOMAINS = [
    "https://def.yacinelive.com",
    "https://ver3.yacinelive.com",
    "https://v31.yacinelive.com"
]

# ترويسة الحماية الوحيدة والأساسية المطلوبة لتشغيل البث المباشر بنجاح
UA_VALUE = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
REFERER_VALUE = "https://x.com/"

# دالة فك التشفير الخاصة بتطبيق ياسين تيفي (XOR Decryption)
def decrypt_yacine(encrypted_data, header_t):
    base_key = "c!xZj+N9&G@Ev@vw"
    full_key = (base_key + header_t).encode('utf-8')
    try:
        encrypted_bytes = base64.b64decode(encrypted_data)
        decrypted_bytes = bytearray()
        for i in range(len(encrypted_bytes)):
            decrypted_bytes.append(encrypted_bytes[i] ^ full_key[i % len(full_key)])
        return decrypted_bytes.decode('utf-8')
    except Exception as e:
        print(f"Error decrypting Yacine: {e}")
        return None

# إنشاء جلسة عمل مشتركة (Session) للحفاظ على الكوكيز وتفادي الحظر
def create_session():
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

# دالة للاتصال بسيرفر ياسين وتجربة النطاقات المستقرة وفك التشفير تلقائياً
def fetch_and_decrypt_yacine_dynamic(session, endpoint_path, headers):
    for domain in YACINE_DOMAINS:
        url = f"{domain}{endpoint_path}"
        try:
            response = session.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                t_value = response.headers.get('T') or response.headers.get('t')
                if t_value:
                    decrypted_json_str = decrypt_yacine(response.text, t_value)
                    if decrypted_json_str:
                        return json.loads(decrypted_json_str)
        except Exception as e:
            print(f"⚠️ فشل النطاق {domain} بسبب: {e}")
            continue
    return None

# دالة جلب رابط التوجيه المباشر (تتبع الـ 302 والحصول على السيرفر الفعلي الفعال باستخدام المرجع المطلوب للموزع)
def get_final_url(session, raw_url):
    browser_headers = {
        "User-Agent": UA_VALUE,
        "Referer": REFERER_VALUE
    }
    try:
        r_redirect = session.get(raw_url, headers=browser_headers, allow_redirects=False, timeout=8)
        if r_redirect.status_code in [301, 302]:
            final_location = r_redirect.headers.get('Location')
            if final_location:
                return final_location
    except Exception as e:
        print(f"⚠️ فشل جلب التوجيه الفعلي للرابط {raw_url}: {e}")
    return raw_url

# دالة فحص صحة روابط البث الفعلي (تتطلب فقط الـ User-Agent وتتجنب المرجع لمنع الحظر)
def validate_stream_url(session, url):
    headers = {
        "User-Agent": UA_VALUE
    }
    try:
        response = session.get(url, headers=headers, stream=True, timeout=4)
        if response.status_code in [200, 302]:
            response.close()
            return True
    except Exception:
        pass
    return False

# دالة ذكية لتجميل وتنظيف أسماء القنوات وتجنب التكرار
def clean_channel_name(name, is_max, quality):
    clean = name
    for word in ["beIN", "Sports", "Sport", "MAX", "بين", "سبورت", "ماكس"]:
        clean = re.compile(re.escape(word), re.IGNORECASE).sub("", clean)
    
    clean = clean.strip()
    clean = re.sub(r'\s+', ' ', clean)
    
    if is_max:
        return f"beIN Sports Max {clean} {quality}"
    else:
        return f"beIN Sports {clean} {quality}"

# دالة لكشف واستخراج قنوات ماجد سبورت النشطة تلقائياً من ملف الإعدادات
def get_majed_dynamic_channels(session):
    timestamp = int(time.time() * 1000)
    config_url = f"http://majed-koora.live/config.json?v={timestamp}"
    headers = {
        "User-Agent": UA_VALUE,
        "Referer": "http://majed-koora.live/"
    }
    try:
        response = session.get(config_url, headers=headers, timeout=10)
        if response.status_code == 200:
            found = re.findall(r'majed[a-zA-Z0-9_-]+', response.text)
            channels = [c for c in found if "koora" not in c.lower() and "live" not in c.lower()]
            if channels:
                unique_channels = list(dict.fromkeys(channels))
                print(f"🔍 تم اكتشاف القنوات النشطة من ملف الإعدادات: {unique_channels}")
                return unique_channels
    except Exception as e:
        print(f"⚠️ فشل جلب ملف الإعدادات config.json من ماجد سبورت: {e}")
    
    return ["majedsports1"]

# دالة لتصفية واستخراج القنوات اليدوية والثابتة فقط بشكل آمن
def extract_static_channels(m3u_content):
    lines = m3u_content.splitlines()
    static_lines = []
    current_channel_block = []
    
    exclude_keywords = [
        "def.yacinelive.com", "metava.online", "re.ycn-redirect.com", "re.ycn-redirect.buzz", "BEIN MAX YACINE TV",
        "albashatv.site", "playcasta.online", "AL BASHA TV", "majed-koora.live"
    ]

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
        
        if line_stripped.startswith("#EXTM3U") or "=====" in line_stripped:
            continue
            
        if line_stripped.startswith("#EXTINF"):
            if current_channel_block:
                block_str = "".join(current_channel_block)
                if not any(kw in block_str for kw in exclude_keywords):
                    static_lines.extend(current_channel_block)
                    static_lines.append("")
            current_channel_block = [line_stripped]
        elif line_stripped.startswith("#") or line_stripped.startswith("http") or line_stripped.startswith("rtmp"):
            if current_channel_block:
                current_channel_block.append(line_stripped)
            else:
                if not any(kw in line_stripped for kw in exclude_keywords):
                    static_lines.append(line_stripped)
                    
    if current_channel_block:
        block_str = "".join(current_channel_block)
        if not any(kw in block_str for kw in exclude_keywords):
            static_lines.extend(current_channel_block)
            
    return "\n".join(static_lines).strip()

# دالة لفحص حالة بروكسي الباشا وكشف صفحات التحدي والحظر
def check_basha_proxy_status(session):
    test_url = "http://live-albashatv.site/stream"
    try:
        response = session.get(test_url, timeout=3, allow_redirects=False)
        response_text_lower = response.text.lower()
        
        is_cloudflare_challenge = (
            "cf-challenge" in response_text_lower or 
            "challenges.cloudflare.com" in response_text_lower or 
            "just a moment" in response_text_lower or
            "turnstile" in response_text_lower
        )
        
        if response.status_code in [200, 400] and not is_cloudflare_challenge:
            print(f"⚡ تم فحص البروكسي: نشط ومتاح.")
            return True
        else:
            print(f"⚠️ تم فحص البروكسي: غير متاح أو محجوب بـ Cloudflare.")
            return False
    except Exception as e:
        print(f"⚠️ تم فحص البروكسي: فشل الاتصال ({e}).")
        return False

# دالة ذكية لاستخراج الأقسام الحالية من الـ Gist لحمايتها في حال حدوث فشل مؤقت للـ API
def extract_section_by_headers(content, current_header, next_headers):
    if current_header not in content:
        return ""
    start_idx = content.find(current_header) + len(current_header)
    end_idx = len(content)
    for next_header in next_headers:
        if next_header in content:
            pos = content.find(next_header)
            if pos > start_idx and pos < end_idx:
                end_idx = pos
    return content[start_idx:end_idx].strip()

# دالة مطورة لمطابقة قنوات الأطفال المستهدفة بدقة عالية باللغتين
def matches_kids(channel_name):
    name_lower = channel_name.lower()
    if any(kw in name_lower for kw in ["tom and jerry", "tom & jerry", "توم وجيري", "توم وجري"]):
        return "Tom and Jerry"
    if "masha" in name_lower or "ماشا" in name_lower:
        return "Masha and the Bear"
    if "dora" in name_lower or "دورا" in name_lower:
        return "Dora"
    if "spacetoon" in name_lower or "سبيستون" in name_lower or "سبيس تون" in name_lower:
        return "Spacetoon"
    if "wanasa" in name_lower or "وناسة" in name_lower:
        return "Wanasat"
    if "baraem" in name_lower or "براعم" in name_lower:
        return "Baraem"
    if "cn arabia" in name_lower or "cartoon network" in name_lower or "كرتون نتورك" in name_lower:
        return "CN Arabia"
    
    if "jeem" in name_lower or "تلفزيون جيم" in name_lower or "قناة جيم" in name_lower or "جيم" in name_lower.split():
        return "Jeem"
    return None


# 1. جلب المحتوى الحالي من الـ Gist وتصفية قنواتك اليدوية وحفظها احتياطياً
print("📂 جاري جلب محتوى الـ Gist الحالي للنسخ الاحتياطي وحفظ القنوات...")
gist_api_url = f"https://api.github.com/gists/{GIST_ID}"
gist_headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

static_clean = ""
current_content = ""
filename = "kz.m3u"

try:
    gist_response = requests.get(gist_api_url, headers=gist_headers, timeout=15)
    if gist_response.status_code == 200:
        gist_data = gist_response.json()
        filename = list(gist_data['files'].keys())[0]
        current_content = gist_data['files'][filename]['content']
        
        static_clean = extract_static_channels(current_content)
        print("✔️ تم تحديد وحفظ القنوات اليدوية والثابتة بنجاح.")
    else:
        print(f"❌ فشل جلب الـ Gist الحالي. كود الحالة: {gist_response.status_code}")
        exit(1)
except Exception as e:
    print(f"❌ خطأ أثناء الاتصال بـ Gist API: {e}")
    exit(1)

# ترويسات الأقسام لتسهيل استخراج الحالة السابقة كـ Fail-safe
headers_list = [
    "# ==================== مجموعة قنوات LIVE ====================",
    "# ==================== مجموعة قنوات AL BASHA TV ====================",
    "# ==================== مجموعة قنوات BEIN MAX YACINE TV ====================",
    "# ==================== قنواتك اليدوية والثابتة ===================="
]

prev_live = extract_section_by_headers(current_content, headers_list[0], headers_list[1:])
prev_basha = extract_section_by_headers(current_content, headers_list[1], headers_list[2:])
prev_yacine = extract_section_by_headers(current_content, headers_list[2], headers_list[3:])

session = create_session()
final_m3u_content = ""

# 2. كشف وتجهيز باقة قنوات LIVE المباشرة ديناميكياً مع حماية الـ Fail-safe
print("\n⚽ جاري كشف وتجهيز مجموعة قنوات LIVE المباشرة...")
live_separator = "# ==================== مجموعة قنوات LIVE ===================="

live_content = ""
try:
    active_majed_channels = get_majed_dynamic_channels(session)
    timestamp = int(time.time() * 1000)

    for channel in active_majed_channels:
        live_url = f"http://majed-koora.live/stream.php?channel={channel}&file=stream.m3u8&v={timestamp}"
        display_name = channel.replace("majedsports", "Majed Sport ").title()
        
        live_content += (
            f'#EXTINF:-1 tvg-logo="" group-title="LIVE", {display_name} FHD\n'
            f'{live_url}\n'
            f'#EXTINF:-1 tvg-logo="" group-title="LIVE", {display_name} HD\n'
            f'{live_url}\n'
        )
except Exception as e:
    print(f"⚠️ خطأ أثناء تحديث باقة LIVE: {e}")

# تعويض وقائي ذكي لباقة LIVE في حال فشل سحبها
if not live_content.strip() and prev_live.strip():
    print("🛡️ فشل جلب باقة LIVE، تم استرداد القنوات السابقة بنجاح لحمايتها من الحذف.")
    live_content = prev_live


# 3. جلب وتصفية باقة قنوات الباشا تيفي (Al Basha TV) مع حماية الـ Fail-safe
print("\n🚀 جاري جلب قنوات الباشا تيفي (Al Basha TV)...")
basha_separator = "# ==================== مجموعة قنوات AL BASHA TV ===================="
basha_api_url = "https://albashatv.site/api.php"
basha_headers = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Connection": "Keep-Alive",
    "User-Agent": "okhttp/3.9.1"
}

use_basha_proxy = check_basha_proxy_status(session)
basha_payloads = ["method=o6&event=view", "method=o2&event=view"]
basha_content = ""

kids_channels_list = []
regular_channels_list = []
seen_basha_urls = set() 
matched_count = 0

for payload in basha_payloads:
    try:
        basha_response = session.post(basha_api_url, headers=basha_headers, data=payload, timeout=15)
        if basha_response.status_code == 200:
            basha_channels = basha_response.json()
            
            for channel in basha_channels:
                channel_name = channel.get('name', '')
                raw_url = channel.get('url', '')
                
                if not raw_url or raw_url in seen_basha_urls:
                    continue
                    
                channel_name_lower = channel_name.lower()
                
                exclude_tags = [
                    "vip de", "vip uk", "vip ru", "vip bg", "vip pl", "vip es", "vip tr", "vip ph", "vip it", "vip br", "vip us", "vip dk", "vip hu", "vip ro",
                    "de:", "uk:", "ru:", "bg:", "pl:", "es:", "ca:", "tr:", "ph:", "au:", "cz:", "usa:", "it:", "br:", "hu:", "us:", "ro:", "dk:", "usa)", "hu", "ro", "dk", "usa",
                    " de ", " uk ", " ru ", " bg ", " pl ", " es ", " ca ", " tr ", " ph ", " au ", " cz ", " usa ", " it ", " br ", " hu ", " us ", " ro ", " dk ",
                    "[de]", "[uk]", "[ru]", "[bg]", "[pl]", "[es]", "[ca]", "[tr]", "[ph]", "[au]", "[cz]", "[usa]", "[it]", "[br]", "[hu]", "[us]", "[ro]", "[dk]",
                    "(de)", "(uk)", "(ru)", "(bg)", "(pl)", "(es)", "(ca)", "(tr)", "(ph)", "(au)", "(cz)", "(usa)", "(it)", "(br)", "(hu)", "(us)", "(ro)", "(dk)"
                ]
                
                if any(tag in channel_name_lower for tag in exclude_tags):
                    continue
                
                kids_match = matches_kids(channel_name)
                if kids_match:
                    if use_basha_proxy:
                        final_basha_url = f"http://live-albashatv.site/stream?url={raw_url}"
                        entry = f'#EXTINF:-1 tvg-logo="" group-title="AL BASHA TV", {channel_name}\n{final_basha_url}\n'
                    else:
                        basha_ua = "okhttp/3.9.1"
                        final_basha_url = f"{raw_url}|User-Agent={basha_ua}"
                        entry = (
                            f'#EXTINF:-1 tvg-logo="" group-title="AL BASHA TV", {channel_name}\n'
                            f'#EXTVLCOPT:http-user-agent={basha_ua}\n'
                            f'{final_basha_url}\n'
                        )
                    kids_channels_list.append(entry)
                    seen_basha_urls.add(raw_url)
                    matched_count += 1
                    continue 
                
                is_bein = "bein" in channel_name_lower
                
                is_arabic_premium = False
                premium_keywords = [
                    "osn", "netflix", "hbo", "amazon", "vip", "shahid", 
                    "box office", "boxoffice", "box-office", "بوكس", 
                    "al fajer", "fajer", "الفجر",
                    "stc", "thamanya", "ثمانية",
                    "alkass", "الكأس", "الكاس",
                    "alwan", "ألوان", "الوان",
                    "mbc", "ام بي سي"
                ]
                if any(kw in channel_name_lower for kw in premium_keywords):
                    has_arabic_chars = any('\u0600' <= char <= '\u06FF' for char in channel_name)
                    has_foreign_tag = any(tag in channel_name_lower for tag in ["fr:", "fr ", "(fr)", "[fr]", " en ", " es ", " de "])
                    if has_arabic_chars or not has_foreign_tag:
                        is_arabic_premium = True
                
                is_french_target = False
                french_tags = ["fr:", "fr ", "(fr)", "[fr]", "france"]
                if any(tag in channel_name_lower for tag in french_tags) or "canal+" in channel_name_lower:
                    french_keywords = [
                        "tf1", "m6", "canal", "rmc", "eurosport", "lequipe", "l'equipe", 
                        "ocs", "cine", "ciné", "gulli", "tiji", "cartoon", "disney", 
                        "nickelodeon", "nat geo", "national geo", "discovery", "ushuaia", 
                        "histoire", "science", "action", "w9", "tmc", "tfx"
                    ]
                    if any(kw in channel_name_lower for kw in french_keywords):
                        is_french_target = True
                
                if is_bein or is_arabic_premium or is_french_target:
                    if use_basha_proxy:
                        final_basha_url = f"http://live-albashatv.site/stream?url={raw_url}"
                        entry = f'#EXTINF:-1 tvg-logo="" group-title="AL BASHA TV", {channel_name}\n{final_basha_url}\n'
                    else:
                        basha_ua = "okhttp/3.9.1"
                        final_basha_url = f"{raw_url}|User-Agent={basha_ua}"
                        entry = (
                            f'#EXTINF:-1 tvg-logo="" group-title="AL BASHA TV", {channel_name}\n'
                            f'#EXTVLCOPT:http-user-agent={basha_ua}\n'
                            f'{final_basha_url}\n'
                        )
                    regular_channels_list.append(entry)
                    seen_basha_urls.add(raw_url)
                    matched_count += 1
    except Exception as e:
        print(f"❌ خطأ أثناء جلب قنوات الباشا: {e}")

basha_content = "".join(kids_channels_list) + "".join(regular_channels_list)

# تعويض وقائي ذكي لباقة الباشا تيفي في حال فشل جلبها
if not basha_content.strip() and prev_basha.strip():
    print("🛡️ فشل جلب باقة الباشا ديناميكياً، تم استرداد القنوات السابقة بنجاح لحمايتها من الحذف.")
    basha_content = prev_basha
else:
    print(f"🎯 تم استخراج وتصفية ({matched_count}) قناة من الباشا بنجاح (بما في ذلك قنوات الأطفال بالمقدمة).")


# 4. جلب وتنسيق باقة قنوات ياسين تيفي (Yacine TV) مع الفصل والتنظيف والتحقق وحماية الـ Fail-safe
print("\n🚀 جاري جلب قنوات ياسين تيفي (Yacine TV)...")
yacine_separator = "# ==================== مجموعة قنوات BEIN MAX YACINE TV ===================="

# الفئات المستهدفة: 90 لجودة FHD، و 89 لجودة HD، و 91 لجودة SD
targets = {
    "/api/categories/90/channels": "FHD",
    "/api/categories/89/channels": "HD",
    "/api/categories/91/channels": "SD"
}

yacine_headers = {
    "Accept": "application/json",
    "Accept-Encoding": "gzip",
    "Connection": "Keep-Alive",
    "User-Agent": "okhttp/4.12.0"
}

yacine_lines = []
yacine_content = ""
yacine_failed = False
total_yacine_channels_extracted = 0

for category_endpoint, quality in targets.items():
    print(f"🔄 جاري سحب باقة ياسين بجودة {quality}...")
    channels_data = fetch_and_decrypt_yacine_dynamic(session, category_endpoint, yacine_headers)
    
    if not channels_data or 'data' not in channels_data:
        print(f"⚠️ فشل جلب البيانات للفئة {quality} أو السيرفر مغلق للصيانة.")
        continue
        
    channels_list = channels_data.get('data', [])
    if not channels_list:
        continue
        
    filtered_channels = []
    for channel in channels_list:
        channel_name = channel.get('name') or ""
        channel_name_lower = channel_name.lower()
        
        is_target = (
            "max" in channel_name_lower or 
            "bein" in channel_name_lower or 
            "ماكس" in channel_name_lower or 
            "بين" in channel_name_lower or
            "سبورت" in channel_name_lower
        )
        if is_target:
            filtered_channels.append(channel)
            
    def extract_number(name):
        nums = re.findall(r'\d+', name)
        return int(nums[0]) if nums else 999
        
    filtered_channels.sort(key=lambda x: extract_number(x.get('name', '')))
    
    for index, channel in enumerate(filtered_channels):
        channel_name = channel.get('name')
        channel_id = channel.get('id')
        
        print(f"   ⏳ [{index + 1}/{len(filtered_channels)}] جاري استخراج قنوات {quality}: {channel_name}...")
        channel_detail_endpoint = f"/api/channel/{channel_id}"
        detail_data = fetch_and_decrypt_yacine_dynamic(session, channel_detail_endpoint, yacine_headers)
        
        if detail_data and 'data' in detail_data:
            streams = detail_data['data']
            
            valid_urls = []
            for stream in streams:
                raw_url = stream.get('url')
                if not raw_url:
                    continue
                
                if "/dash/.mpd" in raw_url:
                    raw_url = raw_url.replace("/dash/.mpd", "/playlist.m3u8")
                    
                if ".mpd" in raw_url.lower() or "cenc" in raw_url.lower() or "/dash/" in raw_url.lower():
                    continue
                    
                valid_urls.append(raw_url)
            
            for stream_idx, final_url in enumerate(valid_urls):
                # 1. تتبع وفك التوجيه والحصول على السيرفر الفعلي المباشر (مثل trivanta.buzz)
                direct_url = get_final_url(session, final_url)
                
                # 2. فحص صحة روابط البث الفعلي (Pre-flight Check) لضمان فعاليتها التامة
                print(f"      🔍 فحص صحة السيرفر لـ {channel_name}...")
                if not validate_stream_url(session, direct_url):
                    print(f"      ❌ السيرفر {direct_url[:40]}... غير متاح أو متوقف حالياً. تم تجاوزه.")
                    continue
                
                # 3. تحديد ما إذا كانت القناة تتبع Max أو الباقة الأساسية مع تنظيف وتجميل الأسماء
                channel_name_lower = channel_name.lower()
                is_max = "max" in channel_name_lower or "ماكس" in channel_name_lower
                
                display_name = clean_channel_name(channel_name, is_max, quality)
                if stream_idx > 0:
                    display_name += f" (S{stream_idx + 1})"
                
                group_title = "BEIN SPORTS MAX" if is_max else "BEIN SPORTS"
                
                # صيغة الرابط الصافية والفعالة بنسبة 100% المقتصرة على الـ User-Agent فقط بدون مراجع معرقلة
                final_url_with_headers = f"{direct_url}|User-Agent={UA_VALUE}"
                
                # صياغة القنوات المتوافقة تماماً مع VLC وكافة أجهزة الاستقبال والريسيفرات
                chan_entry = (
                    f'#EXTINF:-1 tvg-logo="" group-title="{group_title}", {display_name}\n'
                    f'#EXTVLCOPT:http-user-agent={UA_VALUE}\n'
                    f'{final_url_with_headers}\n'
                )
                yacine_lines.append(chan_entry)
                total_yacine_channels_extracted += 1
                print(f"      ✔️ تم جلب وتأكيد تشغيل: {display_name}")
        
        time.sleep(random.uniform(0.3, 0.8))

yacine_content = "".join(yacine_lines)

# 4. آلية الحماية والاحتفاظ الوقائي من الانهيار (Fail-Safe Mechanism) في حال الصيانة أو عطل الشبكة
if total_yacine_channels_extracted == 0:
    yacine_failed = True

if yacine_failed and prev_yacine.strip():
    print("\n🛡️ ⚠️ تنبيه هام: تطبيق ياسين تيفي مغلق حالياً أو الـ API لا تستجيب!")
    print("🛡️ سيتم تلقائياً حماية واستعادة كامل باقة ياسين تيفي السابقة لمنع مسح القنوات وضمان تشغيلها.")
    yacine_content = prev_yacine
else:
    print(f"\n🎉 تم جلب وتصفية وتأكيد عمل ({total_yacine_channels_extracted}) قناة فعالّة كلياً.")


# 5. دمج المحتوى بالترتيب مع قنواتك اليدوية وحفظ وتحديث الـ Gist الخاص بك
final_m3u_content = f"#EXTM3U\n\n{live_separator}\n{live_content}\n\n{basha_separator}\n{basha_content}\n\n{yacine_separator}\n{yacine_content}\n\n# ==================== قنواتك اليدوية والثابتة ====================\n{static_clean}"

print("\n🔐 جاري تحديث الـ Gist الخاص بك...")
update_data = {
    "files": {
        filename: {
            "content": final_m3u_content
        }
    }
}

update_response = requests.patch(gist_api_url, headers=gist_headers, json=update_data)

if update_response.status_code == 200:
    print("🎉 تم التحديث بنجاح! الروابط أصبحت الآن مباشرة، نظيفة وبأسمائها الصحيحة تماماً وجاهزة للعمل.")
else:
    print(f"❌ فشل تحديث الـ Gist. كود الحالة: {update_response.status_code}")
