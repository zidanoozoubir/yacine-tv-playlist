import base64
import requests
import json
import time
import os
import re
import hashlib
import hmac
import urllib.parse
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

# جلب معلومات الـ Gist من متغيرات البيئة الآمنة (GitHub Secrets)
GIST_ID = os.environ.get("GIST_ID")
GITHUB_TOKEN = os.environ.get("GIST_TOKEN")

# --- إعدادات التمرير اليدوي المؤقت لقنوات Reezn TV (عند الحاجة) ---
# إذا انتهت صلاحية التواقيع الافتراضية، يمكنك وضع القيم الطازجة الملتقطة من HTTP Toolkit هنا لتشغيل السكربت فوراً
MANUAL_REEZN_SIG = "ba571e3a4bea773a696897cdd96a26d123e4ada84ed18a4220ac603394838e1f"  # ضع توقيع الرياضة الطازج هنا
MANUAL_REEZN_TIME = "1783256939"  # ضع الرمز الزمني المقابل له هنا

MANUAL_REEZN_SIG_CHANNELS = ""  # توقيع باقة القنوات العامة الطازج (اختياري)
MANUAL_REEZN_TIME_CHANNELS = ""  # الرمز الزمني المقابل له (اختياري)

# قائمة النطاقات المستقرة والفعالة لتطبيق ياسين تيفي
YACINE_DOMAINS = [
    "https://def.yacinelive.com",
    "https://ver3.yacinelive.com",
    "https://v31.yacinelive.com"
]

# متغير عالمي لحفظ صيغة التوقيع المكتشفة ديناميكياً
FOUND_FORMULA = None

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

# دالة للاتصال بسيرفر ياسين وتجربة النطاقات المستقرة وفك التشفير تلقائياً
def fetch_and_decrypt_yacine_dynamic(session, endpoint_path, headers):
    for domain in YACINE_DOMAINS:
        url = f"{domain}{endpoint_path}"
        try:
            response = session.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                t_value = response.headers.get('T') or response.headers.get('t')
                if t_value:
                    decrypted_json_str = decrypt_yacine(response.text, t_value)
                    if decrypted_json_str:
                        return json.loads(decrypted_json_str)
        except Exception:
            continue
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

# دالة لكشف واستخراج قنوات ماجد سبورت النشطة تلقائياً من ملف الإعدادات
def get_majed_dynamic_channels(session):
    timestamp = int(time.time() * 1000)
    config_url = f"http://majed-koora.live/config.json?v={timestamp}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
        "Referer": "http://majed-koora.live/"
    }
    try:
        response = session.get(config_url, headers=headers, timeout=10)
        if response.status_code == 200:
            found = re.findall(r'majed[a-zA-Z0-9_-]+', response.text)
            channels = [c for c in found if "koora" not in c.lower() and "live" not in c.lower()]
            if channels:
                unique_channels = list(dict.fromkeys(channels))
                print(f"🔍 تم اكتشاف القنوات النشطة من ملف الإعدادات: {unique_channels}")
                return unique_channels
    except Exception as e:
        print(f"⚠️ فشل جلب ملف الإعدادات config.json من ماجد سبورت: {e}")
    
    return ["majedsports1"]

