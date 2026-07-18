import base64
import requests
import json
import time
import os
import re
import random
import urllib.parse
import concurrent.futures
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

# جلب معلومات الـ Gist من متغيرات البيئة الآمنة (GitHub Secrets)
GIST_ID = os.environ.get("GIST_ID")
GITHUB_TOKEN = os.environ.get("GIST_TOKEN")

# إنشاء جلسة عمل مشتركة (Session) للحفاظ على الكوكيز وتفادي الحظر
def create_session():
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

# دالة جلب رابط التوجيه (Redirect)
def get_final_url(raw_url):
    browser_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
    }
    try:
        r_redirect = requests.get(raw_url, headers=browser_headers, allow_redirects=False, timeout=10)
        if r_redirect.status_code in [301, 302]:
            return r_redirect.headers.get('Location')
    except Exception:
        pass
    return raw_url

# دالة جلب قنوات ماجد سبورت
def get_majed_sport_channels(session):
    timestamp = int(time.time() * 1000)
    config_url = f"https://www.majed-koora.live/config.json?v={timestamp}"
    headers = {
        "User-Agent": "MajedSportApp",
        "Accept": "application/json"
    }
    majed_lines = []
    try:
        response = session.get(config_url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            
            stream_keys = {
                "stream_high": "Majed Sport FHD",
                "stream_medium": "Majed Sport HD",
                "stream_low": "Majed Sport SD",
                "stream_reserve": "Majed Sport Reserve 1",
                "stream_reserve2": "Majed Sport Reserve 2"
            }
            
            match_info = ""
            matches = data.get("matches", [])
            if matches:
                first_match = matches[0]
                team1 = first_match.get("team1", "")
                team2 = first_match.get("team2", "")
                comp = first_match.get("comp", "")
                if team1 and team2:
                    match_info = f" - {team1} VS {team2} ({comp})"
            
            vlc_ua = "VLC/3.0.16 LibVLC/3.0.16"
            
            for key, display_name in stream_keys.items():
                stream_url = data.get(key, "").strip()
                if stream_url:
                    stream_url = stream_url.replace("\\/", "/").strip()
                    
                    if "?" in stream_url:
                        stream_url_with_time = f"{stream_url}&v={timestamp}"
                    else:
                        stream_url_with_time = f"{stream_url}?v={timestamp}"
                    
                    full_display_name = f"{display_name}{match_info}"
                    
                    entry = (
                        f'#EXTINF:-1 tvg-logo="" group-title="LIVE", {full_display_name}\n'
                        f'#EXTVLCOPT:http-user-agent={vlc_ua}\n'
                        f'{stream_url_with_time}\n'
                    )
                    majed_lines.append(entry)
                    print(f"      ⚽ تم جلب وتأكيد قناة ماجد سبورت: {full_display_name}")
                    
    except Exception as e:
        print(f"⚠️ فشل جلب باقة ماجد سبورت بسبب: {e}")
    return "".join(majed_lines)

# دالة معالجة وتوحيد النصوص العربية لتفادي اختلاف الإملاء
def normalize_arabic(text):
    if not text:
        return ""
    # تحويل الألف المقصورة والممدودة والهمزات إلى ألف عادية
    text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    # توحيد التاء المربوطة والهاء
    text = text.replace("ة", "ه")
    # إزالة التشكيل وعلامات الإعراب
    text = re.sub(r'[\u064B-\u0652]', '', text)
    return text.strip().lower()

# دالة الفلترة الذكية لمطابقة القنوات المطلوبة بمختلف احتمالات كتابتها
def matches_target_channels(channel_name):
    name_lower = channel_name.lower()
    name_norm = normalize_arabic(channel_name)
    
    # 1. فحص قنوات بيين سبورت وبيين ماكس (العربية والفرنسية والإنجليزية)
    bein_en = ["bein", "be in"]
    bein_ar = ["بين", "بيين", "بي ان"] # تغطي 'بي إن' بعد المعالجة
    is_bein = any(kw in name_lower for kw in bein_en) or any(kw in name_norm for kw in bein_ar)
    
    # 2. فحص قنوات ألوان الرياضية
    alwan_en = ["alwan", "elwan"]
    alwan_ar = ["الوان"] # تغطي 'ألوان' بعد المعالجة
    is_alwan = any(kw in name_lower for kw in alwan_en) or any(kw in name_norm for kw in alwan_ar)
    
    # 3. فحص قنوات الفجر
    fajer_en = ["fajer", "fajr"]
    fajer_ar = ["الفجر", "فجر"]
    is_fajer = any(kw in name_lower for kw in fajer_en) or any(kw in name_norm for kw in fajer_ar)
    
    return is_bein or is_alwan or is_fajer

# دالة جلب وتصفية قنوات باقة SPORT VIP بشكل آمن وسريع (الخيار الأول المطور بالتوازي)
def get_new_app_channels(session):
    sport_vip_lines = []
    seen_urls = set()
    new_app_ua = "Dalvik/2.1.0 (Linux; U; Android 9; SM-S9210 Build/PQ3A.190705.05150936)"
    base_url = "http://go8knm.optikl.ink"
    
    print("   📡 جاري جلب الأقسام الرئيسية لباقة SPORT VIP...")
    groups_url = f"{base_url}/Albsh/api.php?cmd=live"
    headers = {
        "User-Agent": new_app_ua,
        "Accept-Encoding": "gzip",
        "Connection": "Keep-Alive"
    }
    
    try:
        response = session.get(groups_url, headers=headers, timeout=12)
        if response.status_code != 200:
            print(f"⚠️ فشل الاتصال بسيرفر SPORT VIP. كود الاستجابة: {response.status_code}")
            return ""
            
        groups_data = response.json().get("data", [])
        if not groups_data:
            print("⚠️ لم يتم العثور على أي فئات في تطبيق SPORT VIP.")
            return ""
            
        # دالة فرعية لجلب قنوات فئة واحدة
        def fetch_group_channels(group_id, group_title):
            ch_url = f"{base_url}/Albsh/api.php?cmd=get_content&id={group_id}"
            try:
                res = session.get(ch_url, headers=headers, timeout=10)
                if res.status_code == 200:
                    return res.json().get("data", [])
            except Exception:
                pass
            return []
            
        print(f"   ⚡ جاري فحص ومطابقة القنوات بالتوازي لتسريع العملية...")
        all_channels_data = []
        
        # استخدام ThreadPoolExecutor للاتصال المتوازي بجميع الفئات دفعة واحدة
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_group = {
                executor.submit(fetch_group_channels, g.get("id"), g.get("group_title")): g 
                for g in groups_data if g.get("id")
            }
            for future in concurrent.futures.as_completed(future_to_group):
                try:
                    channels_list = future.result()
                    if channels_list:
                        all_channels_data.extend(channels_list)
                except Exception:
                    pass
                    
        # تصفية القنوات واستخراج القنوات المستهدفة فقط
        matched_count = 0
        for ch in all_channels_data:
            if not isinstance(ch, dict):
                continue
                
            ch_name = ch.get("name", "").strip()
            s_url = ch.get("url", "").strip()
            logo = ch.get("logo", "").strip()
            ch_ua = ch.get("user_agent", "").strip() or new_app_ua
            
            if s_url and s_url not in seen_urls:
                if matches_target_channels(ch_name):
                    seen_urls.add(s_url)
                    matched_count += 1
                    
                    # تمرير الـ User Agent المطلوب لتشغيل القناة بنجاح
                    vlc_opts = [f'#EXTVLCOPT:http-user-agent={ch_ua}']
                    vlc_opts_str = "\n".join(vlc_opts)
                    
                    entry = (
                        f'#EXTINF:-1 tvg-logo="{logo}" group-title="SPORT VIP", {ch_name}\n'
                        f'{vlc_opts_str}\n'
                        f'{s_url}\n'
                    )
                    sport_vip_lines.append(entry)
                    
        print(f"      ✔️ تم جلب وتصفية ({matched_count}) قناة بنجاح من باقة SPORT VIP.")
    except Exception as e:
        print(f"⚠️ فشل الاتصال بتطبيق SPORT VIP بسبب: {e}")
        
    return "".join(sport_vip_lines)

# دالة لتصفية واستخراج القنوات اليدوية والثابتة فقط بشكل آمن لحمايتها
def extract_static_channels(m3u_content):
    lines = m3u_content.splitlines()
    static_lines = []
    current_channel_block = []
    
    exclude_keywords = [
        "api.apipremiumcdn.xyz", "yyyylive", "YALLA LIVE",
        "albashatv.site", "playcasta.online", "AL BASHA TV", "majed-koora.live", "modyleech.workers.dev",
        "ycn-redirect", "cinemesh.online", "yacinelive", "YACINE TV", "مجموعة ياسين تيفي",
        "go8knm.optikl.ink", "optikl.ink", "SPORT VIP"
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

# دالة مطابقة قنوات الأطفال المستهدفة بدقة عالية باللغتين لباقة الباشا تيفي
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


# 1. جلب المحتوى الحالي من الـ Gist وتصفية قنواتك اليدوية وحفظها احتياطياً وتطهيرها من المكررات
print("📂 جاري جلب محتوى الـ Gist الحالي للنسخ الاحتياطي وتطهير وتصفية القنوات المكررة...")
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
        print("✔️ تم تنظيف الـ Gist وتحديد وحفظ القنوات اليدوية والثابتة بنجاح.")
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
    "# ==================== مجموعة قنوات SPORT VIP ====================",
    "# ==================== قنوات YALLA LIVE (مباريات جارية) ====================",
    "# ==================== قنواتك اليدوية والثابتة ===================="
]

prev_live = extract_section_by_headers(current_content, headers_list[0], headers_list[1:])
prev_basha = extract_section_by_headers(current_content, headers_list[1], headers_list[2:])
prev_sport_vip = extract_section_by_headers(current_content, headers_list[2], headers_list[3:])
prev_yalla = extract_section_by_headers(current_content, headers_list[3], headers_list[4:])

session = create_session()
final_m3u_content = ""

# 2. كشف وتجهيز باقة قنوات LIVE المباشرة
print("\n⚽ جاري كشف وتجهيز مجموعة قنوات LIVE المباشرة...")
live_separator = "# ==================== مجموعة قنوات LIVE ===================="

live_content = get_majed_sport_channels(session)

# تعويض وقائي ذكي لباقة LIVE في حال عطل الشبكة المؤقت
if not live_content.strip() and prev_live.strip():
    print("🛡️ فشل جلب باقة LIVE، تم استرداد القنوات السابقة بنجاح لحمايتها من الحذف.")
    live_content = prev_live


# 3. جلب وتصفية باقة قنوات الباشا تيفي (Al Basha TV) وتنقيتها لـ VLC والريسيفرات
print("\n🚀 جاري جلب قنوات الباشا تيفي (Al Basha TV)...")
basha_separator = "# ==================== مجموعة قنوات AL BASHA TV ===================="
basha_api_url = "https://albashatv.site/api.php"
basha_headers = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Connection": "Keep-Alive",
    "User-Agent": "okhttp/3.9.1"
}

