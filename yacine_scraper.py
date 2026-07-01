import base64
import requests
import json
import time
import os
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
        print(f"خطأ في فك التشفير: {e}")
        return None

# إنشاء جلسة عمل مشتركة (Session) للحفاظ على الكوكيز وتفادي الحظر
def create_session():
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

# دالة للاتصال بالسيرفر وفك تشفير البيانات تلقائياً
def fetch_and_decrypt(session, url, headers):
    try:
        response = session.get(url, headers=headers, timeout=15)
        print(f"📡 طلب: {url} -> حالة الرد: {response.status_code}")
        if response.status_code == 200:
            t_value = response.headers.get('T') or response.headers.get('t')
            if t_value:
                decrypted_json_str = decrypt_yacine(response.text, t_value)
                if decrypted_json_str:
                    return json.loads(decrypted_json_str)
        else:
            print(f"❌ فشل الاتصال بالرابط: {url} - كود الحالة: {response.status_code}")
    except Exception as e:
        print(f"❌ خطأ أثناء جلب الرابط {url}: {e}")
    return None

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

# 1. جلب المحتوى الحالي من الـ Gist السري الخاص بك لتنظيفه والحفاظ على قنواتك الثابتة
print("📂 جاري جلب محتوى الـ Gist الحالي...")
gist_api_url = f"https://api.github.com/gists/{GIST_ID}"
gist_headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

try:
    gist_response = requests.get(gist_api_url, headers=gist_headers, timeout=15)
    if gist_response.status_code == 200:
        gist_data = gist_response.json()
        # جلب اسم الملف الأول داخل الـ Gist ومحتواه
        filename = list(gist_data['files'].keys())[0]
        current_content = gist_data['files'][filename]['content']
        
        # قص القنوات القديمة المضافة سابقاً للحفاظ على قنواتك الثابتة فقط ومنع التكرار اللانهائي
        separator = "# ==================== مجموعة قنوات BEIN MAX YACINE TV ===================="
        if separator in current_content:
            m3u_content = current_content.split(separator)[0].strip() + "\n"
        else:
            m3u_content = current_content.strip() + "\n"
    else:
        print(f"❌ فشل جلب الـ Gist الحالي. كود الحالة: {gist_response.status_code}")
        exit(1)
except Exception as e:
    print(f"❌ خطأ أثناء الاتصال بـ Gist API: {e}")
    exit(1)

m3u_content += f"\n{separator}\n"

# 2. بدء تشغيل جلسة سحب قنوات ياسين تيفي
session = create_session()
targets = {
    "https://def.yacinelive.com/api/categories/90/channels": "FHD",
    "https://def.yacinelive.com/api/categories/89/channels": "HD"
}
app_headers = {
    "Accept": "application/json",
    "Accept-Encoding": "gzip",
    "Connection": "Keep-Alive",
    "User-Agent": "okhttp/4.12.0"
}

for category_url, quality in targets.items():
    print(f"🔄 جاري سحب قنوات ياسين بجودة {quality}...")
    channels_data = fetch_and_decrypt(session, category_url, app_headers)
    
    if channels_data and 'data' in channels_data:
        channels_list = channels_data['data']
        for index, channel in enumerate(channels_list):
            channel_name = channel.get('name')
            channel_id = channel.get('id')
            
            print(f"   ⏳ [{index + 1}/{len(channels_list)}] جاري استخراج: {channel_name}...")
            channel_detail_url = f"https://def.yacinelive.com/api/channel/{channel_id}"
            detail_data = fetch_and_decrypt(session, channel_detail_url, app_headers)
            
            if detail_data and 'data' in detail_data:
                streams = detail_data['data']
                if streams:
                    stream = streams[0]
                    raw_url = stream.get('url')
                    final_url = get_final_url(raw_url)
                    
                    # تسمية القنوات وتجميعها تحت المسمى الجديد المطلوب
                    display_name = f"{channel_name} {quality}"
                    m3u_content += f'#EXTINF:-1 tvg-logo="" group-title="BEIN MAX YACINE TV", {display_name}\n'
                    m3u_content += f'#EXTVLCOPT:http-referrer=http://re.ycn-redirect.com/\n'
                    m3u_content += f'#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36\n'
                    m3u_content += f'{final_url}\n'
                    print(f"      ✔️ نجاح.")
            time.sleep(0.5)

# 3. تحديث الـ Gist السري الخاص بك مباشرة بالملف الجديد المدمج
print("\n🔐 جاري تحديث الـ Gist السري الخاص بك برابط البث الجديد...")
update_data = {
    "files": {
        filename: {
            "content": m3u_content
        }
    }
}

update_response = requests.patch(gist_api_url, headers=gist_headers, json=update_data)

if update_response.status_code == 200:
    print("🎉 تم تحديث الـ Gist السري الخاص بك بنجاح تام! القنوات تعمل الآن على الريسيفر.")
else:
    print(f"❌ فشل تحديث الـ Gist. كود الحالة: {update_response.status_code}")
