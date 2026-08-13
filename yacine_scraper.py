import os
import requests
import re
from collections import defaultdict
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

# ==========================================
# 1. الإعدادات ومتغيرات البيئة المعرفة
# ==========================================
GITHUB_TOKEN = os.environ.get("GIST_TOKEN")

GIST_S1_ID = os.environ.get("GIST_S1_ID") or "9c22160f66145ec833f3df816ed80239"  # صفحة s1.m3u (وان+)
GIST_KZ_ID = os.environ.get("GIST_KZ_ID") or "2b7f88f1e20b990504349ccd761b4de3"  # صفحة kz.m3u (APP2 القديم)

APP2_M3U_URL = os.environ.get(
    "APP2_M3U_URL",
    "http://185.191.126.127:8080/get.php?username=b0:99:d7:15:88:50&password=3090914536649669&type=m3u_plus&output=ts"
)

WANPLUS_API_ENDPOINT = os.environ.get(
    "WANPLUS_API_ENDPOINT",
    "https://atared.serv00.net/lion_panel_4k_x91/api/verificar_codigo.php"
)
ACTIVATION_CODE = os.environ.get("ACTIVATION_CODE", "V1")

# ==========================================
# 2. إنشاء جلسة اتصال مستقرة
# ==========================================
def create_session():
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries, pool_connections=30, pool_maxsize=30)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

# ==============================================================================
# SECTION A: كود ودالة صفحة kz.m3u الأصلية القديمة (بدون أي تعديل أو مساس إطلاقاً)
# ==============================================================================
EXCLUDE_TAGS_KZ = [
    "vip de", "vip uk", "vip ru", "vip bg", "vip pl", "vip es", "vip tr", "vip ph", "vip it", "vip br", "vip us", "vip dk", "vip hu", "vip ro", "vip pt", "vip nl", "vip se", "vip no", "vip al",
    "de:", "uk:", "ru:", "bg:", "pl:", "es:", "ca:", "tr:", "ph:", "au:", "cz:", "usa:", "it:", "br:", "hu:", "us:", "ro:", "dk:", "usa)", "al:", "pt:", "nl:", "il:", "so:", "no:", "se:", "fi:", "gr:", "ex-yu:", "ex yu:", "sk:", "in:", "pk:", "bd:", "af:", "ir:", "he:", "sr:", "hr:", "ba:", "mk:", "si:",
    " de ", " uk ", " ru ", " bg ", " pl ", " es ", " ca ", " tr ", " ph ", " au ", " cz ", " usa ", " it ", " br ", " hu ", " us ", " ro ", " dk ", " al ", " pt ", " nl ", " il ", " so ", " no ", " se ",
    "[de]", "[uk]", "[ru]", "[bg]", "[pl]", "[es]", "[ca]", "[tr]", "[ph]", "[au]", "[cz]", "[usa]", "[it]", "[br]", "[hu]", "[us]", "[ro]", "[dk]", "[al]", "[pt]", "[nl]", "[il]", "[so]", "[no]", "[se]",
    "(de)", "(uk)", "(ru)", "(bg)", "(pl)", "(es)", "(ca)", "(tr)", "(ph)", "(au)", "(cz)", "(usa)", "(it)", "(br)", "(hu)", "(us)", "(ro)", "(dk)", "(al)", "(pt)", "(nl)", "(il)", "(so)", "(no)", "(se)"
]

