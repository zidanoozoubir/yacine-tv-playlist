import base64
import requests
import json

# دالة فك التشفير الخاصة بتطبيق ياسين تيفي (XOR Decryption)
def decrypt_yacine(encrypted_data, header_t):
    # المفتاح السري الثابت المكتشف داخل كود التطبيق
    base_key = "c!xZj+N9&G@Ev@vw"
    
    # دمج المفتاح الثابت مع القيمة الديناميكية T القادمة في ترويسة الرد
    full_key = (base_key + header_t).encode('utf-8')
    
    # فك ترميز Base64 إلى بايتات (Bytes)
    try:
        encrypted_bytes = base64.b64decode(encrypted_data)
    except Exception as e:
        print(f"Error decoding Base64: {e}")
        return None
    
    # تطبيق عملية XOR لفك التشفير
    decrypted_bytes = bytearray()
    for i in range(len(encrypted_bytes)):
        decrypted_bytes.append(encrypted_bytes[i] ^ full_key[i % len(full_key)])
        
    return decrypted_bytes.decode('utf-8')

# دالة لتتبع رابط التوجيه (Redirect) وجلب الرابط المباشر لـ VLC
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

# قائمة القنوات التي نريد سحبها (اسم القناة ومعرفها)
# يمكنك إضافة قنوات أخرى هنا مستقبلاً باتباع نفس التنسيق
channels_to_scrape = {
    "beIN Sports 1": "1471",
}

m3u_content = "#EXTM3U\n"

for channel_name, channel_id in channels_to_scrape.items():
    channel_url = f"https://def.yacinelive.com/api/channel/{channel_id}"
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "Connection": "Keep-Alive",
        "User-Agent": "okhttp/4.12.0"
    }
    
    try:
        response = requests.get(channel_url, headers=headers, timeout=10)
        if response.status_code == 200:
            t_value = response.headers.get('T') or response.headers.get('t')
            if t_value:
                decrypted_json_str = decrypt_yacine(response.text, t_value)
                data = json.loads(decrypted_json_str)
                streams = data.get('data', [])
                
                # جلب المصدر الأول (غالباً الأعلى جودة)
                if streams:
                    stream = streams[0]
                    raw_url = stream.get('url')
                    final_url = get_final_url(raw_url)
                    
                    # تنسيق ملف M3U مع إرسال الترويسات المطلوبة للسيرفر عند تشغيل الملف
                    m3u_content += f'#EXTINF:-1 tvg-logo="" group-title="Yacine TV", {channel_name}\n'
                    m3u_content += f'#EXTVLCOPT:http-referrer=http://re.ycn-redirect.com/\n'
                    m3u_content += f'#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36\n'
                    m3u_content += f'{final_url}\n'
                    print(f"Successfully scraped {channel_name}")
    except Exception as e:
        print(f"Error scraping {channel_name}: {e}")

# حفظ الروابط المستخرجة في ملف M3U
with open("playlist.m3u", "w", encoding="utf-8") as f:
    f.write(m3u_content)
