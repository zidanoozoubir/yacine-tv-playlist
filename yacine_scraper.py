import base64
import requests
import json

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
        print(f"Error decrypting: {e}")
        return None

# دالة مساعدة للاتصال بالخادم وفك التشفير تلقائياً
def fetch_and_decrypt(url, headers):
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            t_value = response.headers.get('T') or response.headers.get('t')
            if t_value:
                decrypted_json_str = decrypt_yacine(response.text, t_value)
                return json.loads(decrypted_json_str)
    except Exception as e:
        print(f"Error fetching {url}: {e}")
    return None

# دالة تتبع إعادة التوجيه (301 Redirect) للحصول على الرابط النهائي لـ VLC
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

# الترويسات الافتراضية للتطبيق لتجنب الحظر
app_headers = {
    "Accept": "application/json",
    "Accept-Encoding": "gzip",
    "Connection": "Keep-Alive",
    "User-Agent": "okhttp/4.12.0"
}

# 1. جلب قائمة القنوات كاملة للقسم 90 (قسم beIN Sports والرياضة)
category_url = "https://def.yacinelive.com/api/categories/90/channels"
print("🔄 جاري جلب قائمة القنوات من السيرفر...")
channels_data = fetch_and_decrypt(category_url, app_headers)

m3u_content = "#EXTM3U\n"

if channels_data and 'data' in channels_data:
    channels_list = channels_data['data']
    print(f"✅ تم جلب القائمة بنجاح! عثرنا على ({len(channels_list)}) قنوات.")
    
    # 2. المرور على كل قناة واستخراج الرابط المباشر لها
    for index, channel in enumerate(channels_list):
        channel_name = channel.get('name')
        channel_id = channel.get('id')
        
        print(f" [{index + 1}/{len(channels_list)}] جاري جلب رابط القناة: {channel_name}...")
        
        # طلب رابط البث للقناة الفردية
        channel_detail_url = f"https://def.yacinelive.com/api/channel/{channel_id}"
        detail_data = fetch_and_decrypt(channel_detail_url, app_headers)
        
        if detail_data and 'data' in detail_data:
            streams = detail_data['data']
            if streams:
                # نأخذ المصدر الأول المتوفر للقناة
                stream = streams[0]
                raw_url = stream.get('url')
                final_url = get_final_url(raw_url)
                
                # إضافة القناة بتنسيق m3u
                m3u_content += f'#EXTINF:-1 tvg-logo="" group-title="Yacine TV", {channel_name}\n'
                m3u_content += f'#EXTVLCOPT:http-referrer=http://re.ycn-redirect.com/\n'
                m3u_content += f'#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36\n'
                m3u_content += f'{final_url}\n'
                print(f"   ✔️ تم بنجاح.")
else:
    print("❌ فشل جلب قائمة القنوات من السيرفر.")

# 3. حفظ جميع القنوات المستخرجة في ملف M3U
with open("playlist.m3u", "w", encoding="utf-8") as f:
    f.write(m3u_content)

print("\n🎉 تم جلب وتحديث جميع القنوات بنجاح في ملف playlist.m3u!")
