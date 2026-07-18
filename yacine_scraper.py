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

# مستودع عالمي موحد لمنع تكرار أي رابط نهائياً في ملف M3U بأكمله
global_seen_urls = set()

# إنشاء جلسة عمل مشتركة (Session) للحفاظ على الكوكيز وتفادي الحظر
def create_session():
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

# دالة ذكية لتتبع رابط التوجيه (302 Redirect) دون تحميل تدفق البث لتجنب تعليق السكربت
def get_final_url(raw_url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
    }
    try:
        # allow_redirects=False تضمن الحصول على رأس التوجيه Location فوراً في أجزاء من الثانية دون تنزيل ملف البث
        response = requests.get(raw_url, headers=headers, allow_redirects=False, timeout=8)
        if response.status_code in [301, 302, 303, 307, 308]:
            return response.headers.get('Location', raw_url)
    except Exception:
        pass
    return raw_url

# دالة جلب قنوات ماجد سبورت
def get_majed_sport_channels(session):
    global global_seen_urls
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
                    
                    if stream_url_with_time not in global_seen_urls:
                        global_seen_urls.add(stream_url_with_time)
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
    text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    text = text.replace("ة", "ه")
    text = re.sub(r'[\u064B-\u0652]', '', text)
    return text.strip().lower()

# دالة الفلترة الذكية لمطابقة القنوات المطلوبة بمختلف احتمالات كتابتها
def matches_target_channels(channel_name):
    name_lower = channel_name.lower()
    name_norm = normalize_arabic(channel_name)
    
    bein_en = ["bein", "be in"]
    bein_ar = ["بين", "بيين", "بي ان"]
    is_bein = any(kw in name_lower for kw in bein_en) or any(kw in name_norm for kw in bein_ar)
    
    alwan_en = ["alwan", "elwan"]
    alwan_ar = ["الوان"]
    is_alwan = any(kw in name_lower for kw in alwan_en) or any(kw in name_norm for kw in alwan_ar)
    
    fajer_en = ["fajer", "fajr"]
    fajer_ar = ["الفجر", "فجر"]
    is_fajer = any(kw in name_lower for kw in fajer_en) or any(kw in name_norm for kw in fajer_ar)
    
    return is_bein or is_alwan or is_fajer

# دالة جلب وتصفية قنوات باقة SPORT VIP الجديدة كلياً والمستقلة من الصفر بالتوازي
def get_sport_vip_channels(session):
    global global_seen_urls
    sport_vip_lines = []
    new_app_ua = "Dalvik/2.1.0 (Linux; U; Android 9; SM-S9210 Build/PQ3A.190705.05150936)"
    base_url = "http://go8knm.optikl.ink"
    
    print("   📡 جاري جلب الأقسام الرئيسية لباقة SPORT VIP...")
    main_url = f"{base_url}/rez/api.php?action=main"
    headers = {
        "User-Agent": new_app_ua,
        "Accept-Encoding": "gzip",
        "Connection": "Keep-Alive"
    }
    
    try:
        response = session.get(main_url, headers=headers, timeout=12)
        if response.status_code != 200:
            print(f"⚠️ فشل الاتصال بسيرفر SPORT VIP. كود الاستجابة: {response.status_code}")
            return ""
            
        resp_json = response.json()
        if resp_json.get("status") != "success":
            print("⚠️ استجابة غير صالحة من سيرفر SPORT VIP.")
            return ""
            
        groups_data = resp_json.get("data", [])
        if not groups_data:
            print("⚠️ لم يتم العثور على أي فئات في تطبيق SPORT VIP.")
            return ""
            
        # دالة فرعية لجلب قنوات فئة واحدة باستخدام معرفها (cat_id)
        def fetch_category_channels(cat_id, cat_name):
            ch_url = f"{base_url}/rez/api.php?action=category&cat_id={cat_id}"
            try:
                res = session.get(ch_url, headers=headers, timeout=10)
                if res.status_code == 200:
                    return res.json().get("data", [])
            except Exception:
                pass
            return []
            
        print(f"   ⚡ جاري فحص ومطابقة قنوات الفئات بالتوازي لتسريع العملية...")
        all_channels_data = []
        
        # الاتصال بالتوازي بجميع فئات السيرفر دفعة واحدة
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_cat = {
                executor.submit(fetch_category_channels, g.get("id"), g.get("name")): g 
                for g in groups_data if g.get("id")
            }
            for future in concurrent.futures.as_completed(future_to_cat):
                try:
                    channels_list = future.result()
                    if channels_list:
                        all_channels_data.extend(channels_list)
                except Exception:
                    pass
                    
        matched_count = 0
        for ch in all_channels_data:
            if not isinstance(ch, dict):
                continue
                
            ch_name = ch.get("name", "").strip()
            raw_stream_url = ch.get("url", "").strip() or ch.get("stream_url", "").strip()
            logo = ch.get("image", "").strip() or ch.get("logo", "").strip()
            
            if raw_stream_url:
                if matches_target_channels(ch_name):
                    # حل التوجيه برمجياً للحصول على رابط البث الفعلي .ts وتمريره للملف مباشرة
                    final_stream_url = get_final_url(raw_stream_url)
                    
                    if final_stream_url and final_stream_url not in global_seen_urls:
                        global_seen_urls.add(final_stream_url)
                        matched_count += 1
                        
                        vlc_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                        
                        entry = (
                            f'#EXTINF:-1 tvg-logo="{logo}" group-title="SPORT VIP", {ch_name}\n'
                            f'#EXTVLCOPT:http-user-agent={vlc_ua}\n'
                            f'{final_stream_url}\n'
                        )
                        sport_vip_lines.append(entry)
                        
        print(f"      ✔️ تم جلب وتصفية ({matched_count}) قناة بنجاح من باقة SPORT VIP دون تكرار.")
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
        "go8knm.optikl.ink", "optikl.ink", "SPORT VIP", "redperch.space"
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


