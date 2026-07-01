import base64
import requests
import json
import time
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

# ==================== إعدادات التصفية المستهدفة ====================
# تم تحديد الأقسام الرياضية الأربعة المكتشفة لضمان جلب beIN و MAX بجودات FHD و HD
TARGET_CATEGORIES = [4, 5, 90, 91]
# ================================================================

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
    # المحاولة التلقائية عند حدوث ضغط على السيرفر
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
                print(f"⚠️ تحذير: لم يتم العثور على مفتاح T في الرد من {url}")
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

# ترويسات التطبيق الافتراضية
app_headers = {
    "Accept": "application/json",
    "Accept-Encoding": "gzip",
    "Connection": "Keep-Alive",
    "User-Agent": "okhttp/4.12.0"
}

session = create_session()

# جلب قائمة الأقسام الرئيسية لمعرفة الأسماء
categories_url = "https://def.yacinelive.com/api/categories"
print("🔄 جاري الاتصال بالسيرفر وجلب الأقسام المحددة...")
categories_data = fetch_and_decrypt(session, categories_url, app_headers)

m3u_content = "#EXTM3U\n"

if categories_data and 'data' in categories_data:
    categories_list = categories_data['data']
    
    # فلترة الأقسام بناءً على الأقسام الأربعة الرياضية المستهدفة فقط
    selected_categories = [c for c in categories_list if c.get('id') in TARGET_CATEGORIES]
    print(f"✅ تم العثور على الأقسام المطلوبة: {[c.get('name') for c in selected_categories]}")
    
    # 2. المرور على الأقسام الرياضية المستهدفة فقط
    for cat in selected_categories:
        cat_name = cat.get('name')
        cat_id = cat.get('id')
        
        print(f"\n📂 جاري سحب قنوات باقة: [{cat_name}]...")
        category_channels_url = f"https://def.yacinelive.com/api/categories/{cat_id}/channels"
        channels_data = fetch_and_decrypt(session, category_channels_url, app_headers)
        
        if channels_data and 'data' in channels_data:
            channels_list = channels_data['data']
            print(f"   📺 عثرنا على ({len(channels_list)}) قنوات في هذه الباقة.")
            
            # 3. جلب جميع جودات القنوات مباشرة
            for index, channel in enumerate(channels_list):
                channel_name = channel.get('name')
                channel_id = channel.get('id')
                
                print(f"   ⏳ [{index + 1}/{len(channels_list)}] جاري استخراج قنوات وجودات: {channel_name}...")
                
                channel_detail_url = f"https://def.yacinelive.com/api/channel/{channel_id}"
                detail_data = fetch_and_decrypt(session, channel_detail_url, app_headers)
                
                if detail_data and 'data' in detail_data:
                    streams = detail_data['data']
                    if streams:
                        # المرور على جميع جودات البث المتوفرة لهذه القناة وإضافتها بالكامل
                        for stream in streams:
                            stream_quality = stream.get('name', 'SD') # اسم الجودة (مثال: 1080p, 720p, 360p)
                            raw_url = stream.get('url')
                            final_url = get_final_url(raw_url)
                            
                            # دمج اسم القناة مع اسم الجودة لتبدو منسقة (مثل: beIN SPORTS 1 - 1080P)
                            display_name = f"{channel_name} - {stream_quality}"
                            
                            m3u_content += f'#EXTINF:-1 tvg-logo="" group-title="{cat_name}", {display_name}\n'
                            m3u_content += f'#EXTVLCOPT:http-referrer=http://re.ycn-redirect.com/\n'
                            m3u_content += f'#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36\n'
                            m3u_content += f'{final_url}\n'
                            print(f"      ✔️ جودة {stream_quality}: نجاح.")
                    else:
                        print(f"      ⚠️ لا توجد جودات بث متوفرة لهذه القناة.")
                
                # تأخير بسيط (0.5 ثانية) لمنع الحظر
                time.sleep(0.5)
        else:
            print(f"❌ فشل جلب قنوات الباقة: {cat_name}")
else:
    print("❌ فشل الاتصال بالسيرفر الرئيسي وجلب الأقسام.")

# حفظ ملف M3U المشترك
with open("playlist.m3u", "w", encoding="utf-8") as f:
    f.write(m3u_content)

print("\n🎉 مبروك! تم جلب الباقتين بجميع الجودات المتوفرة بنجاح وبسرعة فائقة في ملف واحد!")