def classify_channel_kz(channel_name):
    name_lower = channel_name.lower().strip()
    
    if any(tag in name_lower for tag in EXCLUDE_TAGS_KZ):
        return None

    if name_lower.startswith("usa") or "usa h" in name_lower:
        return None

    if "tod" in name_lower:
        return "BEIN TOD"

    if "bein" in name_lower:
        if any(kw in name_lower for kw in ["fr", "france", "french", "فرنسية", "فرنسيه"]):
            if any(kw in name_lower for kw in ["bein sport", "bein sports", "h.265", "h265", "hevc"]):
                return "BEIN SPORT FR"
            return "FRENCH"

        bein_media_keywords = [
            "movie", "movies", "mov", "cinema", "سينما", "drama", "دراما", 
            "series", "مسلسلات", "gourmet", "gorment", "fatafeat", "فتافيت",
            "fox", "life", "action", "bbc", "earth", "star", "world",
            "baraeam", "baraem", "براعم", "jeem", "جيم", "nat geo", "national", "wild",
            "box office", "boxoffice", "pop up", "popup", "media", "entertainment", 
            "junior", "news", "اخبار", "أخبار", "افلام", "أفلام"
        ]
        if any(kw in name_lower for kw in bein_media_keywords):
            return "BEIN MEDIA"

        bein_sports_triggers = ["bein sport", "bein sports", "h.265", "h265", "hevc", "4k"]
        if any(trigger in name_lower for trigger in bein_sports_triggers):
            return "BEIN SPORT AR"
            
        return None

    if any(kw in name_lower for kw in ["al jazeera", "aljazeera", "الجزيرة", "al arabiya", "alarabiya", "العربية", "al hadath", "alhadath", "الحدث", "sky news", "سكاي نيوز"]):
        if "sky" in name_lower:
            if any(ar in name_lower for ar in ["arabic", "arabia", "عرب", "عربية", "سكاي نيوز"]):
                return "ARABIC NEWS"
        else:
            return "ARABIC NEWS"

    kids_ar_kw = [
        "tom and jerry", "tom & jerry", "توم وجيري", "توم وجري", "masha", "ماشا", 
        "dora", "دورا", "spacetoon", "سبيستون", "سبيس تون", "wanasat", "وناسة", 
        "baraem", "براعم", "cn arabia", "cartoon network", "كرتون نتورك", "jeem", 
        "تلفزيون جيم", "قناة جيم", "اطفال", "أطفال"
    ]
    kids_fr_kw = ["gulli", "tiji", "disney kids", "nickelodeon", "boing", "piwi", "cartoon network fr"]
    if any(kw in name_lower for kw in kids_ar_kw) or any(kw in name_lower for kw in kids_fr_kw):
        return "KIDS"

    doc_keywords = ["nat geo", "national geo", "discovery", "documentary", "الوثائقية", "وثائقية", "ushuaia", "histoire", "science"]
    if any(kw in name_lower for kw in doc_keywords):
        foreign_doc_tags = ["al:", "pt:", "nl:", "il:", "so:", "no:", "se:", "de:", "uk:", "es:", "it:", "tr:", "ru:", "pl:", "bg:", "cz:", "hu:", "ro:", "dk:", "us:"]
        if not any(foreign in name_lower for foreign in foreign_doc_tags):
            return "DOCUMENTARY"

    french_tags = ["fr:", "fr ", "(fr)", "[fr]", "france"]
    french_kw = [
        "tf1", "m6", "canal+", "canal", "rmc", "eurosport", "lequipe", "l'equipe", 
        "ocs", "cine", "ciné", "w9", "tmc", "tfx", "gulli", "tiji", "france 2", 
        "france 3", "france 4", "france 5", "france 24", "bfm"
    ]
    if any(tag in name_lower for tag in french_tags) or any(kw in name_lower for kw in french_kw):
        return "FRENCH"

    if any(kw in name_lower for kw in ["alwan sport", "alwan sports", "الوان سبورت", "ألوان سبورت", "الوان الرياضية", "ألوان الرياضية"]):
        return "ALWAN SPORT"

    if "fajer" in name_lower or "الفجر" in name_lower:
        return "AL FAJER"

    algeria_keywords = [
        "algeria", "algerie", "algérie", "algerien", "entv", "الجزائر", "الجزائرية", 
        "الهداف", "el heddaf", "el bilad", "البلاد", "الشروق", "echorouk", "النهار", 
        "ennahar", "samira", "سميرة", "numidia", "نوميديا", "الوطنية", "el watania", "al24"
    ]
    if any(kw in name_lower for kw in algeria_keywords):
        return "ALGERIA"

    if "alwan" in name_lower or "ألوان" in name_lower or "الوان" in name_lower:
        return "ALWAN MOVIES"

    if "rotana" in name_lower or "روتانا" in name_lower:
        return "ROTANA"

    if "mbc" in name_lower or "ام بي سي" in name_lower or "إم بي سي" in name_lower:
        return "MBC GROUP"

    if any(kw in name_lower for kw in ["box office", "boxoffice", "box-office", "بوكس أوفيس", "بوكس اوفيس"]):
        return "BOX OFFICE"

    if "netflix" in name_lower or "نتفليكس" in name_lower or "نتفلكس" in name_lower:
        return "NETFLIX"

    if "amazon" in name_lower or "prime" in name_lower or "أمازون" in name_lower or "امازون" in name_lower:
        return "AMAZON PRIME"

    if "hbo" in name_lower:
        return "HBO"

    if any(kw in name_lower for kw in ["showtime", "شوتايم"]):
        return "SHOWTIME"

    if any(kw in name_lower for kw in ["home cinema", "homecinema", "هوم سينما", "هومسينما"]):
        return "HOME CINEMA"

    if any(kw in name_lower for kw in ["mh", "ام اتش", "أم اتش"]):
        return "MH GROUP"

    return None

