import base64
import requests
import json
import time
import os
import urllib.parse
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

GIST_ID = os.environ.get("GIST_ID")
GITHUB_TOKEN = os.environ.get("GIST_TOKEN")

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

def create_session():
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

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

def get_final_url(raw_url):
    browser_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        r_redirect = requests.get(raw_url, headers=browser_headers, allow_redirects=False, timeout=10)
        if r_redirect.status_code in [301, 302]:
            return r_redirect.headers.get('Location')
    except Exception:
        pass
    return raw_url

def extract_static_channels(m3u_content):
    lines = m3u_content.splitlines()
    static_lines, current_block = [], []
    exclude = ["def.yacinelive.com", "metava.online", "re.ycn-redirect.com", "BEIN MAX YACINE TV", "albashatv.site", "playcasta.online", "AL BASHA TV", "majed-koora.live", "195.182.16.45"]
    for line in lines:
        line_str = line.strip()
        if not line_str or line_str.startswith("#EXTM3U") or "=====" in line_str:
            continue
        if line_str.startswith("#EXTINF"):
            if current_block:
                block = "".join(current_block)
                if not any(kw in block for kw in exclude):
                    static_lines.extend(current_block + [""])
            current_block = [line_str]
        elif line_str.startswith("#") or line_str.startswith("http") or line_str.startswith("rtmp"):
            if current_block:
                current_block.append(line_str)
            else:
                if not any(kw in line_str for kw in exclude):
                    static_lines.append(line_str)
    if current_block and not any(kw in "".join(current_block) for kw in exclude):
        static_lines.extend(current_block)
    return "\n".join(static_lines).strip()

def is_arabic_or_french(name):
    name_low = name.lower()
    if any('\u0600' <= char <= '\u06FF' for char in name):
        return True
    arabic_keywords = ["bein", "osn", "mbc", "ssc", "shahid", "art", "rotana", "al jazeera", "vip", "basha", "al fajer", "fajer", "stc", "thamanya", "alkass", "alwan", "box office", "boxoffice", "بوكس"]
    if any(kw in name_low for kw in arabic_keywords):
        return True
    french_keywords = ["fr:", "fr ", "(fr)", "[fr]", "france", "canal", "rmc", "tf1", "m6", "ocs", "cine", "ciné", "gulli", "tiji", "cartoon", "disney", "nickelodeon", "nat geo", "discovery", "ushuaia", "histoire", "science"]
    if any(kw in name_low for kw in french_keywords):
        return True
    return False

# 1. جلب محتوى Gist وتصفية القنوات الثابتة
print("📂 جاري جلب محتوى الـ Gist الحالي...")
gist_api_url = f"https://api.github.com/gists/{GIST_ID}"
gist_headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
static_clean, filename = "", "kz.m3u"

try:
    gist_response = requests.get(gist_api_url, headers=gist_headers, timeout=15)
    if gist_response.status_code == 200:
        gist_data = gist_response.json()
        filename = list(gist_data['files'].keys())[0]
        static_clean = extract_static_channels(gist_data['files'][filename]['content'])
        print("✔️ تم حفظ القنوات اليدوية المكتوبة مسبقاً.")
    else:
        print(f"❌ فشل جلب الـ Gist. كود الحالة: {gist_response.status_code}")
        exit(1)
except Exception as e:
    print(f"❌ خطأ Gist API: {e}")
    exit(1)

session = create_session()

# 2. جلب وتصفية قنوات السيرفر الأول (Match LIVE TV)
print("\n⚽ جاري تهيئة مجموعة قنوات LIVE المباشرة...")
live_separator = "# ==================== مجموعة قنوات LIVE ===================="
live_url = "https://majed-koora.live/stream.php?channel=majed20267&file=stream.m3u8"
live_content = (
    f'#EXTINF:-1 tvg-logo="" group-title="LIVE", Match LIVE TV FHD\n'
    f'{live_url}\n'
    f'#EXTINF:-1 tvg-logo="" group-title="LIVE", Match LIVE TV HD\n'
    f'{live_url}\n'
)

# 2.5 جلب وتصفية باقة قنوات General TV الجديدة ديناميكياً من السيرفر (تطبيق الاتفاق)
print("\n📺 جاري جلب وتصفية قنوات General TV من السيرفر الجديد...")
general_separator = "# ==================== مجموعة قنوات GENERAL TV ===================="
general_url = "http://195.182.16.45:8080/get.php?username=omar777&password=01103978590&output=m3u_plus"
general_ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_7 like Mac OS X) AppleWebKit/605.1.15"
general_headers = {"User-Agent": general_ua}
general_content, general_count = "", 0

try:
    response = session.get(general_url, headers=general_headers, timeout=25)
    if response.status_code == 200:
        lines = response.text.splitlines()
        current_inf = ""
        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue
            if line_str.startswith("#EXTINF"):
                current_inf = line_str
            elif line_str.startswith("http"):
                if current_inf:
                    ch_name = current_inf.split(",", 1)[1].strip() if "," in current_inf else ""
                    ch_name_low = ch_name.lower()
                    
                    # الفلترة المطلوبة للجنرال تيفي: بي إن سبورت، ماكس، ألوان، الفجر، بي إن الفرنسية
                    is_bein = "bein" in ch_name_low
                    is_alwan = any(kw in ch_name_low for kw in ["alwan", "الوان", "ألوان"])
                    is_fajer = any(kw in ch_name_low for kw in ["fajer", "al fajer", "الفجر"])
                    
                    if is_bein or is_alwan or is_fajer:
                        new_inf = f'#EXTINF:-1 tvg-logo="" group-title="General TV", {ch_name}'
                        # إضافة هيدر هاتف الآيفون تلقائياً في نهاية الرابط لضمان التشغيل على الريسيفر بدون حظر
                        stream_url = f"{line_str}|User-Agent={general_ua}"
                        general_content += f"{new_inf}\n{stream_url}\n"
                        general_count += 1
                    current_inf = ""
    else:
        print(f"❌ فشل جلب قنوات General TV. كود الحالة: {response.status_code}")
