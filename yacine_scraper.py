import base64
import requests
import json
import time
import os
import urllib.parse
import re
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

# جلب معلومات الـ Gist من متغيرات البيئة الآمنة (GitHub Secrets)
GIST_ID = os.environ.get("GIST_ID")
GITHUB_TOKEN = os.environ.get("GIST_TOKEN")

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
    except Exception:
        return None

# إنشاء جلسة عمل مشتركة (Session) للحفاظ على الاتصال وتفادي الحظر
def create_session():
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

# دالة للاتصال بسيرفر ياسين وفك التشفير تلقائياً
def fetch_and_decrypt_yacine(session, url, headers):
    try:
        response = session.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            t_value = response.headers.get('T') or response.headers.get('t')
            if t_value:
                decrypted_json_str = decrypt_yacine(response.text, t_value)
                if decrypted_json_str:
                    return json.loads(decrypted_json_str)
    except Exception:
        pass
    return None

# دالة جلب رابط التوجيه (Redirect) لياسين تيفي
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

# دالة تنظيف وتقشير روابط الباشا
def clean_and_extract_url(raw_url):
    if not raw_url:
        return raw_url
    if "?url=" in raw_url:
        parsed_url = urllib.parse.urlparse(raw_url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        if 'url' in query_params:
            raw_url = query_params['url'][0]
    if "://" in raw_url:
        scheme, rest = raw_url.split("://", 1)
        parts = [p for p in rest.split("/") if p]
        normalized_rest = "/".join(parts)
        return f"{scheme}://{normalized_rest}"
    return raw_url

# دالة لاختيار البث الأفضل والأعلى جودة لقنوات ياسين تيفي وتجنب الجودات الضعيفة
def select_best_yacine_stream(streams, target_quality):
    if not streams:
        return None
    
    target_lower = target_quality.lower() # فحص الجودة المطلوبة (fhd أو hd)
    
    # محاولة جلب السيرفر الذي يطابق الجودة المطلوبة بالاسم
    for stream in streams:
        stream_name = str(stream.get("name", "")).lower()
        if target_lower in stream_name or (target_lower == "fhd" and "1080" in stream_name) or (target_lower == "hd" and "720" in stream_name):
            return stream
            
    # في حال طلب جودة FHD ولم نجدها، نبحث عن جودة HD كبديل أول
    if target_lower == "fhd":
        for stream in streams:
            stream_name = str(stream.get("name", "")).lower()
            if "hd" in stream_name or "720" in stream_name:
                return stream
                
    # كخيار أخير في حال عدم مطابقة الشروط، نعود للسيرفر الأول المتاح تلقائياً
    return streams[0]

# دالة استخراج الأقسام الحالية من الـ Gist لاستخدامها كنسخ احتياطية في حال الفشل
def get_section_content(m3u_text, header_marker):
    lines = m3u_text.splitlines()
    section_lines = []
    capture = False
    for line in lines:
        line_stripped = line.strip()
        if header_marker in line_stripped:
            capture = True
            continue
        if capture:
            if line_stripped.startswith("# ===================="):
                break
            section_lines.append(line)
    return "\n".join(section_lines).strip()

# دالة الفلترة الاحتياطية للقنوات اليدوية الثابتة
def extract_static_channels(m3u_content):
    lines = m3u_content.splitlines()
    static_lines = []
    current_channel_block = []
    exclude_keywords = [
        "foxbleu.org", "used4.fun", "albashatv.site", "playcasta.online", 
        "def.yacinelive.com", "metava.online", "re.ycn-redirect.com", 
        "BEIN MAX YACINE TV", "AL BASHA TV", "DEJLA TV", "majed-koora.live"
    ]
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped or line_stripped.startswith("#EXTM3U") or "=====" in line_stripped:
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

# دالة تصنيف قنوات DEJLA TV حسب الترتيب المطلوب
def get_dejla_group(channel_name):
    name_lower = channel_name.lower()
    if "bein max" in name_lower:
        return 1
    if "bein sport" in name_lower:
        return 2
    if "bein" in name_lower:
        return 3
    ent_keywords = ["osn", "amazon", "netflix", "neflix", "box office", "boxe office", "hbo", "rotana", "روتانا", "mbc", "gobx"]
    if any(kw in name_lower for kw in ent_keywords):
        return 4
    if "france" in name_lower or re.search(r'\bfr\b', name_lower) or "|fr|" in name_lower or "fr:" in name_lower:
        return 5
    if "algeria" in name_lower or "الجزائر" in name_lower or re.search(r'\bdz\b', name_lower) or "|dz|" in name_lower or "dz:" in name_lower:
        return 6
    kids_keywords = ["kids", "kid", "cartoon", "disney", "nickelodeon", "براعم", "اطفال", "أطفال", "ماجد", "space toon", "spacetoon"]
    if any(kw in name_lower for kw in kids_keywords):
        return 7
    return None

# دالة ديناميكية لجلب وتحديث رابط بث "ماجد كورة"
def get_majed_koora_stream(session):
    config_url = "https://www.majed-koora.live/config.json"
    try:
        ts = int(time.time() * 1000)
        response = session.get(f"{config_url}?v={ts}", timeout=10)
        if response.status_code == 200:
            config_data = response.json()
            channel_id = None
            
            if isinstance(config_data, dict):
                for k, v in config_data.items():
                    if k.lower() in ["channel", "mamam", "live", "current"]:
                        channel_id = v
                        break
                if not channel_id:
                    for v in config_data.values():
                        if isinstance(v, str) and len(v) < 25:
                            channel_id = v
                            break
            elif isinstance(config_data, list) and len(config_data) > 0:
                channel_id = config_data[0].get("channel")
            
            if channel_id:
                ua = "VLC/3.0.16 LibVLC/3.0.16"
                return f"https://majed-koora.live/stream.php?channel={channel_id}&file=stream.m3u8|User-Agent={ua}"
    except Exception as e:
        print(f"⚠️ خطأ أثناء تحديث كود ماجد كورة: {e}")
    return "https://majed-koora.live/stream.php?channel=mamam991&file=stream.m3u8|User-Agent=VLC/3.0.16 LibVLC/3.0.16"


# 1. جلب المحتوى الحالي من الـ Gist واستخلاص النسخ الاحتياطية للأمان
print("📂 جاري جلب محتوى الـ Gist الحالي للتحليل وتأمين البيانات...")
gist_api_url = f"https://api.github.com/gists/{GIST_ID}"
gist_headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}
filename = "kz.m3u"
current_content = ""