PREFERRED_ORDER_KZ = [
    "BEIN SPORT AR", 
    "BEIN TOD", 
    "BEIN SPORT FR", 
    "BEIN MEDIA", 
    "ALWAN SPORT", 
    "AL FAJER", 
    "KIDS", 
    "ALGERIA", 
    "ARABIC NEWS", 
    "ALWAN MOVIES", 
    "ROTANA", 
    "MBC GROUP", 
    "BOX OFFICE", 
    "NETFLIX", 
    "AMAZON PRIME", 
    "HBO", 
    "SHOWTIME", 
    "HOME CINEMA", 
    "MH GROUP", 
    "DOCUMENTARY",
    "FRENCH"
]

def process_m3u_kz(m3u_text):
    grouped_channels = defaultdict(list)
    total_count = 0
    seen_urls = set()

    lines = m3u_text.splitlines()
    current_extinf = ""

    for line in lines:
        line_str = line.strip()
        if line_str.startswith("#EXTINF:"):
            current_extinf = line_str
        elif line_str.startswith("http://") or line_str.startswith("https://"):
            if current_extinf:
                parts = current_extinf.split(",")
                channel_name = parts[-1].strip() if len(parts) > 1 else "Channel"

                group_title = classify_channel_kz(channel_name)
                if group_title:
                    logo = ""
                    if 'tvg-logo="' in current_extinf:
                        logo = current_extinf.split('tvg-logo="')[1].split('"')[0]

                    final_url = line_str.replace(".m3u8", ".ts")
                    final_url = final_url.replace("217.60.15.177:8080", "185.191.126.127:8080")
                    final_url = re.sub(r'/live/+', '/live//', final_url)

                    if final_url in seen_urls:
                        continue

                    vlc_opts_str = (
                        "#EXTVLCOPT:http-header=Icy-MetaData: 1\n"
                        "#EXTVLCOPT:http-user-agent=okhttp/3.9.1\n"
                        "#EXTVLCOPT:http-referrer=http://albashatv.site/"
                    )

                    entry = f'#EXTINF:-1 tvg-logo="{logo}" group-title="{group_title}",{channel_name}\n{vlc_opts_str}\n{final_url}'
                    grouped_channels[group_title].append(entry)
                    seen_urls.add(final_url)
                    total_count += 1
                current_extinf = ""

    m3u_lines = ["#EXTM3U"]
    for group in PREFERRED_ORDER_KZ:
        if group in grouped_channels and grouped_channels[group]:
            m3u_lines.extend(grouped_channels[group])

    return "\n".join(m3u_lines), total_count