basha_payloads = ["method=o6&event=view"]
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
                
                basha_ua = channel.get('user_agent', '').strip()
                referer = channel.get('refrens', '').strip()
                cookie = channel.get('cookie', '').strip()
                
                vlc_opts = ["#EXTVLCOPT:http-header=Icy-MetaData: 1"]
                if basha_ua:
                    vlc_opts.append(f'#EXTVLCOPT:http-user-agent={basha_ua}')
                if referer:
                    vlc_opts.append(f'#EXTVLCOPT:http-referrer={referer}')
                if cookie:
                    vlc_opts.append(f'#EXTVLCOPT:http-cookie={cookie}')
                
                vlc_opts_str = "\n".join(vlc_opts)
                
                final_basha_url = re.sub(r'live/+', 'live//', raw_url).strip()
                logo = channel.get('logo', '').strip()
                group_title = "AL BASHA TV"

                kids_match = matches_kids(channel_name)
                if kids_match:
                    entry = f'#EXTINF:-1 tvg-logo="{logo}" group-title="{group_title}", {channel_name}\n'
                    entry += f'{vlc_opts_str}\n'
                    entry += f'{final_basha_url}\n'
                    
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
                    entry = f'#EXTINF:-1 tvg-logo="{logo}" group-title="{group_title}", {channel_name}\n'
                    entry += f'{vlc_opts_str}\n'
                    entry += f'{final_basha_url}\n'
                    
                    regular_channels_list.append(entry)
                    seen_basha_urls.add(raw_url)
                    matched_count += 1
    except Exception as e:
        print(f"❌ خطأ أثناء جلب قنوات الباشا: {e}")

