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
    except Exception as e:
        print(f"Error decrypting Yacine: {e}")
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

# دالة تنظيف وتقشير روابط الباشا لتصبح متوافقة مع أجهزة الاستقبال
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

# دالة ذكية لتصنيف قنوات DEJLA TV في المجموعات المطلوبة بالترتيب
def get_dejla_group(channel_name):
    name_lower = channel_name.lower()
    
    # 1. beIN MAX
    if "bein max" in name_lower:
        return 1
    # 2. beIN SPORT
    if "bein sport" in name_lower:
        return 2
    # 3. beIN (بقية قنوات بين الترفيهية أو الإخبارية)
    if "bein" in name_lower:
        return 3
    # 4. OSN / AMAZON PRIME / NETFLIX / BOX OFFICE / HBO / ROTANA / MBC / GOBX
    ent_keywords = ["osn", "amazon", "netflix", "neflix", "box office", "boxe office", "hbo", "rotana", "روتانا", "mbc", "gobx"]
    if any(kw in name_lower for kw in ent_keywords):
        return 4
    # 5. FRANCE
    if "france" in name_lower or re.search(r'\bfr\b', name_lower) or "|fr|" in name_lower or "fr:" in name_lower:
        return 5
    # 6. ALGERIA
    if "algeria" in name_lower or "الجزائر" in name_lower or re.search(r'\bdz\b', name_lower) or "|dz|" in name_lower or "dz:" in name_lower:
        return 6
    # 7. KIDS
    kids_keywords = ["kids", "kid", "cartoon", "disney", "nickelodeon", "براعم", "اطفال", "أطفال", "ماجد", "space toon", "spacetoon"]
    if any(kw in name_lower for kw in kids_keywords):
        return 7
        
    return None # القنوات غير المطابقة للشروط لن تضاف لمنع تراكم قنوات لا تهمك

# دالة لتصفية واستخراج القنوات اليدوية الثابتة فقط من الـ Gist الحالي بشكل آمن
def extract_static_channels(m3u_content):
    lines = m3u_content.splitlines()
    static_lines = []
    current_channel_block = []
    
    exclude_keywords = [
        "foxbleu.org", "used4.fun", "albashatv.site", "playcasta.online", 
        "def.yacinelive.com", "metava.online", "re.ycn-redirect.com", 
        "BEIN MAX YACINE TV", "AL BASHA TV", "DEJLA TV"
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

# 1. جلب محتوى الـ Gist واستخلاص قنواتك الثابتة
print("📂 جاري جلب محتوى الـ Gist لتأمين قنواتك اليدوية...")
gist_api_url = f"https://api.github.com/gists/{GIST_ID}"
gist_headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}
static_clean = ""
filename = "kz.m3u"

try:
    gist_response = requests.get(gist_api_url, headers=gist_headers, timeout=15)
    if gist_response.status_code == 200:
        gist_data = gist_response.json()
        filename = list(gist_data['files'].keys())[0]
        current_content = gist_data['files'][filename]['content']
        static_clean = extract_static_channels(current_content)
        print("✔️ تم عزل وحفظ القنوات اليدوية الثابتة بنجاح.")
    else:
        print(f"❌ فشل جلب الـ Gist. كود الحالة: {gist_response.status_code}")
        exit(1)
except Exception as e:
    print(f"❌ خطأ أثناء الاتصال بـ Gist API: {e}")
    exit(1)

session = create_session()

# ==================== (أ) جلب وتحديث قنوات DEJLA TV بالترتيب المحدد ====================
print("\n🚀 جاري جلب وترتيب باقة DEJLA TV...")
dejla_separator = "# ==================== مجموعة قنوات DEJLA TV ===================="
api_url = "http://used4.fun/api/Getappuser.php"
api_headers = {"Content-Type": "application/json; charset=utf-8", "User-Agent": "smart-tv"}

# تشفير الماك أدرس لاستخراج رابط الـ M3U المباشر من السيرفر
mac_address = "5e:0f:fa:6d:d2:48"
mac_clean = mac_address.replace(":", "").lower()
mac_b64_1 = base64.b64encode(mac_clean.encode('utf-8')).decode('utf-8')
mac_b64_2 = base64.b64encode(mac_b64_1.encode('utf-8')).decode('utf-8')