# ==============================================================================
# SECTION B: كود التصفية الصارمة المخصص لصفحة s1.m3u فقط (وان+)
# ==============================================================================
EXCLUDE_TAGS_S1 = [
    "vip de", "vip uk", "vip ru", "vip bg", "vip pl", "vip es", "vip tr", "vip ph", "vip it", "vip br", "vip us", "vip dk", "vip hu", "vip ro", "vip pt", "vip nl", "vip se", "vip no", "vip al",
    "de:", "uk:", "ru:", "bg:", "pl:", "es:", "ca:", "tr:", "ph:", "au:", "cz:", "usa:", "it:", "br:", "hu:", "us:", "ro:", "dk:", "usa)", "al:", "pt:", "nl:", "il:", "so:", "no:", "se:", "fi:", "gr:", "ex-yu:", "ex yu:", "sk:", "in:", "pk:", "bd:", "af:", "ir:", "he:", "sr:", "hr:", "ba:", "mk:", "si:",
    " de ", " uk ", " ru ", " bg ", " pl ", " es ", " ca ", " tr ", " ph ", " au ", " cz ", " usa ", " it ", " br ", " hu ", " us ", " ro ", " dk ", " al ", " pt ", " nl ", " il ", " so ", " no ", " se ",
    "[de]", "[uk]", "[ru]", "[bg]", "[pl]", "[es]", "[ca]", "[tr]", "[ph]", "[au]", "[cz]", "[usa]", "[it]", "[br]", "[hu]", "[us]", "[ro]", "[dk]", "[al]", "[pt]", "[nl]", "[il]", "[so]", "[no]", "[se]",
    "(de)", "(uk)", "(ru)", "(bg)", "(pl)", "(es)", "(ca)", "(tr)", "(ph)", "(au)", "(cz)", "(usa)", "(it)", "(br)", "(hu)", "(us)", "(ro)", "(dk)", "(al)", "(pt)", "(nl)", "(il)", "(so)", "(no)", "(se)",
    "china", "christian", "cine mania india", "cine mania usa", "cric life", "cricket", "denmark", "ethiopia", "finland", "germany", "greece", "india", "malaysia", "nepal", "pakistan", "poland", "portugal", "romania", "russia", "thailand", "turkey", "vietnam"
]