basha_content = "".join(kids_channels_list) + "".join(regular_channels_list)

if not basha_content.strip() and prev_basha.strip():
    print("🛡️ فشل جلب باقة الباشا ديناميكياً، تم استرداد القنوات السابقة بنجاح لحمايتها من الحذف.")
    basha_content = prev_basha
else:
    print(f"🎯 تم استخراج وتصفية ({matched_count}) قناة من الباشا بنجاح.")


# 4. جلب وتصفية باقة قنوات SPORT VIP (بديل ياسين تيفي)
print("\n🚀 جاري جلب وتصفية قنوات باقة SPORT VIP...")
sport_vip_separator = "# ==================== مجموعة قنوات SPORT VIP ===================="

sport_vip_content = get_new_app_channels(session)

# تعويض وقائي ذكي لباقة SPORT VIP في حال حدوث خطأ مؤقت بالشبكة
if not sport_vip_content.strip() and prev_sport_vip.strip():
    print("🛡️ فشل جلب باقة SPORT VIP، تم استرداد القنوات السابقة بنجاح لحمايتها.")
    sport_vip_content = prev_sport_vip


# 5. جلب وتنسيق قنوات Yalla Live للمباريات الجارية حالياً
print("\n🚀 جاري جلب وتحديث باقة قنوات Yalla Live...")
yalla_separator = "# ==================== قنوات YALLA LIVE (مباريات جارية) ===================="