try:
    gist_response = requests.get(gist_api_url, headers=gist_headers, timeout=15)
    if gist_response.status_code == 200:
        gist_data = gist_response.json()
        filename = list(gist_data['files'].keys())[0]
        current_content = gist_data['files'][filename]['content']
    else:
        print(f"❌ فشل الاتصال بـ Gist API.")
        exit(1)
except Exception as e:
    print(f"❌ خطأ: {e}")
    exit(1)

# استخراج النسخ الاحتياطية الحالية لمنع المسح التلقائي في حال توقف أي سيرفر
old_dejla = get_section_content(current_content, "DEJLA TV")
old_basha = get_section_content(current_content, "AL BASHA TV")
old_yacine = get_section_content(current_content, "BEIN MAX YACINE TV")
old_live = get_section_content(current_content, "LIVE")
static_clean = get_section_content(current_content, "قنواتك اليدوية والثابتة")

if not static_clean:
    static_clean = extract_static_channels(current_content)

session = create_session()

# ==================== (أ) جلب وتحديث قنوات ماجد كورة (LIVE) ====================
print("\n🚀 جاري تحديث بث ماجد كورة المباشر...")
live_separator = "# ==================== مجموعة قنوات LIVE ===================="
live_content = ""
new_live_url = get_majed_koora_stream(session)

if new_live_url:
    live_content = f'#EXTINF:-1 tvg-logo="" group-title="LIVE", Majed Koora Live\n{new_live_url}'
else:
    live_content = old_live if old_live else f'#EXTINF:-1 tvg-logo="" group-title="LIVE", Majed Koora Live\nhttps://majed-koora.live/stream.php?channel=mamam991&file=stream.m3u8|User-Agent=VLC/3.0.16 LibVLC/3.0.16'

