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

# دالة لتصفية واستخراج القنوات اليدوية والثابتة فقط بشكل آمن
def extract_static_channels(m3u_content):
    lines = m3u_content.splitlines()
    static_lines = []
    current_channel_block = []
    
    # تم استبعاد قنوات البث المباشر المحددة لمنع تكرارها في القسم الثابت
    exclude_keywords = [
        "def.yacinelive.com", "metava.online", "re.ycn-redirect.com", "BEIN MAX YACINE TV",
        "albashatv.site", "playcasta.online", "AL BASHA TV", "majed-koora.live", "na-drtv.org"
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

# دالة ذكية صارمة وفائقة الدقة لفحص حالة بروكسي الباشا وكشف صفحات التحدي والحظر
def check_basha_proxy_status(session):
    test_url = "http://live-albashatv.site/stream"
    try:
        # إرسال طلب فحص ديناميكي بمهلة تشغيل قصيرة
        response = session.get(test_url, timeout=3, allow_redirects=False)
        response_text_lower = response.text.lower()
        
        # كشف ما إذا كانت الاستجابة عبارة عن صفحة حظر أو صفحة تحدي/تحقق من Cloudflare
        is_cloudflare_challenge = (
            "cf-challenge" in response_text_lower or 
            "challenges.cloudflare.com" in response_text_lower or 
            "just a moment" in response_text_lower or
            "turnstile" in response_text_lower
        )
        
        # لكي نعتبر البروكسي يعمل، يجب أن يرجع كود حالة طبيعي (200 أو 400) وألا يكون صفحة تحدي أو حظر
        if response.status_code in [200, 400] and not is_cloudflare_challenge:
            print(f"⚡ تم فحص البروكسي: خادم البروكسي نشط ومتاح حالياً (كود: {response.status_code}). سيتم استخدام البروكسي.")
            return True
        else:
            print(f"⚠️ تم فحص البروكسي: غير متاح أو محجوب بحماية Cloudflare (كود: {response.status_code}). سيتم الانتقال للروابط المباشرة تلقائياً.")
            return False
    except Exception as e:
        print(f"⚠️ تم فحص البروكسي: فشل الاتصال المباشر بخادم البروكسي ({e}). سيتم الانتقال للروابط المباشرة تلقائياً.")
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
final_m3u_content = ""

# 2. تهيئة وتجهيز باقة قنوات LIVE المباشرة الجديدة بالترتيب الأول
print("\n⚽ جاري تهيئة مجموعة قنوات LIVE المباشرة...")
live_separator = "# ==================== مجموعة قنوات LIVE ===================="
live_url = "https://majed-koora.live/stream.php?channel=majed20267&file=stream.m3u8"
live_content = (
    f'#EXTINF:-1 tvg-logo="" group-title="LIVE", Match LIVE TV FHD\n'
    f'{live_url}\n'
    f'#EXTINF:-1 tvg-logo="" group-title="LIVE", Match LIVE TV HD\n'
    f'{live_url}\n'
)

# 3. جلب وتصفية باقة قنوات الباشا تيفي (Al Basha TV)
print("\n🚀 جاري جلب قنوات الباشا تيفي (Al Basha TV)...")
basha_separator = "# ==================== مجموعة قنوات AL BASHA TV ===================="
basha_api_url = "https://albashatv.site/api.php"
basha_headers = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Connection": "Keep-Alive",
    "User-Agent": "okhttp/3.9.1"
}

