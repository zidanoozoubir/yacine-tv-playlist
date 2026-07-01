import base64
import requests
import json
import time
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

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
        print(f"❌ خطأ في فك التشفير: {e}")
        return None

# إعداد الجلسة مع الكوكيز والمحاولات التلقائية
def create_session():
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

# دالة الاتصال وجلب البيانات وفك تشفيرها مع طباعة التفاصيل عند الفشل
def fetch_and_decrypt(session, url, headers):
    try:
        response = session.get(url, headers=headers, timeout=15)
        print(f"📡 طلب: {url} -> حالة الرد: {response.status_code}")
        
        if response.status_code == 200:
            t_value = response.headers.get('T') or response.headers.get('t')
            if t_value:
                decrypted_str = decrypt_yacine(response.text, t_value)
                if decrypted_json_str := decrypted_json_str:
                    return json.loads(decrypted_json_str)
            else:
                print(f"⚠️ تحذير: لم يتم العثور على ترويسة T في الرد من {url}")
        else:
            print(f"❌ فشل الاتصال بالرابط {url}. محتوى الرد (أول 100 حرف): {response.text[:100]}")
    except Exception as e:
        print(f"❌ خطأ غير متوقع أثناء جلب {url}: {e}")
    return None

# تتبع الـ Redirect للحصول على البث النهائي
def get_final_url(raw_url):
    browser_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
    }
    try:
        r_redirect = requests.get(raw_url, headers=browser_headers, allow_redirects=False, timeout=10)
        if r_redirect.status_code in [301, 302]:
            return r_redirect.headers.get('Location')
    except Exception as e:
        print(f"⚠️ فشل تتبع التوجيه للرابط {raw_url}: {e}")
    return raw_url

# الترويسات الرسمية للتطبيق
app_headers = {
    "Accept": "application/json",
    "Accept-Encoding": "gzip",
    "Connection": "Keep-Alive",
    "User-Agent": "okhttp/4.12.0"
}

# تشغيل الجلسة
session = create_session()

# الأقسام الرياضية المستهدفة (90 لقنوات beIN و 89 لقنوات MAX)
TARGET_CATEGORIES = ["90", "89"]
FILTER_KEYWORDS = ["bein", "bien", "max"]

print("🚀 بدء تشغيل السكربت المطور...")
categories_url = "https://def.yacinelive.com/api/categories"
categories_data = fetch_and_decrypt(session, categories_url, app_headers)

m3u_content = "#EXTM3U\n"

if categories_data and 'data' in categories_data:
    categories_list = categories_data['data']
    selected_categories = [c for c in categories_list if str(c.get('id')) in TARGET_CATEGORIES]
    print(f"✅ تم العثور على {len(selected_categories)} أقسام رياضية مستهدفة.")
    
    for cat in selected_categories:
        cat_name = cat.get('name')
        cat_id = str(cat.get('id'))
        
        print(f"\n📂 فحص القسم: [{cat_name}] (ID: {cat_id})...")
        category_channels_url = f"https://def.yacinelive.com/api/categories/{cat_id}/channels"
        channels_data = fetch_and_decrypt(session, category_channels_url, app_headers)
        
        if channels_data and 'data' in channels_data:
            channels_list = channels_data['data']
            
            # تصفية القنوات
            filtered_channels = []
            for channel in channels_list:
                ch_name = channel.get('name', '')
                if any(keyword.lower() in ch_name.lower() for keyword in FILTER_KEYWORDS):
                    filtered_channels.append(channel)
            
            if filtered_channels:
                print(f"   📺 تم العثور على {len(filtered_channels)} قناة رياضية مطابقة للفلتر.")
                for index, channel in enumerate(filtered_channels):
                    channel_name = channel.get('name')
                    channel_id = channel.get('id')
                    
                    print(f"   ⏳ [{index + 1}/{len(filtered_channels)}] جاري استخراج: {channel_name}...")
                    channel_detail_url = f"https://def.yacinelive.com/api/channel/{channel_id}"
                    detail_data = fetch_and_decrypt(session, channel_detail_url, app_headers)
                    
                    if detail_data and 'data' in detail_data:
                        streams = detail_data['data']
                        if streams:
                            raw_url = streams[0].get('url')
                            final_url = get_final_url(raw_url)
                            
                            m3u_content += f'#EXTINF:-1 tvg-logo="" group-title="{cat_name}", {channel_name}\n'
                            m3u_content += f'#EXTVLCOPT:http-referrer=http://re.ycn-redirect.com/\n'
                            m3u_content += f'#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36\n'
                            m3u_content += f'{final_url}\n'
                            print(f"      ✔️ نجاح: تم جلب الرابط بنجاح.")
                    time.sleep(0.5)
            else:
                print(f"   ⚠️ تحذير: القسم {cat_name} لا يحتوي على قنوات مطابقة للفلاتر {FILTER_KEYWORDS}")
        else:
            print(f"   ❌ فشل فتح قنوات القسم: {cat_name}")
else:
    print("❌ خطأ فادح: فشل جلب الأقسام الرئيسية بالكامل من السيرفر الرئيسي.")

# كتابة ملف M3U
with open("playlist.m3u", "w", encoding="utf-8") as f:
    f.write(m3u_content)

print("\n🎉 انتهت العملية.")