except Exception as e:
    print(f"❌ خطأ في السيرفر الجديد: {e}")

print(f"🎯 تم استخراج وتصفية ({general_count}) قناة من General TV بنجاح.")

# 3. جلب وتصفية قنوات الباشا تيفي (Al Basha TV)
print("\n🚀 جاري جلب قنوات الباشا تيفي...")
basha_separator = "# ==================== مجموعة قنوات AL BASHA TV ===================="
basha_api_url = "https://albashatv.site/api.php"
basha_headers = {"Content-Type": "application/x-www-form-urlencoded", "Connection": "Keep-Alive", "User-Agent": "okhttp/3.9.1"}
basha_payloads = ["method=o6&event=view", "method=o2&event=view"]
basha_targets = ["bein max", "bein sport", "osn", "netflix", "bein media", "hbo", "amazon prime", "amazon", "vip"]
basha_content, seen_basha_urls, basha_count = "", set(), 0

for payload in basha_payloads:
    try:
        res = session.post(basha_api_url, headers=basha_headers, data=payload, timeout=15)
        if res.status_code == 200:
            for ch in res.json():
                name = ch.get('name', '')
                url = ch.get('url', '')
                if not url or url in seen_basha_urls:
                    continue
                
                name_low = name.lower()
                exclude_tags = ["vip de", "vip uk", "vip ru", "vip bg", "vip pl", "vip es", "vip tr", "vip ph", "vip it", "vip br", "vip us", "vip dk", "vip hu", "vip ro", "de:", "uk:", "ru:", "bg:", "pl:", "es:", "ca:", "tr:", "ph:", "au:", "cz:", "usa:", "it:", "br:", "hu:", "us:", "ro:", "dk:", "usa)", "hu", "ro", "dk", "usa", " de ", " uk ", " ru ", " bg ", " pl ", " es ", " ca ", " tr ", " ph ", " au ", " cz ", " usa ", " it ", " br "]
                if any(tag in name_low for tag in exclude_tags):
                    continue
                
                if any(target in name_low for target in basha_targets):
                    final_url = f"http://live-albashatv.site//stream?url={url}" if not url.startswith("http://live-albashatv.site//stream?url=") else url
                    basha_content += f'#EXTINF:-1 tvg-logo="" group-title="AL BASHA TV", {name}\n{final_url}\n'
                    seen_basha_urls.add(url)
                    basha_count += 1
    except Exception as e:
        print(f"❌ خطأ الباشا: {e}")

print(f"🎯 تم استخراج ({basha_count}) قناة من الباشا.")

# 4. جلب وتنسيق باقة قنوات ياسين تيفي (Yacine TV)
print("\n🚀 جاري جلب قنوات ياسين تيفي...")
yacine_separator = "# ==================== مجموعة قنوات BEIN MAX YACINE TV ===================="
targets = {"https://def.yacinelive.com/api/categories/90/channels": "FHD"}
yacine_headers = {"Accept": "application/json", "Accept-Encoding": "gzip", "Connection": "Keep-Alive", "User-Agent": "okhttp/4.12.0"}
ua_val = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
ref_val = "http://re.ycn-redirect.com/"
yacine_content = ""

for cat_url, qual in targets.items():
    ch_data = fetch_and_decrypt_yacine(session, cat_url, yacine_headers)
    if ch_data and 'data' in ch_data:
        for index, ch in enumerate(ch_data['data']):
            name = ch.get('name')
            ch_id = ch.get('id')
            name_low = name.lower() if name else ""
            if not ("max" in name_low or "bein sport" in name_low):
                continue
                
            print(f"   ⏳ [{index + 1}] جاري استخراج: {name}...")
            det_url = f"https://def.yacinelive.com/api/channel/{ch_id}"
            det_data = fetch_and_decrypt_yacine(session, det_url, yacine_headers)
            if det_data and 'data' in det_data and det_data['data']:
                raw_url = det_data['data'][0].get('url')
                fin_url = get_final_url(raw_url)
                yac_url = f"{fin_url}|User-Agent={ua_val}&Referer={ref_val}"
                yacine_content += f'#EXTINF:-1 tvg-logo="" group-title="BEIN MAX YACINE TV", {name} {qual}\n{yac_url}\n'
                print("      ✔️ نجاح.")
            time.sleep(0.5)

# 5. دمج المحتوى بالترتيب الجديد وتحديث الـ Gist
final_m3u_content = f"#EXTM3U\n\n{live_separator}\n{live_content}\n\n{general_separator}\n{general_content}\n\n{basha_separator}\n{basha_content}\n\n{yacine_separator}\n{yacine_content}\n\n# ==================== قنواتك اليدوية والثابتة ====================\n{static_clean}"
update_data = {"files": {filename: {"content": final_m3u_content}}}
up_res = requests.patch(gist_api_url, headers=gist_headers, json=update_data)

if up_res.status_code == 200:
    print("🎉 تم التحديث بنجاح! جميع القنوات والأسماء الجديدة تعمل الآن ومتاحة للريسيفر.")
else:
    print(f"❌ فشل تحديث الـ Gist. كود الحالة: {up_res.status_code}")