request_payload = {"app_device_id": mac_b64_2, "app_type": "tv", "version": "1.0", "is_paid": True}
request_json_str = json.dumps(request_payload, separators=(',', ':'))
encrypted_request = base64.b64encode(request_json_str.encode('utf-8')).decode('utf-8')

m3u_url = ""
try:
    response = session.post(api_url, json={"data": encrypted_request}, headers=api_headers, timeout=15)
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

# إنشاء تصنيفات منفصلة للترتيب
dejla_groups = {1: "", 2: "", 3: "", 4: "", 5: "", 6: "", 7: ""}

try:
    m3u_response = session.get(m3u_url, headers={"User-Agent": "Ibo Pro Ultra 3.9"}, timeout=30)
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
                    # فحص اسم القناة لمعرفة مجموعتها
                    channel_name = current_inf.split(",")[-1]
                    group_id = get_dejla_group(channel_name)
                    
                    if group_id:
                        # تعديل الرابط ليتوافق مع الريسيفر
                        final_url = f"{line_stripped}|User-Agent=Ibo Pro Ultra 3.9"
                        
                        # استبدال اسم المجموعة الأصلي باسم DEJLA TV للظهور في الريسيفر
                        clean_inf = re.sub(r'group-title="[^"]*"', 'group-title="DEJLA TV"', current_inf)
                        
                        dejla_groups[group_id] += f"{clean_inf}\n{final_url}\n"
                    current_inf = ""
except Exception as e:
    print(f"❌ خطأ أثناء معالجة باقة DEJLA TV: {e}")

# دمج باقة دجلة حسب الترتيب المطلوب بدقة
dejla_content = (
    dejla_groups[1] + # beIN MAX
    dejla_groups[2] + # beIN SPORT
    dejla_groups[3] + # beIN Others
    dejla_groups[4] + # OSN/Netflix/HBO...
    dejla_groups[5] + # France
    dejla_groups[6] + # Algeria
    dejla_groups[7]   # Kids
)

# ==================== (ب) جلب وتحديث باقة الباشا تيفي ====================
print("\n🚀 جاري جلب وتحديث قنوات الباشا تيفي...")
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
except Exception as e:
    print(f"❌ خطأ أثناء جلب قنوات الباشا: {e}")

# ==================== (ج) جلب وتحديث باقة ياسين تيفي ====================
print("\n🚀 جاري جلب وتحديث قنوات ياسين تيفي...")
yacine_separator = "# ==================== مجموعة قنوات BEIN MAX YACINE TV ===================="
yacine_targets = {
    "https://def.yacinelive.com/api/categories/90/channels": "FHD",
    "https://def.yacinelive.com/api/categories/89/channels": "HD"
}
yacine_headers = {"Accept": "application/json", "User-Agent": "okhttp/4.12.0"}
ua_value = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
referer_value = "http://re.ycn-redirect.com/"

yacine_content = ""
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
                if streams:
                    raw_url = streams[0].get('url')
                    final_url = get_final_url(raw_url)
                    final_url_with_headers = f"{final_url}|User-Agent={ua_value}&Referer={referer_value}"
                    display_name = f"{channel_name} {quality}"
                    yacine_content += f'#EXTINF:-1 tvg-logo="" group-title="BEIN MAX YACINE TV", {display_name}\n'
                    yacine_content += f'{final_url_with_headers}\n'
            time.sleep(0.3)

# دمج جميع الأقسام مع الحفاظ على قنواتك اليدوية في الأسفل
final_m3u_content = (
    f"#EXTM3U\n\n"
    f"{dejla_separator}\n{dejla_content}\n\n"
    f"{basha_separator}\n{basha_content}\n\n"
    f"{yacine_separator}\n{yacine_content}\n\n"
    f"# ==================== قنواتك اليدوية والثابتة ====================\n{static_clean}"
)

# 5. تحديث الـ Gist
print("\n🔐 جاري تحديث الـ Gist بالترتيب والشروط الجديدة...")
update_data = {"files": {filename: {"content": final_m3u_content}}}
update_response = requests.patch(gist_api_url, headers=gist_headers, json=update_data)

if update_response.status_code == 200:
    print("🎉 تم التحديث بنجاح! تم تطبيق الترتيب وتحديث جميع الباقات وحماية قنواتك الخاصة.")
else:
    print(f"❌ فشل تحديث الـ Gist. كود الحالة: {update_response.status_code}")