yalla_content = ""
yalla_api_failed = False

yalla_api_url = "https://api.apipremiumcdn.xyz/api/105/all"
yalla_headers = {
    "User-Agent": "Dart/3.11 (dart:io)",
    "Accept": "application/json"
}

yalla_lines = []
try:
    yalla_response = session.get(yalla_api_url, headers=yalla_headers, timeout=12)
    if yalla_response.status_code == 200:
        yalla_data = yalla_response.json()
        match_list = yalla_data.get("List", [])
        
        for match in match_list:
            if match.get("live") and match.get("started") and not match.get("finished"):
                server_val = str(match.get("server", "s")).lower().strip()
                channel_name = match.get("sound", "beIN Max")
                team1 = match.get("name1", "Team 1")
                team2 = match.get("name2", "Team 2")
                league = match.get("ligue", "Live Match")
                
                num_match = re.findall(r'\d+', server_val)
                server_num = num_match[0] if num_match else "1"
                
                stream_url = f"https://yyyylive{server_num}.blob.core.windows.net/live/stream/index.fmp4.m3u8"
                display_name = f"{channel_name} - {team1} VS {team2} ({league})"
                
                entry = (
                    f'#EXTINF:-1 tvg-logo="" group-title="YALLA LIVE (مباريات جارية)", {display_name}\n'
                    f'{stream_url}\n'
                )
                yalla_lines.append(entry)
                print(f"      ⚽ تم اكتشاف مباراة جارية وإضافة بثها المباشر الفعال: {display_name}")
        
        yalla_content = "".join(yalla_lines)
        if not yalla_content.strip():
            print("      ℹ️ لا توجد مباريات جارية حالياً في التطبيق (تم إبقاء القسم نظيفاً للـ M3U).")
    else:
        print(f"⚠️ استجابة سيرفر Yalla Live خاطئة: {yalla_response.status_code}")
        yalla_api_failed = True
except Exception as e:
    print(f"⚠️ فشل الاتصال بسيرفر Yalla Live بسبب: {e}")
    yalla_api_failed = True

if yalla_api_failed and prev_yalla.strip():
    print("🛡️ فشل جلب باقة Yalla Live بسبب عطل بالشبكة، تم استرداد الحالة السابقة من الـ Gist لحمايتها.")
    yalla_content = prev_yalla


# 6. دمج المحتوى بالترتيب مع قنواتك اليدوية وحفظ وتحديث الـ Gist
final_m3u_content = f"#EXTM3U\n\n{live_separator}\n{live_content}\n\n{basha_separator}\n{basha_content}\n\n{sport_vip_separator}\n{sport_vip_content}\n\n{yalla_separator}\n{yalla_content}\n\n# ==================== قنواتك اليدوية والثابتة ====================\n{static_clean}"

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
    print("🎉 تم التحديث بنجاح! الروابط أصبحت الآن مباشرة وجاهزة للعمل بالصوت والصورة على كافة أجهزة منزلك ومنزل والدك وباسم باقة SPORT VIP.")
else:
    print(f"❌ فشل تحديث الـ Gist. كود الحالة: {update_response.status_code}")