def classify_channel_s1(channel_name, orig_group=""):
    full_text = f"{channel_name} {orig_group}".lower().strip()
    name_lower = channel_name.lower().strip()

    # 1. استبعاد الدولة أو اللغات الأجنبية فوراً
    if any(tag in full_text for tag in EXCLUDE_TAGS_S1):
        return None

    if name_lower.startswith("usa") or "usa h" in full_text:
        return None

    # 2. BEIN TOD
    if any(kw in full_text for kw in ["tod", "تود"]):
        return "BEIN TOD"

    # 3. BEIN SPORT AR / FR / MEDIA
    if any(kw in full_text for kw in ["bein", "بي ان", "بي إن"]):
        if any(kw in full_text for kw in ["fr", "france", "french", "فرنسية", "فرنسيه"]):
            if any(kw in full_text for kw in ["sport", "sports", "h.265", "h265", "hevc"]):
                return "BEIN SPORT FR"
            return "FRENCH"

        bein_media_keywords = [
            "movie", "movies", "mov", "cinema", "سينما", "drama", "دراما", 
            "series", "مسلسلات", "gourmet", "gorment", "fatafeat", "فتافيت",
            "fox", "life", "action", "bbc", "earth", "star", "world",
            "baraeam", "baraem", "براعم", "jeem", "جيم", "nat geo", "national", "wild",
            "box office", "boxoffice", "pop up", "popup", "media", "entertainment", 
            "junior", "news", "اخبار", "أخبار", "افلام", "أفلام", "hgtv", "starz"
        ]
        if any(kw in full_text for kw in bein_media_keywords):
            return "BEIN MEDIA"

        bein_sports_triggers = ["sport", "sports", "h.265", "h265", "hevc", "4k", "hd", "sd"]
        if any(trigger in full_text for trigger in bein_sports_triggers):
            return "BEIN SPORT AR"

    # 4. MBC GROUP
    if any(kw in full_text for kw in ["mbc", "m b c", "ام بي سي", "إم بي سي", "mpc"]):
        return "MBC GROUP"

    # 5. ROTANA
    if any(kw in full_text for kw in ["rotana", "روتانا"]):
        return "ROTANA"

    # 6. HBO
    if any(kw in full_text for kw in ["hbo", "h b o", "اتش بي او", "اتش بي أوا"]):
        return "HBO"

    # 7. BOX OFFICE (OSN, Box Office, ART)
    if any(kw in full_text for kw in ["osn", "o s n", "او اس ان", "أو إس إن", "box office", "boxoffice", "art vip", "ارتي"]):
        return "BOX OFFICE"

    # 8. NETFLIX (Netflix, Shahid)
    if any(kw in full_text for kw in ["netflix", "نتفليكس", "نتفلكس", "shahid", "شاهد"]):
        return "NETFLIX"

    # 9. AMAZON PRIME
    if any(kw in full_text for kw in ["amazon", "prime", "أمازون", "امازون"]):
        return "AMAZON PRIME"

    # 10. SHOWTIME
    if any(kw in full_text for kw in ["showtime", "شوتايم"]):
        return "SHOWTIME"

    # 11. HOME CINEMA
    if any(kw in full_text for kw in ["home cinema", "homecinema", "هوم سينما"]):
        return "HOME CINEMA"

    # 12. MH GROUP
    if any(kw in full_text for kw in ["mh", "ام اتش", "أم اتش"]):
        return "MH GROUP"

    # 13. ALWAN SPORT
    if any(kw in full_text for kw in ["alwan sport", "alwan sports", "الوان سبورت", "ألوان سبورت", "الوان الرياضية", "ألوان الرياضية"]):
        return "ALWAN SPORT"

    # 14. AL FAJER
    if "fajer" in full_text or "الفجر" in full_text:
        return "AL FAJER"

    # 15. ALWAN MOVIES
    if "alwan" in full_text or "ألوان" in full_text or "الوان" in full_text:
        return "ALWAN MOVIES"

    # 16. ARABIC NEWS (حصراً: الجزيرة، العربية، الحدث، سكاي نيوز عربية)
    if any(kw in full_text for kw in ["al jazeera", "aljazeera", "الجزيرة", "al arabiya", "alarabiya", "العربية", "al hadath", "alhadath", "الحدث", "sky news", "سكاي نيوز"]):
        if "sky" in full_text:
            if any(ar in full_text for ar in ["arabic", "arabia", "عرب", "عربية", "سكاي نيوز"]):
                return "ARABIC NEWS"
        else:
            return "ARABIC NEWS"

    # 17. KIDS (عربي وفرنسي فقط)
    kids_ar_kw = [
        "tom and jerry", "tom & jerry", "توم وجيري", "توم وجري", "masha", "ماشا", 
        "dora", "دورا", "spacetoon", "سبيستون", "سبيس تون", "wanasat", "وناسة", 
        "baraem", "براعم", "cn arabia", "cartoon network", "كرتون نتورك", "jeem", 
        "تلفزيون جيم", "قناة جيم", "اطفال", "أطفال"
    ]
    kids_fr_kw = ["gulli", "tiji", "disney kids", "nickelodeon", "boing", "piwi", "cartoon network fr"]
    if any(kw in full_text for kw in kids_ar_kw) or any(kw in full_text for kw in kids_fr_kw):
        return "KIDS"

    # 18. DOCUMENTARY (عربي وفرنسي فقط)
    doc_keywords = ["documentary", "وثائقي", "وثائقية", "nat geo", "national geo", "discovery", "history", "animal planet", "ushuaia", "histoire", "science", "alwathiqia"]
    if any(kw in full_text for kw in doc_keywords):
        foreign_doc_tags = ["al:", "pt:", "nl:", "il:", "so:", "no:", "se:", "de:", "uk:", "es:", "it:", "tr:", "ru:", "pl:", "bg:", "cz:", "hu:", "ro:", "dk:", "us:"]
        if not any(foreign in full_text for foreign in foreign_doc_tags):
            return "DOCUMENTARY"

    # 19. ALGERIA
    algeria_keywords = [
        "algeria", "algerie", "algérie", "algerien", "entv", "الجزائر", "الجزائرية", 
        "الهداف", "el heddaf", "el bilad", "البلاد", "الشروق", "echorouk", "النهار", 
        "ennahar", "samira", "سميرة", "numidia", "نوميديا", "الوطنية", "el watania", "al24", "dz -", "alg:"
    ]
    if any(kw in full_text for kw in algeria_keywords):
        return "ALGERIA"

    # 20. FRENCH (المجموعة الأخيرة)
    french_tags = ["france", "فرنسا", "fr:", "fr ", "(fr)", "[fr]", "fr|", "fr |", "fr-", "fr_", "french"]
    french_kw = [
        "tf1", "m6", "canal+", "canal", "rmc", "eurosport", "lequipe", "l'equipe", 
        "ocs", "cine", "ciné", "w9", "tmc", "tfx", "gulli", "tiji", "france 2", 
        "france 3", "france 4", "france 5", "france 24", "bfm", "planete", "animaux"
    ]
    if any(tag in full_text for tag in french_tags) or any(kw in full_text for kw in french_kw):
        return "FRENCH"

    # 🚫 استبعاد ومنع أي قناة أخرى لا تنتمي للـ 21 مجموعة المحددة حصراً!
    return None

