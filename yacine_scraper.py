import base64
import requests
import json
import time
import os
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

# دالة ذكية لتنظيف وتقشير روابط الباشا لتصبح متوافقة مع أجهزة الاستقبال
def clean_and_extract_url(raw_url):
    if not raw_url:
        return raw_url
        
    # 1. إذا كان الرابط يمر عبر وسيط الباشا تيفي نقوم باستخراج الرابط الداخلي
    if "?url=" in raw_url:
        parsed_url = urllib.parse.urlparse(raw_url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        if 'url' in query_params:
            raw_url = query_params['url'][0]
            
    # 2. تنظيف وتصحيح الشرطات المائلة المتكررة (مثل /// أو //)
    if "://" in raw_url:
        scheme, rest = raw_url.split("://", 1)
        parts = [p for p in rest.split("/") if p]
        normalized_rest = "/".join(parts)
        return f"{scheme}://{normalized_rest}"
        
    return raw_url

# دالة لتصفية واستخراج القنوات اليدوية والثابتة فقط بشكل آمن
def extract_static_channels(m3u_content):
    lines = m3u_content.splitlines()
    static_lines = []
    current_channel_block = []
    
    # تم إدراج كلمات الاستبعاد الخاصة بماجد سبورت لحماية القنوات اليدوية من التداخل والمسح
    exclude_keywords = [
        "def.yacinelive.com", "metava.online", "re.ycn-redirect.com", "BEIN MAX YACINE TV",
        "albashatv.site", "playcasta.online", "AL BASHA TV", "majed-koora.live", 'group-title="live"'
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
final_m3u_content = ""

# 2. جلب وتصفية باقة قنوات الباشا تيفي (Al Basha TV) المحددة وتنظيف روابطها للريسيفر
print("\n🚀 جاري جلب قنوات الباشا تيفي (Al Basha TV)...")
basha_separator = "# ==================== مجموعة قنوات AL BASHA TV ===================="
basha_api_url = "https://albashatv.site/api.php"
basha_headers = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Connection": "Keep-Alive",
    "User-Agent": "okhttp/3.9.1"
}
basha_payload = "method=o6&event=view"

# إضافة "vip" للبحث عن قنوات الأفلام والمسلسلات داخل تطبيق الباشا
basha_targets = ["bein max", "bein sport", "osn", "netflix", "bein media", "hbo", "amazon prime", "amazon", "vip"]

basha_content = ""
try:
    basha_response = session.post(basha_api_url, headers=basha_headers, data=basha_payload, timeout=15)
    if basha_response.status_code == 200:
        basha_channels = basha_response.json()
        print(f"✅ تم الاتصال بسيرفر الباشا بنجاح. إجمالي القنوات: ({len(basha_channels)}) قناة.")
        
        matched_count = 0
        for channel in basha_channels:
            channel_name = channel.get('name', '')
            raw_url = channel.get('url', '')
            
            channel_name_lower = channel_name.lower()
            if any(target in channel_name_lower for target in basha_targets):
                # استخراج الرابط المباشر وتنظيفه للجهاز
                cleaned_url = clean_and_extract_url(raw_url)
                
                # ربط هيدر التطبيق لتشغيل قنوات الباشا خارج التطبيق بشكل صحيح
                cleaned_url_with_headers = f"{cleaned_url}|User-Agent=okhttp/3.9.1"
                
                basha_content += f'#EXTINF:-1 tvg-logo="" group-title="AL BASHA TV", {channel_name}\n'
                basha_content += f'{cleaned_url_with_headers}\n'
                matched_count += 1
                
        print(f"🎯 تم استخراج وتصحيح ({matched_count}) قناة لتصبح متوافقة مع الريسيفر.")
    else:
        print(f"❌ فشل جلب قنوات الباقة: AL BASHA TV")
except Exception as e:
    print(f"❌ خطأ أثناء جلب قنوات الباشا: {e}")


# 3. جلب وتنسيق باقة قنوات ياسين تيفي (Yacine TV) بجميع جوداتها المتاحة
print("\n🚀 جاري جلب قنوات ياسين تيفي (Yacine TV)...")
yacine_separator = "# ==================== مجموعة قنوات BEIN MAX YACINE TV ===================="
targets = {
    "https://def.yacinelive.com/api/categories/90/channels": "FHD",
    "https://def.yacinelive.com/api/categories/89/channels": "HD"
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
            
            print(f"   ⏳ [{index + 1}/{len(channels_list)}] جاري استخراج: {channel_name}...")
            channel_detail_url = f"https://def.yacinelive.com/api/channel/{channel_id}"
            detail_data = fetch_and_decrypt_yacine(session, channel_detail_url, yacine_headers)
            
            if detail_data and 'data' in detail_data:
                streams = detail_data['data']
                if streams:
                    # تكرار جلب كل الجودات المتاحة للقناة لعدم خسارة الجودات المرتفعة
                    for stream in streams:
                        raw_url = stream.get('url')
                        stream_quality = stream.get('name', quality)
                        final_url = get_final_url(raw_url)
                        
                        final_url_with_headers = f"{final_url}|User-Agent={ua_value}&Referer={referer_value}"
                        display_name = f"{channel_name} {stream_quality}"
                        
                        yacine_content += f'#EXTINF:-1 tvg-logo="" group-title="BEIN MAX YACINE TV", {display_name}\n'
                        yacine_content += f'{final_url_with_headers}\n'
                    print(f"      ✔️ نجاح استخراج الجودات.")
            time.sleep(0.5)


# 4. جلب وتنسيق باقة قنوات ماجد سبورت (Majed Sport) وإضافتها كمجموعة live
print("\n🚀 جاري جلب قنوات ماجد سبورت (Majed Sport)...")
majed_separator = "# ==================== مجموعة قنوات live ===================="
majed_config_url = f"https://www.majed-koora.live/config.json?v={int(time.time())}"
majed_headers = {
    "User-Agent": "VLC/3.0.16 LibVLC/3.0.16",
    "Referer": "https://www.majed-koora.live/"
}
majed_content = ""
try:
    majed_response = session.get(majed_config_url, headers=majed_headers, timeout=15)
    if majed_response.status_code == 200:
        config_data = majed_response.json()
        channels_found = []
        
        # استخراج المعرفات من config.json بشكل مرن وحركي
        if isinstance(config_data, list):
            for item in config_data:
                if isinstance(item, dict):
                    ch_id = item.get('channel') or item.get('id') or item.get('code')
                    if ch_id:
                        channels_found.append(ch_id)
        elif isinstance(config_data, dict):
            for key in ['channels', 'streams', 'data', 'list']:
                if key in config_data and isinstance(config_data[key], list):
                    for item in config_data[key]:
                        if isinstance(item, dict):
                            ch_id = item.get('channel') or item.get('id') or item.get('code')
                            if ch_id:
                                channels_found.append(ch_id)
            if not channels_found:
                for k, v in config_data.items():
                    if isinstance(v, str) and ('stream' in v or 'm3u8' in v or len(v) < 30):
                        channels_found.append(v)
                        
        if not channels_found:
            channels_found = ["mamam991"]
            
        channels_found = list(dict.fromkeys(channels_found)) # إزالة التكرارات
        
        for idx, ch_id in enumerate(channels_found, 1):
            if "channel=" in ch_id:
                parsed_ch = urllib.parse.urlparse(ch_id)
                queries = urllib.parse.parse_qs(parsed_ch.query)
                if 'channel' in queries:
                    ch_id = queries['channel'][0]
                    
            timestamp = int(time.time() * 1000)
            stream_url = f"https://majed-koora.live/stream.php?channel={ch_id}&file=stream.m3u8&v={timestamp}"
            stream_url_with_headers = f"{stream_url}|User-Agent=VLC/3.0.16 LibVLC/3.0.16"
            
            display_name = f"live {idx:02d}"
            majed_content += f'#EXTINF:-1 tvg-logo="" group-title="live", {display_name}\n'
            majed_content += f'{stream_url_with_headers}\n'
        print(f"✅ تم سحب ({len(channels_found)}) قناة وتسميتها بالتسلسل.")
    else:
        print(f"❌ فشل جلب قنوات ماجد سبورت. كود الحالة: {majed_response.status_code}")
except Exception as e:
    print(f"❌ خطأ أثناء جلب قنوات ماجد سبورت: {e}")


# دمج المحتوى بالترتيب مع الحفاظ الكامل على قنواتك اليدوية والثابتة
final_m3u_content = f"#EXTM3U\n\n{majed_separator}\n{majed_content}\n\n{basha_separator}\n{basha_content}\n\n{yacine_separator}\n{yacine_content}\n\n# ==================== قنواتك اليدوية والثابتة ====================\n{static_clean}"

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
    print("🎉 تم التحديث بنجاح! الروابط أصبحت الآن مباشرة ونظيفة وجاهزة للعمل على الريسيفر.")
else:
    print(f"❌ فشل تحديث الـ Gist. كود الحالة: {update_response.status_code}")