# ==================== (ب) جلب وتحديث قنوات DEJLA TV ====================
print("\n🚀 جاري جلب وترتيب باقة DEJLA TV المباشرة...")
dejla_separator = "# ==================== مجموعة قنوات DEJLA TV ===================="
m3u_url = ""

# تشفير الماك أدرس لتوليد رابط القنوات المباشر
mac_address = "5e:0f:fa:6d:d2:48"
mac_clean = mac_address.replace(":", "").lower()
mac_b64_1 = base64.b64encode(mac_clean.encode('utf-8')).decode('utf-8')
mac_b64_2 = base64.b64encode(mac_b64_1.encode('utf-8')).decode('utf-8')

request_payload = {"app_device_id": mac_b64_2, "app_type": "tv", "version": "1.0", "is_paid": True}
request_json_str = json.dumps(request_payload, separators=(',', ':'))
encrypted_request = base64.b64encode(request_json_str.encode('utf-8')).decode('utf-8')

try:
    response = session.post("http://used4.fun/api/Getappuser.php", json={"data": encrypted_request}, headers={"Content-Type": "application/json", "User-Agent": "smart-tv"}, timeout=15)
    if response.status_code == 200:
        res_json = response.json()
        if "data" in res_json:
            decrypted_res = json.loads(base64.b64decode(res_json["data"]).decode('utf-8'))
            if "urls" in decrypted_res and len(decrypted_res["urls"]) > 0:
                m3u_url = decrypted_res["urls"][0].get("url")
except Exception:
    pass

if not m3u_url:
    m3u_url = "http://foxbleu.org:8789/get.php?username=ludovic&password=8333&type=m3u_plus&output=ts"

dejla_groups = {1: "", 2: "", 3: "", 4: "", 5: "", 6: "", 7: ""}
dejla_content = ""

try:
    m3u_response = session.get(m3u_url, timeout=30)
    if m3u_response.status_code == 200:
        lines = m3u_response.text.splitlines()
        current_inf = ""
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped or line_stripped.startswith("#EXTM3U"):
                continue
            if line_stripped.startswith("#EXTINF"):
                current_inf = line_stripped
            elif not line_stripped.startswith("#"):
                if current_inf:
                    channel_name = current_inf.split(",")[-1]
                    group_id = get_dejla_group(channel_name)
                    if group_id:
                        # روابط DEJLA لا تحتاج ترويسات مشفرة وتعمل مباشرة وممتازة بدون أنبوب
                        clean_inf = re.sub(r'group-title="[^"]*"', 'group-title="DEJLA TV"', current_inf)
                        dejla_groups[group_id] += f"{clean_inf}\n{line_stripped}\n"
                    current_inf = ""
        
        dejla_content = (
            dejla_groups[1] + # BEIN MAX
            dejla_groups[2] + # BEIN SPORT
            dejla_groups[3] + # Any BEIN
            dejla_groups[4] + # OSN / Netflix / HBO...
            dejla_groups[5] + # FRANCE
            dejla_groups[6] + # ALGERIA
            dejla_groups[7]   # KIDS
        ).strip()
except Exception as e:
    print(f"❌ خطأ في سحب DEJLA TV: {e}")

if not dejla_content:
    print("⚠️ تم استعادة قنوات DEJLA TV القديمة مؤقتاً.")
    dejla_content = old_dejla