# دالة لتصفية واستخراج القنوات اليدوية والثابتة فقط بشكل آمن
def extract_static_channels(m3u_content):
    lines = m3u_content.splitlines()
    static_lines = []
    current_channel_block = []
    
    exclude_keywords = [
        "def.yacinelive.com", "metava.online", "re.ycn-redirect.com", "BEIN MAX YACINE TV",
        "albashatv.site", "playcasta.online", "AL BASHA TV", "majed-koora.live",
        "server.reezntv.com", "reezntv", "staticdev9.workers.dev", "REEZN TV"
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

# دالة لفحص حالة بروكسي الباشا وكشف صفحات التحدي والحظر
def check_basha_proxy_status(session):
    test_url = "http://live-albashatv.site/stream"
    try:
        response = session.get(test_url, timeout=3, allow_redirects=False)
        response_text_lower = response.text.lower()
        
        is_cloudflare_challenge = (
            "cf-challenge" in response_text_lower or 
            "challenges.cloudflare.com" in response_text_lower or 
            "just a moment" in response_text_lower or
            "turnstile" in response_text_lower
        )
        
        if response.status_code in [200, 400] and not is_cloudflare_challenge:
            print(f"⚡ تم فحص البروكسي: نشط ومتاح.")
            return True
        else:
            print(f"⚠️ تم فحص البروكسي: غير متاح أو محجوب بـ Cloudflare.")
            return False
    except Exception as e:
        print(f"⚠️ تم فحص البروكسي: فشل الاتصال ({e}).")
        return False

# دالة ذكية للبحث عن مصفوفة القنوات داخل استجابة الـ JSON مهما كانت متداخلة
def find_list_in_json(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ["data", "channels", "sports", "categories", "streams", "list"]:
            if key in data:
                val = data[key]
                if isinstance(val, list):
                    return val
                elif isinstance(val, dict):
                    sub_list = find_list_in_json(val)
                    if sub_list:
                        return sub_list
        for val in data.values():
            if isinstance(val, list):
                return val
            elif isinstance(val, dict):
                sub_list = find_list_in_json(val)
                if sub_list:
                    return sub_list
    return []

# تحليل واستنتاج معادلة التوقيع الرقمي تلقائياً عند التشغيل (Self-Healing Signature Engine)
def find_hashing_formula():
    global FOUND_FORMULA
    
    # عينة باقة الرياضة (Sports)
    time_1 = "1783256939"
    body_1_raw = '{"secret":"blaidyalah","date":"05_07_2026"}'
    body_1_nl = '{"secret":"blaidyalah","date":"05_07_2026"}\n'
    sig_1 = "ba571e3a4bea773a696897cdd96a26d123e4ada84ed18a4220ac603394838e1f"
    
    # عينة باقة القنوات العامة (Channels)
    time_2 = "1783251653"
    body_2_raw = '{"secret":"blaidyalah"}'
    body_2_nl = '{"secret":"blaidyalah"}\n'
    sig_2 = "dc2b63ba68b26969446821486d5cea4d18927fbb390d3f173863aaa999daebd2"
    
    test_secret = "blaidyalah"
    test_client = "SecureNativeV2"
    test_package = "com.bedevlab.reezn"
    test_debug = "1"
    
    placeholders = ["{TIME}", "{BODY}", "{SECRET}", "{CLIENT}", "{PACKAGE}", "{DEBUG}"]
    import itertools
    
    print("🔬 جاري فحص وتحليل خوارزمية تشفير السيرفر ذاتياً...")
    
    for r in range(1, len(placeholders) + 1):
        for perm in itertools.permutations(placeholders, r):
            for sep in ["", " ", "_", "-", ":", "/", "+"]:
                for is_nl in [False, True]:
                    b1 = body_1_nl if is_nl else body_1_raw
                    b2 = body_2_nl if is_nl else body_2_raw
                    
                    # فحص التنسيقات المختلفة للـ JSON لتغطية المسافات المحتملة
                    for b1_variant, b2_variant in [
                        (b1, b2), 
                        (b1.strip(), b2.strip()), 
                        (b1.replace(" ", ""), b2.replace(" ", ""))
                    ]:
                        s1 = sep.join([p.replace("{TIME}", time_1).replace("{BODY}", b1_variant).replace("{SECRET}", test_secret).replace("{CLIENT}", test_client).replace("{PACKAGE}", test_package).replace("{DEBUG}", test_debug) for p in perm])
                        s2 = sep.join([p.replace("{TIME}", time_2).replace("{BODY}", b2_variant).replace("{SECRET}", test_secret).replace("{CLIENT}", test_client).replace("{PACKAGE}", test_package).replace("{DEBUG}", test_debug) for p in perm])
                        
                        h1 = hashlib.sha256(s1.encode('utf-8')).hexdigest()
                        h2 = hashlib.sha256(s2.encode('utf-8')).hexdigest()
                        
                        if h1 == sig_1 and h2 == sig_2:
                            FOUND_FORMULA = {"type": "sha256", "sep": sep, "order": perm, "newline": is_nl}
                            print(f"🎉 تم كشف الخوارزمية بنجاح! نوع: SHA256، الترتيب: {perm}، الفاصل: '{sep}'")
                            return
                            
                        m1 = hashlib.md5(s1.encode('utf-8')).hexdigest()
                        m2 = hashlib.md5(s2.encode('utf-8')).hexdigest()
                        if m1 == sig_1 and m2 == sig_2:
                            FOUND_FORMULA = {"type": "md5", "sep": sep, "order": perm, "newline": is_nl}
                            print(f"🎉 تم كشف الخوارزمية بنجاح! نوع: MD5، الترتيب: {perm}، الفاصل: '{sep}'")
                            return

    # تجربة خوارزمية HMAC-SHA256
    for salt_key in [test_secret, test_client, test_package]:
        for msg_template in ["{TIME}", "{BODY_RAW}", "{BODY_NL}", "{TIME}{BODY_RAW}", "{TIME}{BODY_NL}"]:
            msg_1 = msg_template.replace("{TIME}", time_1).replace("{BODY_RAW}", body_1_raw).replace("{BODY_NL}", body_1_nl)
            msg_2 = msg_template.replace("{TIME}", time_2).replace("{BODY_RAW}", body_2_raw).replace("{BODY_NL}", body_2_nl)
            
            h1 = hmac.new(salt_key.encode('utf-8'), msg_1.encode('utf-8'), hashlib.sha256).hexdigest()
            h2 = hmac.new(salt_key.encode('utf-8'), msg_2.encode('utf-8'), hashlib.sha256).hexdigest()
            if h1 == sig_1 and h2 == sig_2:
                FOUND_FORMULA = {"type": "hmac_sha256", "salt_key": salt_key, "msg_template": msg_template}
                print(f"🎉 تم كشف الخوارزمية بنجاح! نوع: HMAC-SHA256، المفتاح: {salt_key}")
                return
                
    print("⚠️ لم يتم الوصول لصيغة الهاش ديناميكياً، سيتم استخدام التواقيع البديلة (التمرير اليدوي أو الثابت).")

# دالة لتوليد التوقيع الرقمي ديناميكياً بناءً على نتيجة الفحص الذاتي أو الارتداد للتمرير اليدوي
def get_signature_for_request(timestamp_str, body_str):
    global FOUND_FORMULA
    
    # التحقق أولاً مما إذا كان المستخدم قد مرر قيماً يدوية طازجة من HTTP Toolkit
    if MANUAL_REEZN_SIG and MANUAL_REEZN_TIME:
        if "date" in body_str:
            return MANUAL_REEZN_SIG, MANUAL_REEZN_TIME
        else:
            return MANUAL_REEZN_SIG_CHANNELS or MANUAL_REEZN_SIG, MANUAL_REEZN_TIME_CHANNELS or MANUAL_REEZN_TIME

    if not FOUND_FORMULA:
        # نظام الارتداد الآمن للتواقيع الثابتة المسجلة
        if "date" in body_str:
            return "ba571e3a4bea773a696897cdd96a26d123e4ada84ed18a4220ac603394838e1f", "1783256939"
        else:
            return "dc2b63ba68b26969446821486d5cea4d18927fbb390d3f173863aaa999daebd2", "1783251653"
            
    test_secret = "blaidyalah"
    test_client = "SecureNativeV2"
    test_package = "com.bedevlab.reezn"
    test_debug = "1"
    
    if FOUND_FORMULA["type"] in ["sha256", "md5"]:
        sep = FOUND_FORMULA["sep"]
        order = FOUND_FORMULA["order"]
        parts = []
        for p in order:
            val = p.replace("{TIME}", timestamp_str).replace("{secret}", test_secret).replace("{date}", time.strftime("%d_%m_%Y")).replace("{client}", test_client).replace("{package}", test_package).replace("{debug}", test_debug).replace("{BODY}", body_str)
            parts.append(val)
        joined = sep.join(parts)
        if FOUND_FORMULA["type"] == "sha256":
            return hashlib.sha256(joined.encode('utf-8')).hexdigest(), timestamp_str
        else:
            return hashlib.md5(joined.encode('utf-8')).hexdigest(), timestamp_str
            
    elif FOUND_FORMULA["type"] == "hmac_sha256":
        salt_key = FOUND_FORMULA["salt_key"]
        msg_template = FOUND_FORMULA["msg_template"]
        msg = msg_template.replace("{TIME}", timestamp_str).replace("{BODY_RAW}", body_str.strip()).replace("{BODY_NL}", body_str)
        sig = hmac.new(salt_key.encode('utf-8'), msg.encode('utf-8'), hashlib.sha256).hexdigest()
        return sig, timestamp_str
        
    return None, timestamp_str

# دالة لجلب القنوات من سيرفر Reezn TV ديناميكياً بكلمة السر وترويسات التوقيع الرقمي
def get_reezn_dynamic_channels(session):
    global FOUND_FORMULA
    endpoints = [
        "https://server.reezntv.com/api/v2/get_sports_db.php",
        "https://server.reezntv.com/api/v2/get_channels_db.php"
    ]
    
    current_time_str = str(int(time.time()))
    current_date_str = time.strftime("%d_%m_%Y")
    channels_found = []
    
    for url in endpoints:
        if "get_sports_db.php" in url:
            if FOUND_FORMULA or (MANUAL_REEZN_SIG and MANUAL_REEZN_TIME):
                raw_data = f'{{"secret":"blaidyalah","date":"{current_date_str}"}}\n'
                sig, req_time = get_signature_for_request(current_time_str, raw_data)
            else:
                raw_data = '{"secret":"blaidyalah","date":"05_07_2026"}\n'
                sig, req_time = "ba571e3a4bea773a696897cdd96a26d123e4ada84ed18a4220ac603394838e1f", "1783256939"
        else:
            raw_data = '{"secret":"blaidyalah"}'
            if FOUND_FORMULA or (MANUAL_REEZN_SIG and MANUAL_REEZN_TIME):
                sig, req_time = get_signature_for_request(current_time_str, raw_data)
            else:
                sig, req_time = "dc2b63ba68b26969446821486d5cea4d18927fbb390d3f173863aaa999daebd2", "1783251653"

        # إجبار الترويسات على المطابقة الكاملة لتجنب صدور الـ ECONNRESET
        headers = {
            "Accept-Encoding": "gzip",
            "Cache-Control": "no-cache",
            "Connection": "Keep-Alive",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "okhttp/4.12.0",
            "X-DEBUG-MODE": "1",
            "X-Request-Signature": sig,
            "X-Request-Time": req_time
        }
        
        try:
            response = session.post(url, data=raw_data, headers=headers, timeout=12)
            print(f"📡 الاتصال بـ {url} - كود الحالة: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                raw_list = find_list_in_json(data)
                print(f"   📊 تم جلب قاعدة البيانات بنجاح، تحتوي على ({len(raw_list)}) قناة.")
                
                for ch in raw_list:
                    if isinstance(ch, dict):
                        name = ch.get("name") or ch.get("title") or ch.get("channel_title") or ch.get("channel_name") or ch.get("channel_title_ar")
                        url_val = ch.get("url") or ch.get("link") or ch.get("stream") or ch.get("stream_url") or ch.get("channel_url") or ch.get("file")
                        if name and url_val:
                            channels_found.append({"name": name, "url": url_val})
            else:
                print(f"   ⚠️ فشل الطلب بكود حالة: {response.status_code} (قد يكون التوقيع منتهي الصلاحية).")
        except Exception as e:
            print(f"   ⚠️ خطأ أثناء جلب القنوات من الرابط ({url}): {e}")
            
    return channels_found

# تشغيل نظام الفحص والشفاء الذاتي للتواقيع قبل البدء في معالجة القنوات
find_hashing_formula()

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

# 2. كشف وتجهيز باقة قنوات LIVE المباشرة ديناميكياً
print("\n⚽ جاري كشف وتجهيز مجموعة قنوات LIVE المباشرة...")
live_separator = "# ==================== مجموعة قنوات LIVE ===================="

active_majed_channels = get_majed_dynamic_channels(session)
live_content = ""
timestamp = int(time.time() * 1000)

for channel in active_majed_channels:
    live_url = f"http://majed-koora.live/stream.php?channel={channel}&file=stream.m3u8&v={timestamp}"
    display_name = channel.replace("majedsports", "Majed Sport ").title()
    
    live_content += (
        f'#EXTINF:-1 tvg-logo="" group-title="LIVE", {display_name} FHD\n'
        f'{live_url}\n'
        f'#EXTINF:-1 tvg-logo="" group-title="LIVE", {display_name} HD\n'
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

use_basha_proxy = check_basha_proxy_status(session)
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
                
                exclude_tags = [
                    "vip de", "vip uk", "vip ru", "vip bg", "vip pl", "vip es", "vip tr", "vip ph", "vip it", "vip br", "vip us", "vip dk", "vip hu", "vip ro",
                    "de:", "uk:", "ru:", "bg:", "pl:", "es:", "ca:", "tr:", "ph:", "au:", "cz:", "usa:", "it:", "br:", "hu:", "us:", "ro:", "dk:", "usa)", "hu", "ro", "dk", "usa",
                    " de ", " uk ", " ru ", " bg ", " pl ", " es ", " ca ", " tr ", " ph ", " au ", " cz ", " usa ", " it ", " br ", " hu ", " us ", " ro ", " dk ",
                    "[de]", "[uk]", "[ru]", "[bg]", "[pl]", "[es]", "[ca]", "[tr]", "[ph]", "[au]", "[cz]", "[usa]", "[it]", "[br]", "[hu]", "[us]", "[ro]", "[dk]",
                    "(de)", "(uk)", "(ru)", "(bg)", "(pl)", "(es)", "(ca)", "(tr)", "(ph)", "(au)", "(cz)", "(usa)", "(it)", "(br)", "(hu)", "(us)", "(ro)", "(dk)"
                ]
                
                if any(tag in channel_name_lower for tag in exclude_tags):
                    continue
                
                is_bein = "bein" in channel_name_lower
                
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
                
                if is_bein or is_arabic_premium or is_french_target:
                    if use_basha_proxy:
                        final_basha_url = f"http://live-albashatv.site/stream?url={raw_url}"
                    else:
                        final_basha_url = raw_url
                    
                    basha_content += f'#EXTINF:-1 tvg-logo="" group-title="AL BASHA TV", {channel_name}\n'
                    basha_content += f'{final_basha_url}\n'
                    
                    seen_basha_urls.add(raw_url)
                    matched_count += 1
    except Exception as e:
        print(f"❌ خطأ أثناء جلب قنوات الباشا: {e}")

print(f"🎯 تم استخراج وتصفية ({matched_count}) قناة من الباشا بنجاح.")

# 4. جلب وتنسيق باقة قنوات ياسين تيفي (Yacine TV) ديناميكياً بالكامل
print("\n🚀 جاري جلب قنوات ياسين تيفي (Yacine TV)...")
yacine_separator = "# ==================== مجموعة قنوات BEIN MAX YACINE TV ===================="

targets = {
    "/api/categories/90/channels": "FHD",
    "/api/categories/89/channels": "HD"
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
for category_endpoint, quality in targets.items():
    print(f"🔄 جاري سحب باقة ياسين بجودة {quality}...")
    channels_data = fetch_and_decrypt_yacine_dynamic(session, category_endpoint, yacine_headers)
    
    if channels_data and 'data' in channels_data:
        channels_list = channels_data['data']
        for index, channel in enumerate(channels_list):
            channel_name = channel.get('name')
            channel_id = channel.get('id')
            
            channel_name_lower = channel_name.lower() if channel_name else ""
            
            is_target = (
                "max" in channel_name_lower or 
                "bein" in channel_name_lower or 
                "ماكس" in channel_name_lower or 
                "بين" in channel_name_lower or
                "سبورت" in channel_name_lower
            )
            
            if not is_target:
                continue
                
            print(f"   ⏳ [{index + 1}/{len(channels_list)}] جاري استخراج: {channel_name}...")
            channel_detail_endpoint = f"/api/channel/{channel_id}"
            detail_data = fetch_and_decrypt_yacine_dynamic(session, channel_detail_endpoint, yacine_headers)
            
            if detail_data and 'data' in detail_data:
                streams = detail_data['data']
                for stream_idx, stream in enumerate(streams):
                    raw_url = stream.get('url')
                    if not raw_url:
                        continue
                        
                    server_label = stream.get('name', f"Server {stream_idx + 1}")
                    final_url = get_final_url(raw_url)
                    
                    if final_url and "/dash/.mpd" in final_url:
                        final_url = final_url.replace("/dash/.mpd", "/playlist.m3u8")
                    
                    final_url_with_headers = f"{final_url}|User-Agent={ua_value}&Referer={referer_value}"
                    display_name = f"{channel_name} {quality} - {server_label}"
                    
                    yacine_content += f'#EXTINF:-1 tvg-logo="" group-title="BEIN MAX YACINE TV", {display_name}\n'
                    yacine_content += f'{final_url_with_headers}\n'
                    print(f"      ✔️ نجاح استخراج السيرفر: {server_label}")
            time.sleep(0.5)

# 5. جلب وتنسيق باقة قنوات Reezn TV الجديدة (الفلترة لـ beIN Sports و beIN MAX فقط)
print("\n🚀 جاري جلب وتصفية قنوات Reezn TV الجديدة...")
reezn_separator = "# ==================== مجموعة قنوات REEZN TV ===================="

reezn_raw_channels = get_reezn_dynamic_channels(session)
reezn_content = ""
seen_reezn_urls = set()
matched_reezn_count = 0

for ch in reezn_raw_channels:
    ch_name = ch["name"]
    raw_url = ch["url"]
    
    if not raw_url or raw_url in seen_reezn_urls:
        continue
        
    ch_name_lower = ch_name.lower()
    
    is_bein_or_max = (
        "bein" in ch_name_lower or
        "max" in ch_name_lower or
        "بين" in ch_name_lower or
        "بي ان" in ch_name_lower or
        "بي إن" in ch_name_lower or
        "ماكس" in ch_name_lower
    )
    
    if is_bein_or_max:
        final_url = get_final_url(raw_url)
        
        if final_url and "/dash/.mpd" in final_url:
            final_url = final_url.replace("/dash/.mpd", "/playlist.m3u8")
            
        reezn_content += f'#EXTINF:-1 tvg-logo="" group-title="REEZN TV", {ch_name}\n'
        reezn_content += f'{final_url}\n'
        seen_reezn_urls.add(raw_url)
        matched_reezn_count += 1

print(f"🎯 تم استخراج وتصفية ({matched_reezn_count}) قناة beIN و MAX من باقة Reezn TV بنجاح.")

# دمج المحتوى بالترتيب مع الحفاظ الكامل على قنواتك اليدوية
final_m3u_content = f"#EXTM3U\n\n{live_separator}\n{live_content}\n\n{basha_separator}\n{basha_content}\n\n{yacine_separator}\n{yacine_content}\n\n{reezn_separator}\n{reezn_content}\n\n# ==================== قنواتك اليدوية والثابتة ====================\n{static_clean}"

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