# 1. جلب المحتوى الحالي من الـ Gist وتصفية قنواتك اليدوية وحفظها احتياطياً
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

# ترويسات الأقسام بعد إزالة الباشا وياسين تيفي لضمان الفصل التام
headers_list = [
    "# ==================== مجموعة قنوات LIVE ====================",
    "# ==================== مجموعة قنوات SPORT VIP ====================",
    "# ==================== قنوات YALLA LIVE (مباريات جارية) ====================",
    "# ==================== قنواتك اليدوية والثابتة ===================="
]

prev_live = extract_section_by_headers(current_content, headers_list[0], headers_list[1:])
prev_sport_vip = extract_section_by_headers(current_content, headers_list[1], headers_list[2:])
prev_yalla = extract_section_by_headers(current_content, headers_list[2], headers_list[3:])

session = create_session()
final_m3u_content = ""

# 2. كشف وتجهيز باقة قنوات LIVE المباشرة
print("\n⚽ جاري كشف وتجهيز مجموعة قنوات LIVE المباشرة...")
live_separator = "# ==================== مجموعة قنوات LIVE ===================="

live_content = get_majed_sport_channels(session)

if not live_content.strip() and prev_live.strip():
    print("🛡️ فشل جلب باقة LIVE، تم استرداد القنوات السابقة بنجاح لحمايتها من الحذف.")
    live_content = prev_live


# 3. جلب وتصفية باقة قنوات SPORT VIP (المستقلة كلياً)
print("\n🚀 جاري جلب وتصفية قنوات باقة SPORT VIP...")
sport_vip_separator = "# ==================== مجموعة قنوات SPORT VIP ===================="

sport_vip_content = get_sport_vip_channels(session)

if not sport_vip_content.strip() and prev_sport_vip.strip():
    print("🛡️ فشل جلب باقة SPORT VIP، تم استرداد القنوات السابقة بنجاح لحمايتها.")
    sport_vip_content = prev_sport_vip


# 4. جلب وتنسيق قنوات Yalla Live للمباريات الجارية حالياً
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
                
                if stream_url not in global_seen_urls:
                    global_seen_urls.add(stream_url)
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


# 5. دمج المحتوى بالترتيب مع قنواتك اليدوية وحفظ وتحديث الـ Gist الخاص بك
final_m3u_content = f"#EXTM3U\n\n{live_separator}\n{live_content}\n\n{sport_vip_separator}\n{sport_vip_content}\n\n{yalla_separator}\n{yalla_content}\n\n# ==================== قنواتك اليدوية والثابتة ====================\n{static_clean}"

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
    print("🎉 تم التحديث بنجاح! السكربت نظيف، مستقل، وخالٍ تماماً من التداخل أو التكرار مع أي سيرفرات أخرى.")
else:
    print(f"❌ فشل تحديث الـ Gist. كود الحالة: {update_response.status_code}")