PREFERRED_ORDER_S1 = [
    "BEIN SPORT AR", 
    "BEIN TOD", 
    "BEIN SPORT FR", 
    "BEIN MEDIA", 
    "ALWAN SPORT", 
    "AL FAJER", 
    "KIDS", 
    "ALGERIA", 
    "ARABIC NEWS", 
    "ALWAN MOVIES", 
    "ROTANA", 
    "MBC GROUP", 
    "BOX OFFICE", 
    "NETFLIX", 
    "AMAZON PRIME", 
    "HBO", 
    "SHOWTIME", 
    "HOME CINEMA", 
    "MH GROUP", 
    "DOCUMENTARY",
    "FRENCH"             # الباقة الأخيرة
]

def process_m3u_s1(m3u_text):
    grouped_channels = defaultdict(list)
    total_count = 0
    seen_urls = set()

    lines = m3u_text.splitlines()
    current_extinf = ""

    for line in lines:
        line_str = line.strip()
        if line_str.startswith("#EXTINF:"):
            current_extinf = line_str
        elif line_str.startswith("http://") or line_str.startswith("https://"):
            if current_extinf:
                parts = current_extinf.split(",")
                channel_name = parts[-1].strip() if len(parts) > 1 else "Channel"

                orig_group = ""
                if 'group-title="' in current_extinf:
                    orig_group = current_extinf.split('group-title="')[1].split('"')[0]

                group_title = classify_channel_s1(channel_name, orig_group)
                if group_title:
                    logo = ""
                    if 'tvg-logo="' in current_extinf:
                        logo = current_extinf.split('tvg-logo="')[1].split('"')[0]

                    final_url = line_str.replace(".m3u8", ".ts")

                    if final_url in seen_urls:
                        continue

                    entry = f'#EXTINF:-1 tvg-logo="{logo}" group-title="{group_title}",{channel_name}\n{final_url}'
                    grouped_channels[group_title].append(entry)
                    seen_urls.add(final_url)
                    total_count += 1
                current_extinf = ""

    m3u_lines = ["#EXTM3U"]
    for group in PREFERRED_ORDER_S1:
        if group in grouped_channels and grouped_channels[group]:
            m3u_lines.extend(grouped_channels[group])

    return "\n".join(m3u_lines), total_count


# ==============================================================================
# SECTION C: جلب ومعالجة المصدرين بشكل منفصل ومستقل
# ==============================================================================
def fetch_and_process_app2(session):
    target_url = APP2_M3U_URL.replace("output=m3u8", "output=ts")
    headers = {"User-Agent": "okhttp/3.9.1"}

    print("\n🚀 [المسار الأول]: جاري جلب قنوات التطبيق القديم (APP2) لصفحة kz.m3u بالسكربت الأصلي...")
    try:
        response = session.get(target_url, headers=headers, timeout=20)
        if response.status_code == 200 and "#EXTM3U" in response.text:
            return process_m3u_kz(response.text)
        else:
            print("❌ فشل استجابة سيرفر APP2 القديم.")
    except Exception as e:
        print(f"❌ خطأ شبكة أثناء جلب APP2: {e}")

    return None, 0

