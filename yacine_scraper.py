import base64
import requests
import json
import time
import os
import re
import urllib.parse
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

# إنشاء جلسة عمل مشتركة (Session) للحفاظ على الكوكيز وتفادي الحظر
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

# دالة لتصفية واستخراج القنوات اليدوية والثابتة فقط بشكل آمن
def extract_static_channels(m3u_content):
    lines = m3u_content.splitlines()
    static_lines = []
    current_channel_block = []
    
    exclude_keywords = [
        "def.yacinelive.com", "metava.online", "re.ycn-redirect.com", "BEIN MAX YACINE TV",
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

# دالة مخصصة لفلترة القنوات العربية والفرنسية فقط لقنوات الباشا
def is_arabic_or_french(name):
    name_lower = name.lower()
    # 1. التحقق من وجود حروف عربية
    if re.search(r'[\u0600-\u06FF]', name):
        return True
    # 2. الكلمات الدلالية للقنوات العربية الرياضية والترفيهية بالإنجليزية
    arabic_keywords = ["bein", "osn", "mbc", "ssc", "shahid", "art", "rotana", "al jazeera", "vip", "basha", "ar:"]
    if any(kw in name_lower for kw in arabic_keywords):
        return True
    # 3. الكلمات الدلالية للقنوات الفرنسية
    french_keywords = ["fr:", "fr ", "(fr)", "[fr]", "france", "canal+", "canal plus", "rmc", "tf1", "m6", "ocs", "ciné+", "cine+"]
    if any(kw in name_lower for kw in french_keywords):
        return True
    return False

# 1. جلب المحتوى الحالي من الـ Gist وتصفية قنواتك اليدوية
print("📂 جاري جلب محتوى الـ Gist الحالي...")
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
        print("✔️ تم تحديد القنوات اليدوية وحفظها.")
    else:
        print(f"❌ فشل جلب الـ Gist الحالي. كود الحالة: {gist_response.status_code}")
        exit(1)
except Exception as e:
    print(f"❌ خطأ أثناء الاتصال بـ Gist API: {e}")
    exit(1)

session = create_session()

# 2. إنشاء مجموعة قنوات الـ LIVE الجديدة في بداية الملف
print("\n⚽ جاري تهيئة مجموعة قنوات LIVE المباشرة...")
live_separator = "# ==================== مجموعة قنوات LIVE ===================="
live_url = "https://majed-koora.live/stream.php?channel=majed20267&file=stream.m3u8"
live_content = (
    f'#EXTINF:-1 tvg-logo="" group-title="LIVE", LIVE FHD\n'
    f'{live_url}\n'
    f'#EXTINF:-1 tvg-logo="" group-title="LIVE", LIVE HD\n'
    f'{live_url}\n'
)

# 3. جلب وتصفية باقة قنوات الباشا تيفي (Al Basha TV) - العربية والفرنسية فقط
print("\n🚀 جاري جلب قنوات الباشا تيفي (Al Basha TV)...")
basha_separator = "# ==================== مجموعة قنوات AL BASHA TV ===================="
basha_api_url = "https://albashatv.site/api.php"
basha_headers = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Connection": "Keep-Alive",
    "User-Agent": "okhttp/3.9.1"
}

# جلب الباقات العادية وباقات الـ VIP
basha_payloads = ["method=o6&event=view", "method=o2&event=view"]

basha_content = ""
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
                
                # الفلترة الصارمة لجلب القنوات العربية والفرنسية فقط
                if is_arabic_or_french(channel_name):
                    # تطبيق البروكسي الخاص بالباشا تيفي حصراً للرابط بدون هيدرات إضافية
                    if not raw_url.startswith("http://live-albashatv.site//stream?url="):
                        final_basha_url = f"http://live-albashatv.site//stream?url={raw_url}"
                    else:
                        final_basha_url = raw_url
                    
                    basha_content += f'#EXTINF:-1 tvg-logo="" group-title="AL BASHA TV", {channel_name}\n'
                    basha_content += f'{final_basha_url}\n'
                    
                    seen_basha_urls.add(raw_url)
                    matched_count += 1
    except Exception as e:
        print(f"❌ خطأ أثناء جلب قنوات الباشا (Payload: {payload}): {e}")

print(f"🎯 تم استخراج وتصفية ({matched_count}) قناة عربية وفرنسية من الباشا تيفي بنجاح.")

# 4. جلب وتنسيق باقة قنوات ياسين تيفي (Yacine TV)
print("\n🚀 جاري جلب قنوات ياسين تيفي (Yacine TV)...")
yacine_separator = "# ==================== مجموعة قنوات BEIN MAX YACINE TV ===================="

# الإبقاء على جودة FHD فقط
targets = {
    "https://def.yacinelive.com/api/categories/90/channels": "FHD"
}
yacine_headers = {
    "Accept": "application/json",
    "Accept-Encoding": "gzip",
    "Connection": "Keep-Alive",
    "User-Agent": "okhttp/4.12.0"
}

ua_value = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
referer_value = "http://re.ycn-redirect.com/"

yacine_content = ""
for category_url, quality in targets.items():
    print(f"🔄 جاري سحب باقة ياسين بجودة {quality}...")
    channels_data = fetch_and_decrypt_yacine(session, category_url, yacine_headers)
    
    if channels_data and 'data' in channels_data:
        channels_list = channels_data['data']
        for index, channel in enumerate(channels_list):
            channel_name = channel.get('name')
            channel_id = channel.get('id')
            
            channel_name_lower = channel_name.lower()
            
            # التأكد من أن القناة هي إما MAX أو beIN Sport العادية
            if not ("max" in channel_name_lower or "bein sport" in channel_name_lower):
                continue
                
            print(f"   ⏳ [{index + 1}/{len(channels_list)}] جاري استخراج: {channel_name}...")
            channel_detail_url = f"https://def.yacinelive.com/api/channel/{channel_id}"
            detail_data = fetch_and_decrypt_yacine(session, channel_detail_url, yacine_headers)
            
            if detail_data and 'data' in detail_data:
                streams = detail_data['data']
                if streams:
                    stream = streams[0]
                    raw_url = stream.get('url')
                    final_url = get_final_url(raw_url)
                    
                    final_url_with_headers = f"{final_url}|User-Agent={ua_value}&Referer={referer_value}"
                    display_name = f"{channel_name} {quality}"
                    
                    yacine_content += f'#EXTINF:-1 tvg-logo="" group-title="BEIN MAX YACINE TV", {display_name}\n'
                    yacine_content += f'{final_url_with_headers}\n'
                    print(f"      ✔️ نجاح.")
            time.sleep(0.5)

# دمج المحتوى بالترتيب الجديد مع تصفية قنواتك اليدوية
final_m3u_content = f"#EXTM3U\n\n{live_separator}\n{live_content}\n\n{basha_separator}\n{basha_content}\n\n{yacine_separator}\n{yacine_content}\n\n# ==================== قنواتك اليدوية والثابتة ====================\n{static_clean}"

# 5. تحديث الـ Gist الخاص بك
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
    print("🎉 تم التحديث بنجاح تام! الروابط والقنوات المباشرة جاهزة ومطابقة للمواصفات المطلوبة.")
else:
    print(f"❌ فشل تحديث الـ Gist. كود الحالة: {update_response.status_code}")