# تشغيل دالة الفحص الذكي الدقيقة للبروكسي قبل معالجة قنوات الباشا
use_basha_proxy = check_basha_proxy_status(session)

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
                    
                channel_name_lower = channel_name.lower()
                
                # تصفية صارمة جداً لحذف قنوات الـ VIP وقنوات الدول غير المرغوبة فوراً
                exclude_tags = [
                    "vip de", "vip uk", "vip ru", "vip bg", "vip pl", "vip es", "vip tr", "vip ph", "vip it", "vip br", "vip us", "vip dk", "vip hu", "vip ro",
                    "de:", "uk:", "ru:", "bg:", "pl:", "es:", "ca:", "tr:", "ph:", "au:", "cz:", "usa:", "it:", "br:", "hu:", "us:", "ro:", "dk:", "usa)", "hu", "ro", "dk", "usa"
                    " de ", " uk ", " ru ", " bg ", " pl ", " es ", " ca ", " tr ", " ph ", " au ", " cz ", " usa ", " it ", " br ", " hu ", " us ", " ro ", " dk ",
                    "[de]", "[uk]", "[ru]", "[bg]", "[pl]", "[es]", "[ca]", "[tr]", "[ph]", "[au]", "[cz]", "[usa]", "[it]", "[br]", "[hu]", "[us]", "[ro]", "[dk]",
                    "(de)", "(uk)", "(ru)", "(bg)", "(pl)", "(es)", "(ca)", "(tr)", "(ph)", "(au)", "(cz)", "(usa)", "(it)", "[br]", "[hu]", "[us]", "[ro]", "[dk]"
                ]
                
                if any(tag in channel_name_lower for tag in exclude_tags):
                    continue
                
                # أ - قنوات beIN Sports و beIN Max (العربية والفرنسية)
                is_bein = "bein" in channel_name_lower
                
                # ب - القنوات الترفيهية العربية المحددة (OSN, Netflix, HBO, Amazon, VIP, Shahid, MBC, الكأس، الفجر، الوان، ثمانية، STC)
                is_arabic_premium = False
                premium_keywords = [
                    "osn", "netflix", "hbo", "amazon", "vip", "shahid", 
                    "box office", "boxoffice", "box-office", "بوكس", 
                    "al fajer", "fajer", "الفجر",
                    "stc", "thamanya", "ثمانية",
                    "alkass", "الكأس", "الكاس",
                    "alwan", "ألوان", "الوان",
                    "mbc", "ام بي سي"
                ]
                if any(kw in channel_name_lower for kw in premium_keywords):
                    has_arabic_chars = any('\u0600' <= char <= '\u06FF' for char in channel_name)
                    has_foreign_tag = any(tag in channel_name_lower for tag in ["fr:", "fr ", "(fr)", "[fr]", " en ", " es ", " de "])
                    if has_arabic_chars or not has_foreign_tag:
                        is_arabic_premium = True
                
                # ج - القنوات الفرنسية المحددة (الوثائقية، الوطنية العامة، الأفلام، الرياضة، الأطفال)
                is_french_target = False
                french_tags = ["fr:", "fr ", "(fr)", "[fr]", "france"]
                if any(tag in channel_name_lower for tag in french_tags) or "canal+" in channel_name_lower:
                    french_keywords = [
                        "tf1", "m6", "canal", "rmc", "eurosport", "lequipe", "l'equipe", 
                        "ocs", "cine", "ciné", "gulli", "tiji", "cartoon", "disney", 
                        "nickelodeon", "nat geo", "national geo", "discovery", "ushuaia", 
                        "histoire", "science", "action", "w9", "tmc", "tfx"
                    ]
                    if any(kw in channel_name_lower for kw in french_keywords):
                        is_french_target = True
                
                # تمرير القناة فقط إذا طابقت أحد الشروط الثلاثة المحددة
                if is_bein or is_arabic_premium or is_french_target:
                    
                    # اختيار صيغة الرابط بناءً على نتيجة فحص خادم البروكسي
                    if use_basha_proxy:
                        # استخدام البروكسي مع تصحيح المسار (شرطة واحدة فقط)
                        final_basha_url = f"http://live-albashatv.site/stream?url={raw_url}"
                    else:
                        # تجاوز البروكسي كلياً واستخدام الروابط المباشرة لضمان التشغيل المستمر
                        final_basha_url = raw_url
                    
                    basha_content += f'#EXTINF:-1 tvg-logo="" group-title="AL BASHA TV", {channel_name}\n'
                    basha_content += f'{final_basha_url}\n'
                    
                    seen_basha_urls.add(raw_url)
                    matched_count += 1
    except Exception as e:
        print(f"❌ خطأ أثناء جلب قنوات الباشا (Payload: {payload}): {e}")