def fetch_and_process_wanplus(session):
    print(f"\n🚀 [المسار الثاني]: جاري الاتصال بالـ API لتفعيل التطبيق الجديد (وان+) بـ التصفية الصارمة لـ s1.m3u...")
    api_params = {"code": ACTIVATION_CODE}
    api_headers = {
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 12; Build/SQ3A.220705.004)",
        "Accept": "application/json"
    }

    try:
        api_resp = session.get(WANPLUS_API_ENDPOINT, params=api_params, headers=api_headers, timeout=15)
        if api_resp.status_code == 200:
            json_data = api_resp.json()
            m3u_url = json_data.get("m3u_url")

            if json_data.get("status") and m3u_url:
                print(f"✅ تم الحصول على رابط تفعيل وان+ بنجاح: {m3u_url}")
                
                target_m3u_url = m3u_url.replace("output=m3u8", "output=ts")
                if "output=ts" not in target_m3u_url:
                    target_m3u_url += "&output=ts"

                m3u_headers = {"User-Agent": "okhttp/4.9.0"}
                m3u_resp = session.get(target_m3u_url, headers=m3u_headers, timeout=30)

                if m3u_resp.status_code == 200 and "#EXTM3U" in m3u_resp.text:
                    return process_m3u_s1(m3u_resp.text)
                else:
                    print("❌ فشل تحميل محتوى M3U للتطبيق الجديد (وان+).")
            else:
                msg = json_data.get("mensagem") or "كود التفعيل غير صحيح أو منتهي."
                print(f"⚠️ استجابة الـ API للتطبيق الجديد: {msg}")
        else:
            print(f"❌ فشل الاتصال بسيرفر API الخاص بـ وان+. كود الحالة: {api_resp.status_code}")
    except Exception as e:
        print(f"❌ خطأ غير متوقع أثناء الاتصال بتطبيق وان+: {e}")

    return None, 0

# ==============================================================================
# SECTION D: تحديث صفحة Gist على GitHub
# ==============================================================================
def update_specific_gist(session, gist_id, page_label, content, total_count):
    if not GITHUB_TOKEN:
        print("❌ خطأ: لم يتم العثور على GIST_TOKEN في متغيرات البيئة!")
        return

    if not content or total_count == 0:
        print(f"\n🛡️ [درع الحماية]: تم إلغاء تحديث الصفحة ({page_label}) لمنع المسح بسبب عدم توفر القنوات.")
        return

    print(f"\n🔐 جاري تحديث صفحة ({page_label}) على GitHub - [Gist: {gist_id}]...")
    gist_api_url = f"https://api.github.com/gists/{gist_id}"
    gist_headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    try:
        get_gist = session.get(gist_api_url, headers=gist_headers, timeout=15)
        if get_gist.status_code == 200:
            filename = list(get_gist.json()['files'].keys())[0]

            update_payload = {
                "files": {
                    filename: {
                        "content": content
                    }
                }
            }

            patch_resp = session.patch(gist_api_url, headers=gist_headers, json=update_payload)
            if patch_resp.status_code == 200:
                print(f"🎉 تم تحديث صفحة ({page_label} - {filename}) بنجاح بحجم خفيف ومصفى بـ ({total_count}) قناة فقط!")
            else:
                print(f"❌ فشل تحديث الـ Gist [{gist_id}]. كود الحالة: {patch_resp.status_code}")
        else:
            print(f"❌ فشل الوصول إلى Gist API لـ [{gist_id}]. كود الحالة: {get_gist.status_code}")
    except Exception as e:
        print(f"❌ خطأ شبكة أثناء تحديث الـ Gist [{gist_id}]: {e}")

# ==============================================================================
# SECTION E: التنفيذ الرئيسي
# ==============================================================================
def main():
    session = create_session()

    # 1. تنفيذ المسار الأول (APP2 القديم -> تحديث kz.m3u بالسكربت الأصلي دون مساس)
    kz_content, kz_count = fetch_and_process_app2(session)
    update_specific_gist(session, GIST_KZ_ID, "kz.m3u", kz_content, kz_count)

    # 2. تنفيذ المسار الثاني (Wan+ الجديد -> تحديث s1.m3u بالتصفية الصارمة)
    s1_content, s1_count = fetch_and_process_wanplus(session)
    update_specific_gist(session, GIST_S1_ID, "s1.m3u", s1_content, s1_count)

    print("\n✨ تم الانتهاء من تنفيذ السكربت الموحد بنجاح تام لجميع الصفحات!")

if __name__ == "__main__":
    main()