# ==================== (ج) جلب وتحديث قنوات الباشا تيفي ====================
print("\n🚀 جاري جلب قنوات الباشا تيفي (Al Basha TV)...")
basha_separator = "# ==================== مجموعة قنوات AL BASHA TV ===================="
basha_api_url = "https://albashatv.site/api.php"
basha_headers = {"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "okhttp/3.9.1"}
basha_payload = "method=o6&event=view"
basha_targets = ["bein max", "bein sport", "osn", "netflix", "bein media", "hbo", "amazon prime", "amazon"]

basha_content = ""
try:
    basha_response = session.post(basha_api_url, headers=basha_headers, data=basha_payload, timeout=15)
    if basha_response.status_code == 200:
        basha_channels = basha_response.json()
        for channel in basha_channels:
            channel_name = channel.get('name', '')
            raw_url = channel.get('url', '')
            channel_name_lower = channel_name.lower()
            if any(target in channel_name_lower for target in basha_targets):
                cleaned_url = clean_and_extract_url(raw_url)
                basha_content += f'#EXTINF:-1 tvg-logo="" group-title="AL BASHA TV", {channel_name}\n'
                basha_content += f'{cleaned_url}\n'
        basha_content = basha_content.strip()
except Exception:
    pass

if not basha_content:
    print("⚠️ تم استعادة قنوات الباشا القديمة.")
    basha_content = old_basha

# ==================== (د) جلب وتحديث قنوات ياسين تيفي بجودات عالية (FHD / HD) ====================
print("\n🚀 جاري جلب قنوات ياسين تيفي (Yacine TV)...")
yacine_separator = "# ==================== مجموعة قنوات BEIN MAX YACINE TV ===================="
yacine_targets = {
    "https://def.yacinelive.com/api/categories/90/channels": "FHD",
    "https://def.yacinelive.com/api/categories/89/channels": "HD"
}
yacine_headers = {"Accept": "application/json", "User-Agent": "okhttp/4.12.0"}
ua_value = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
referer_value = "http://re.ycn-redirect.com/"

yacine_content = ""
try:
    for category_url, quality in yacine_targets.items():
        channels_data = fetch_and_decrypt_yacine(session, category_url, yacine_headers)
        if channels_data and 'data' in channels_data:
            channels_list = channels_data['data']
            for channel in channels_list:
                channel_name = channel.get('name')
                channel_id = channel.get('id')
                channel_detail_url = f"https://def.yacinelive.com/api/channel/{channel_id}"
                detail_data = fetch_and_decrypt_yacine(session, channel_detail_url, yacine_headers)
                if detail_data and 'data' in detail_data:
                    streams = detail_data['data']
                    
                    # اختيار البث الأفضل والأعلى جودة بدلاً من أخذ السيرفر الأول عشوائياً
                    best_stream = select_best_yacine_stream(streams, quality)
                    if best_stream:
                        raw_url = best_stream.get('url')
                        final_url = get_final_url(raw_url)
                        final_url_with_headers = f"{final_url}|User-Agent={ua_value}&Referer={referer_value}"
                        
                        actual_quality = best_stream.get("name", quality)
                        display_name = f"{channel_name} {actual_quality}"
                        
                        yacine_content += f'#EXTINF:-1 tvg-logo="" group-title="BEIN MAX YACINE TV", {display_name}\n'
                        yacine_content += f'{final_url_with_headers}\n'
                time.sleep(0.3)
    yacine_content = yacine_content.strip()
except Exception as e:
    print(f"❌ خطأ أثناء معالجة باقة ياسين تيفي: {e}")

if not yacine_content:
    print("⚠️ تم استعادة قنوات ياسين القديمة.")
    yacine_content = old_yacine

# دمج المحتوى الكلي بشكل آمن ومرتب ومحمي بالكامل
final_m3u_content = (
    f"#EXTM3U\n\n"
    f"{live_separator}\n{live_content}\n\n"
    f"{dejla_separator}\n{dejla_content}\n\n"
    f"{basha_separator}\n{basha_content}\n\n"
    f"{yacine_separator}\n{yacine_content}\n\n"
    f"# ==================== قنواتك اليدوية والثابتة ====================\n{static_clean}"
)

# 5. تحديث الـ Gist
print("\n🔐 جاري حفظ وتحديث الـ Gist بنظام الأمان الشامل...")
update_data = {"files": {filename: {"content": final_m3u_content}}}
update_response = requests.patch(gist_api_url, headers=gist_headers, json=update_data)

if update_response.status_code == 200:
    print("🎉 تم التحديث بنجاح! تم ترقية جودة قنوات ياسين تيفي إلى FHD/HD وباقي الميزات تعمل بكفاءة.")
else:
    print(f"❌ فشل تحديث الـ Gist. كود الحالة: {update_response.status_code}")