print(f"🎯 تم استخراج وتصفية ({matched_count}) قناة من الباشا بنجاح.")

# 4. جلب وتنسيق باقة قنوات ياسين تيفي (Yacine TV)
print("\n🚀 جاري جلب قنوات ياسين تيفي (Yacine TV)...")
yacine_separator = "# ==================== مجموعة قنوات BEIN MAX YACINE TV ===================="

# الإبقاء على جودة FHD فقط (الفئة 90)
targets = {
    "https://def.yacinelive.com/api/categories/90/channels": "FHD"
}
yacine_headers = {
    "Accept": "application/json",
    "Accept-Encoding": "gzip",
    "Connection": "Keep-Alive",
    "User-Agent": "okhttp/4.12.0"
}

ua_value = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/139.0.0.0 Safari/537.36"
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
            
            channel_name_lower = channel_name.lower() if channel_name else ""
            
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

# 5. جلب وتنسيق باقة قنوات ريان تيفي (Rayan TV) ديناميكياً
print("\n🚀 جاري جلب قنوات ريان تيفي (Rayan TV)...")
rayan_separator = "# ==================== مجموعة قنوات RAYAN TV ===================="
rayan_content = ""

try:
    rayan_api_url = "https://rayanamir.xyz/api/Getappuser.php"
    rayan_headers = {
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": "smart-tv"
    }
    # إرسال طلب الـ POST المشفر بترميز Base64 مع حرفي التشويش "mo"
    rayan_payload = {
        "data": "eyJhcHBfZGV2aWNlX2lkIjoiTldVd1ptWmhObVJrTWpRNFlUTmtZZz09IiwiYXBwX3R5cGUiOiJ0dmkiLCJ2ZXJzaW9uIjoiMS4wIiwiaXNfcGFpZCI6ZmFsc2V9mo"
    }
    
    rayan_response = session.post(rayan_api_url, headers=rayan_headers, json=rayan_payload, timeout=15)
    if rayan_response.status_code == 200:
        res_data = rayan_response.json()
        encrypted_b64 = res_data.get("data", "")
        
        if encrypted_b64:
            # إزالة حرفي التشويش "aa" من نهاية الـ Base64
            clean_b64 = encrypted_b64[:-2]
            
            # تصحيح الـ padding لضمان فك التشفير بشكل سليم
            missing_padding = len(clean_b64) % 4
            if missing_padding:
                clean_b64 += '=' * (4 - missing_padding)
                
            try:
                decrypted_json_str = base64.b64decode(clean_b64).decode('utf-8')
                config_data = json.loads(decrypted_json_str)
                urls_list = config_data.get("urls", [])
            except Exception as dec_err:
                print(f"   ❌ فشل فك ترميز Base64 لبيانات الإعدادات: {dec_err}")
                urls_list = []
                
            if urls_list:
                # جلب رابط الـ M3U المباشر من السيرفر الفعّال حالياً
                m3u_url = urls_list[0].get("url")
                print(f"   📥 تم استخراج رابط البث المباشر الفعال لريان تيفي.")
                
                # ترويسة مخصصة لتخطي حظر Cloudflare على السيرفر المستهدف
                m3u_headers = {
                    "User-Agent": "okhttp/5.0.0-alpha.2",
                    "Accept-Encoding": "gzip",
                    "Connection": "Keep-Alive"
                }
                
                m3u_response = session.get(m3u_url, headers=m3u_headers, timeout=25)
                print(f"   📡 كود حالة الاستجابة لسيرفر القنوات: {m3u_response.status_code}")
                
                if m3u_response.status_code == 200:
                    lines = m3u_response.text.splitlines()
                    print(f"   📊 حجم ملف القنوات المستلم: {len(m3u_response.text)} حرف.")
                    seen_urls = set()
                    current_inf = None
                    matched_rayan_count = 0
                    
                    # وسوم اللغات الأجنبية المستبعدة فوراً لقنوات beIN لضمان العربية والفرنسية فقط
                    foreign_tags = [
                        "en:", "es:", "tr:", "us:", "uk:", "de:", "it:", "pl:", "ru:", "gr:", "ro:", "dk:", "hu:", "ph:", "bg:",
                        "[en]", "[es]", "[tr]", "[us]", "[uk]", "[de]", "[it]", "[pl]", "[ru]", "[gr]", "[ro]", "[dk]", "[hu]",
                        "(en)", "(es)", "(tr)", "(us)", "(uk)", "(de)", "(it)", "(pl)", "(ru)", "(gr)", "(ro)", "(dk)", "(hu)",
                        " en ", " es ", " tr ", " us ", " uk ", " de ", " it ", " pl ", " ru ", " gr ", " ro ", " dk "
                    ]
                    
                    for line in lines:
                        line_stripped = line.strip()
                        if not line_stripped:
                            continue
                        if line_stripped.startswith("#EXTM3U"):
                            continue
                        if line_stripped.startswith("#EXTINF"):
                            current_inf = line_stripped
                        elif line_stripped.startswith("http") or line_stripped.startswith("rtmp"):
                            if current_inf and line_stripped not in seen_urls:
                                # استخراج اسم القناة من سطر الـ INF
                                name_parts = current_inf.rsplit(",", 1)
                                channel_name = name_parts[-1].strip() if len(name_parts) > 1 else "Rayan Channel"
                                channel_name_lower = channel_name.lower()
                                
                                # 1. التحقق من قنوات beIN Sports و beIN Max (العربية والفرنسية فقط واستبعاد بقية اللغات فوراً)
                                is_target_bein = False
                                if "bein" in channel_name_lower:
                                    if not any(tag in channel_name_lower for tag in foreign_tags):
                                        is_target_bein = True
                                
                                # 2. التحقق من قنوات الفجر
                                is_fajer = "fajer" in channel_name_lower or "الفجر" in channel_name_lower
                                
                                # 3. التحقق من قنوات ألوان / ألوان سبورت
                                is_alwan = "alwan" in channel_name_lower or "الوان" in channel_name_lower
                                
                                # تصفية دقيقة لتجاوز وحذف أي قناة أخرى فوراً
                                if is_target_bein or is_fajer or is_alwan:
                                    rayan_content += f'#EXTINF:-1 tvg-logo="" group-title="RAYAN TV", {channel_name}\n'
                                    rayan_content += f'{line_stripped}\n'
                                    seen_urls.add(line_stripped)
                                    matched_rayan_count += 1
                                current_inf = None
                    print(f"   🎯 تم تصفية واستخراج ({matched_rayan_count}) قناة فقط (بيين عربي/فرنسي، الفجر، ألوان سبورت) من ريان تيفي بنجاح.")
except Exception as e:
    print(f"❌ خطأ أثناء معالجة باقة ريان تيفي ديناميكياً: {e}")

# دمج المحتوى بالترتيب مع الحفاظ الكامل على قنواتك اليدوية
final_m3u_content = f"#EXTM3U\n\n{live_separator}\n{live_content}\n\n{basha_separator}\n{basha_content}\n\n{yacine_separator}\n{yacine_content}\n\n{rayan_separator}\n{rayan_content}\n\n# ==================== قنواتك اليدوية والثابتة ====================\n{static_clean}"

# 6. تحديث الـ Gist الخاص بك
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
