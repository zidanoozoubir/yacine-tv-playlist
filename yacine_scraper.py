import os
import requests
import re
from collections import defaultdict
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor

# ==========================================
# 1. الإعدادات ومتغيرات البيئة المعرفة
# ==========================================
GITHUB_TOKEN = os.environ.get("GIST_TOKEN")

GIST_S1_ID = os.environ.get("GIST_S1_ID") or "9c22160f66145ec833f3df816ed80239"  # صفحة s1.m3u (وان+)
GIST_KZ_ID = os.environ.get("GIST_KZ_ID") or "2b7f88f1e20b990504349ccd761b4de3"  # صفحة kz.m3u (الباشا تيفي)

# رابط API الباشا تيفي الجديد (o6)
ALBASHA_API_ENDPOINT = os.environ.get(
    "ALBASHA_API_ENDPOINT",
    "https://albashatv.site/api.php"
)

# هيدر الباشا / Lion الرسمي المشغل للسيرفرات
LION_UA = "com.shadeed.lionpro/56 (Linux; U; Android 14; ar_EG_#u-nu-arab; LLY-LX2; Build/HONORLLY-L32; Cronet/151.0.7922.83)"

# إعدادات وان+
WANPLUS_API_ENDPOINT = os.environ.get(
    "WANPLUS_API_ENDPOINT",
    "https://atared.serv00.net/lion_panel_4k_x91/api/verificar_codigo.php"
)
ACTIVATION_CODE = os.environ.get("ACTIVATION_CODE", "V1")

# ==========================================
# 2. إنشاء جلسات اتصال متخصصة (سريعة ومستقرة)
# ==========================================
def create_session():
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries, pool_connections=30, pool_maxsize=30)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def create_probe_session():
    """جلسة فائقة السرعة لفحص الروابط بدون أي إعادة محاولة أو تأخير"""
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=0, pool_connections=40, pool_maxsize=40)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

# ==========================================
# محرك المطابقة الدقيقة للكلمات المستقلة
# ==========================================
def match_exact_word(kw, text):
    pattern = r'\b' + re.escape(kw.lower()) + r'\b'
    return bool(re.search(pattern, text.lower()))

def has_word(kw_list, text):
    return any(match_exact_word(kw, text) for kw in kw_list)

def is_live_stream_only(url, title):
    u = url.lower().strip()
    t = title.lower().strip()

    if "/movie/" in u or "/series/" in u or u.endswith(".mp4") or u.endswith(".mkv") or u.endswith(".avi"):
        return False

    if re.search(r'\bs\d{1,2}\s*e\d{1,2}\b', t) or re.search(r'\bs\d{2}\b', t) or re.search(r'\be\d{2}\b', t):
        return False
    if re.search(r'\b(season|episode|part|ep)\s*\d+\b', t):
        return False

    if re.search(r'\b(tom\s*and\s*jerry|tiki|masha)\s+\d+\b', t):
        return False

    if re.search(r'[-+]\d{1,2}h\b', t) or "timeshift" in t or "time shift" in t:
        return False

    return True


# ==============================================================================
# SECTION A: تصنيف ومعالجة قنوات الباشا تيفي لصفحة kz.m3u
# ==============================================================================
EXCLUDE_TAGS_KZ = [
    "vip de", "vip uk", "vip ru", "vip bg", "vip pl", "vip es", "vip tr", "vip ph", "vip it", "vip br", "vip us", "vip dk", "vip hu", "vip ro", "vip pt", "vip nl", "vip se", "vip no",
    "de:", "uk:", "ru:", "bg:", "pl:", "es:", "ca:", "tr:", "ph:", "au:", "cz:", "usa:", "it:", "br:", "hu:", "us:", "ro:", "dk:", "usa)", "pt:", "nl:", "il:", "so:", "no:", "se:", "fi:", "gr:", "ex-yu:", "ex yu:", "sk:", "in:", "pk:", "bd:", "af:", "ir:", "he:", "sr:", "hr:", "ba:", "mk:", "si:",
    " de ", " uk ", " ru ", " bg ", " pl ", " es ", " ca ", " tr ", " ph ", " au ", " cz ", " usa ", " it ", " br ", " hu ", " us ", " ro ", " dk ", " pt ", " nl ", " il ", " so ", " no ", " se ",
    "[de]", "[uk]", "[ru]", "[bg]", "[pl]", "[es]", "[ca]", "[tr]", "[ph]", "[au]", "[cz]", "[usa]", "[it]", "[br]", "[hu]", "[us]", "[ro]", "[dk]", "[al]", "[pt]", "[nl]", "[il]", "[so]", "[no]", "[se]",
    "(de)", "(uk)", "(ru)", "(bg)", "(pl)", "(es)", "(ca)", "(tr)", "(ph)", "(au)", "(cz)", "(usa)", "(it)", "(br)", "(hu)", "(us)", "(ro)", "(dk)", "(al)", "(pt)", "(nl)", "(il)", "(so)", "(no)", "(se)"
]

def classify_channel_kz(channel_name, orig_group=""):
    full_text = f"{channel_name} {orig_group}".lower().strip()
    name_lower = channel_name.lower().strip()
    
    if any(tag in full_text for tag in EXCLUDE_TAGS_KZ):
        return None

    if name_lower.startswith("usa") or "usa h" in full_text:
        return None

    if "tod" in full_text:
        return "BEIN TOD"

    if "bein" in full_text:
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
            "junior", "news", "اخبار", "أخبار", "افلام", "أفلام"
        ]
        if any(kw in full_text for kw in bein_media_keywords):
            return "BEIN MEDIA"

        bein_sports_triggers = [
            "bein sport", "bein sports", "sport", "sports", 
            "h.265", "h265", "hevc", "4k", "hd", "sd", "english", "max", "premium", "xtra"
        ]
        if any(trigger in full_text for trigger in bein_sports_triggers) or "bein" in name_lower:
            return "BEIN SPORT AR"
            
        return None

    if any(kw in full_text for kw in ["al jazeera", "aljazeera", "الجزيرة", "al arabiya", "alarabiya", "العربية", "al hadath", "alhadath", "الحدث", "sky news", "سكاي نيوز"]) or orig_group.lower() == "news":
        if "sky" in full_text:
            if any(ar in full_text for ar in ["arabic", "arabia", "عرب", "عربية", "سكاي نيوز"]):
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
    if any(kw in full_text for kw in kids_ar_kw) or any(kw in full_text for kw in kids_fr_kw) or orig_group.lower() == "kids":
        return "KIDS"

    doc_keywords = ["nat geo", "national geo", "discovery", "documentary", "الوثائقية", "وثائقية", "ushuaia", "histoire", "science"]
    if any(kw in full_text for kw in doc_keywords) or "document" in orig_group.lower():
        foreign_doc_tags = ["pt:", "nl:", "il:", "so:", "no:", "se:", "de:", "uk:", "es:", "it:", "tr:", "ru:", "pl:", "bg:", "cz:", "hu:", "ro:", "dk:", "us:"]
        if not any(foreign in full_text for foreign in foreign_doc_tags):
            return "DOCUMENTARY"

    french_tags = ["fr:", "fr ", "(fr)", "[fr]", "france"]
    french_kw = [
        "tf1", "m6", "canal+", "canal", "rmc", "eurosport", "lequipe", "l'equipe", 
        "ocs", "cine", "ciné", "w9", "tmc", "tfx", "gulli", "tiji", "france 2", 
        "france 3", "france 4", "france 5", "france 24", "bfm"
    ]
    if any(tag in full_text for tag in french_tags) or any(kw in full_text for kw in french_kw):
        return "FRENCH"

    if any(kw in full_text for kw in ["alwan sport", "alwan sports", "الوان سبورت", "ألوان سبورت", "الوان الرياضية", "ألوان الرياضية"]):
        return "ALWAN SPORT"

    if "fajer" in full_text or "الفجر" in full_text or "alfajer" in full_text:
        return "AL FAJER"

    algeria_keywords = [
        "algeria", "algerie", "algérie", "algerien", "entv", "الجزائر", "الجزائرية", 
        "الهداف", "el heddaf", "el bilad", "البلاد", "الشروق", "echorouk", "النهار", 
        "ennahar", "samira", "سميرة", "numidia", "نوميديا", "الوطنية", "el watania", "al24"
    ]
    if any(kw in full_text for kw in algeria_keywords):
        return "ALGERIA"

    if "alwan" in full_text or "ألوان" in full_text or "الوان" in full_text:
        return "ALWAN MOVIES"

    if "rotana" in full_text or "روتانا" in full_text:
        return "ROTANA"

    if "mbc" in full_text or "ام بي سي" in full_text or "إم بي سي" in full_text or orig_group.lower() == "mbc":
        return "MBC GROUP"

    if any(kw in full_text for kw in ["box office", "boxoffice", "box-office", "بوكس أوفيس", "بوكس اوفيس", "osn"]):
        return "BOX OFFICE"

    if "netflix" in full_text or "نتفليكس" in full_text or "نتفلكس" in full_text or orig_group.lower() == "netflix":
        return "NETFLIX"

    if "amazon" in full_text or "prime" in full_text or "أمازون" in full_text or "امازون" in full_text:
        return "AMAZON PRIME"

    if "hbo" in full_text:
        return "HBO"

    if any(kw in full_text for kw in ["showtime", "شوتايم"]):
        return "SHOWTIME"

    if any(kw in full_text for kw in ["home cinema", "homecinema", "هوم سينما", "هومسينما"]):
        return "HOME CINEMA"

    if any(kw in full_text for kw in ["mh", "ام اتش", "أم اتش"]):
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

def clean_stream_url(raw_url):
    """تخطي البروكسي المعطل 109.122.18.14 واستخراج رابط البث المباشر الفعلي"""
    url = raw_url.strip()
    if "proxy?url=" in url:
        url = url.split("proxy?url=")[-1].strip()
    return url

def get_effective_ua(raw_ua):
    """تصحيح هيدر الـ User-Agent التالف أو الفارغ وإسناد هيدر Lion الرسمي"""
    ua = (raw_ua or "").strip()
    if not ua or ua.startswith("oC6") or "okhttp" in ua.lower():
        return LION_UA
    return ua

def should_resolve(url):
    """فحص ذكي: هل يحتاج هذا الرابط حقاً إلى حل التوكن والتحويل؟"""
    if not url or not url.startswith("http"):
        return False
    # الروابط التي تحوي توكن ومنفذ 2095 أو السيرفرات المباشرة لا تحتاج أي وقت
    if "?token=" in url and ":2095" in url:
        return False
    # الروابط التي تحول فقط هي التي نفحصها
    return any(domain in url.lower() for domain in ["lionmax", "megoaroma"])

def resolve_stream_url(probe_session, url, ua):
    """حل تحويلات الـ 302 في أجزاء من الثانية مع إغلاق فوري للبث المباشر لمنع التعليق"""
    if not should_resolve(url):
        return url

    curr_url = url
    for _ in range(2):
        try:
            # استخدام stream=True حاسم جداً حتى لا يقوم بايثون بتنزيل الفيديو الحي
            resp = probe_session.get(curr_url, headers={"User-Agent": ua}, allow_redirects=False, stream=True, timeout=2.0)
            loc = resp.headers.get("Location")
            resp.close()  # إغلاق الاتصال فوراً بمجرد قراءة الهيدر!
            if loc:
                curr_url = urljoin(curr_url, loc.strip())
                continue
            break
        except Exception:
            break
    return curr_url

def process_json_kz(channels_list):
    candidates = []
    seen_urls = set()

    # 1. جمع القنوات وتصفيتها بسرعة
    for item in channels_list:
        if not isinstance(item, dict):
            continue

        channel_name = item.get("name", "").strip()
        orig_group = item.get("group_title", "").strip()
        raw_url = item.get("url", "").strip()
        logo = item.get("logo", "").strip()
        item_ua = item.get("user_agent", "").strip()
        item_ref = item.get("refrens", "").strip()

        if not raw_url or not channel_name:
            continue

        final_url = clean_stream_url(raw_url)
        if not final_url or final_url in seen_urls:
            continue

        group_title = classify_channel_kz(channel_name, orig_group)
        if not group_title:
            continue

        ua = get_effective_ua(item_ua)
        candidates.append({
            "name": channel_name,
            "group": group_title,
            "url": final_url,
            "logo": logo,
            "ua": ua,
            "ref": item_ref
        })
        seen_urls.add(final_url)

    # 2. حل روابط التوكن للموزعات فقط (خلال ثانية واحدة بالتوازي)
    print(f"⚡ جاري فحص وحل روابط ({len(candidates)}) قناة بسرعة فائقة...")
    probe_session = create_probe_session()

    def resolve_candidate(cand):
        cand["resolved_url"] = resolve_stream_url(probe_session, cand["url"], cand["ua"])
        return cand

    with ThreadPoolExecutor(max_workers=25) as executor:
        resolved_candidates = list(executor.map(resolve_candidate, candidates))

    # 3. بناء ملف M3U
    grouped_channels = defaultdict(list)
    total_count = 0

    for item in resolved_candidates:
        group_title = item["group"]
        channel_name = item["name"]
        final_url = item["resolved_url"]
        logo = item["logo"]
        ua = item["ua"]
        ref = item["ref"]

        vlc_opts = [
            "#EXTVLCOPT:http-header=Icy-MetaData: 1",
            f"#EXTVLCOPT:http-user-agent={ua}"
        ]
        if ref:
            vlc_opts.append(f"#EXTVLCOPT:http-referrer={ref}")

        vlc_opts_str = "\n".join(vlc_opts)
        ref_attr = f' http-referrer="{ref}"' if ref else ''

        entry = (
            f'#EXTINF:-1 tvg-logo="{logo}" group-title="{group_title}" '
            f'http-user-agent="{ua}" user-agent="{ua}"{ref_attr},{channel_name}\n'
            f'{vlc_opts_str}\n'
            f'{final_url}'
        )
        grouped_channels[group_title].append(entry)
        total_count += 1

    m3u_lines = ["#EXTM3U"]
    for group in PREFERRED_ORDER_KZ:
        if group in grouped_channels and grouped_channels[group]:
            m3u_lines.extend(grouped_channels[group])

    return "\n".join(m3u_lines), total_count


# ==============================================================================
# SECTION B: كود التصفية الصارمة الدقيقة المخصص لصفحة s1.m3u (وان+)
# ==============================================================================
EXCLUDE_TAGS_S1 = [
    "vip de", "vip uk", "vip ru", "vip bg", "vip pl", "vip es", "vip tr", "vip ph", "vip it", "vip br", "vip us", "vip dk", "vip hu", "vip ro", "vip pt", "vip nl", "vip se", "vip no", "vip al",
    "de:", "uk:", "ru:", "bg:", "pl:", "es:", "ca:", "tr:", "ph:", "au:", "cz:", "usa:", "it:", "br:", "hu:", "us:", "ro:", "dk:", "usa)", "pt:", "nl:", "il:", "so:", "no:", "se:", "fi:", "gr:", "ex-yu:", "ex yu:", "sk:", "in:", "pk:", "bd:", "af:", "ir:", "he:", "sr:", "hr:", "ba:", "mk:", "si:",
    " de ", " uk ", " ru ", " bg ", " pl ", " es ", " ca ", " tr ", " ph ", " au ", " cz ", " usa ", " it ", " br ", " hu ", " us ", " ro ", " dk ", " pt ", " nl ", " il ", " so ", " no ", " se ",
    "[de]", "[uk]", "[ru]", "[bg]", "[pl]", "[es]", "[ca]", "[tr]", "[ph]", "[au]", "[cz]", "[usa]", "[it]", "[br]", "[hu]", "[us]", "[ro]", "[dk]", "[al]", "[pt]", "[nl]", "[il]", "[so]", "[no]", "[se]",
    "(de)", "(uk)", "(ru)", "(bg)", "(pl)", "(es)", "(ca)", "(tr)", "(ph)", "(au)", "(cz)", "(usa)", "(it)", "(br)", "(hu)", "(us)", "(ro)", "(dk)", "(al)", "(pt)", "(nl)", "(il)", "(so)", "(no)", "(se)",
    "china", "christian", "cine mania india", "cine mania usa", "cric life", "cricket", "denmark", "ethiopia", "finland", "germany", "greece", "india", "malaysia", "nepal", "pakistan", "poland", "portugal", "romania", "russia", "thailand", "turkey", "vietnam"
]

def classify_channel_s1(channel_name, orig_group="", stream_url=""):
    full_text = f"{channel_name} {orig_group}".lower().strip()
    name_lower = channel_name.lower().strip()
    
    clean_text = re.sub(r'[\s:_\-\|/\[\]\(\)]+', '', full_text)

    if not is_live_stream_only(stream_url, channel_name):
        return None

    if any(tag in full_text for tag in EXCLUDE_TAGS_S1):
        return None

    if name_lower.startswith("usa") or "usa h" in full_text:
        return None

    if has_word(["tod", "تود"], full_text) and "today" not in full_text:
        return "BEIN TOD"

    if has_word(["bein", "بي ان", "بي إن"], full_text):
        if has_word(["fr", "france", "french", "فرنسية", "فرنسيه"], full_text):
            if has_word(["sport", "sports", "h.265", "h265", "hevc"], full_text):
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
        if has_word(bein_media_keywords, full_text):
            return "BEIN MEDIA"

        bein_sports_triggers = ["sport", "sports", "h.265", "h265", "hevc", "4k", "hd", "sd"]
        if has_word(bein_sports_triggers, full_text):
            return "BEIN SPORT AR"

    if has_word(["alwan sport", "alwan sports", "الوان سبورت", "ألوان سبورت", "الوان الرياضية", "ألوان الرياضية"], full_text):
        return "ALWAN SPORT"

    if "alfajer" in clean_text or "alfajr" in clean_text or "fadjrsports" in clean_text or "fajersports" in clean_text or has_word(["fajer", "alfajer", "fadjr", "fajr", "الفجر", "فجر"], full_text):
        if not any(alg in full_text for alg in ["alg", "dz", "algeria", "الجزائر", "الجزائرية"]):
            return "AL FAJER"

    alwan_movies_kw = ["alwan movie", "alwan movies", "alwan cinema", "alwan film", "alwan aflam", "ألوان أفلام", "الوان افلام", "ألوان سينما", "الوان سينما"]
    if has_word(alwan_movies_kw, full_text):
        return "ALWAN MOVIES"

    if has_word(["mbc", "m b c", "ام بي سي", "إم بي سي", "mpc"], full_text):
        return "MBC GROUP"

    if has_word(["rotana", "روتانا"], full_text):
        return "ROTANA"

    if has_word(["hbo", "h b o", "اتش بي او", "اتش بي أوا"], full_text):
        return "HBO"

    if has_word(["osn", "o s n", "او اس ان", "أو إس إن", "box office", "boxoffice", "art", "ارتي", "أرتي"], full_text):
        return "BOX OFFICE"

    if has_word(["netflix", "نتفليكس", "نتفلكس", "shahid", "شاهد"], full_text) or "net |" in full_text:
        return "NETFLIX"

    if has_word(["amazon", "prime", "أمازون", "امازون"], full_text):
        return "AMAZON PRIME"

    if has_word(["showtime", "شوتايم"], full_text):
        return "SHOWTIME"

    if has_word(["home cinema", "homecinema", "هوم سينما"], full_text):
        return "HOME CINEMA"

    if has_word(["mh", "ام اتش", "أم اتش"], full_text):
        return "MH GROUP"

    kids_strict_kw = [
        "tom and jerry", "tom & jerry", "توم وجيري", "توم وجري",
        "masha", "ماشا", "دب",
        "spacetoon", "سبيستون", "سبيس تون",
        "baraem", "براعم",
        "cartoon network", "cn arabia", "كرتون نتورك"
    ]
    if has_word(kids_strict_kw, full_text):
        if "yemen" not in full_text and "اليمن" not in full_text:
            if "en" not in full_text and "english" not in full_text:
                return "KIDS"

    exact_doc_triggers = [
        "nat geo wild", "national geo wild", "ad nat geo", "الجزيرة الوثائقية", "al jazeera documentary",
        "aljazeera documentary", "وثائقية", "وثائقي", "alwathiqia", "alwathafeqia", "discovery",
        "asharq", "الشرق", "yemen documentary", "اليمن الوثائقية", "osn documentary", "netflix documentary",
        "ushuaia", "أوشوايا", "animal planet", "anemal planet", "animaux", "nature", "natura"
    ]
    if any(trigger in full_text for trigger in exact_doc_triggers):
        doc_exclude_words = [
            "doku", "bg", "cz", "allente", "in-tm", "movistar",
            "al:", "pt:", "nl:", "il:", "so:", "no:", "se:", "de:", "uk:", "es:", "it:", "tr:", "ru:", "pl:", "bg:", "cz:", "hu:", "ro:", "dk:", "us:"
        ]
        if not any(ex in full_text for ex in doc_exclude_words):
            return "DOCUMENTARY"

    algeria_keywords = [
        "algeria", "algerie", "algérie", "algerien", "entv", "الجزائر", "الجزائرية", 
        "الهداف", "el heddaf", "el bilad", "البلاد", "الشروق", "echorouk", "النهار", 
        "ennahar", "samira", "سميرة", "numidia", "نوميديا", "الوطنية", "el watania", "al24", "dz -", "alg:"
    ]
    if has_word(algeria_keywords, full_text):
        return "ALGERIA"

    french_tags = ["france", "فرنسا", "fr:", "fr ", "(fr)", "[fr]", "fr|", "fr |", "fr-", "fr_", "french"]
    french_kw = [
        "tf1", "m6", "canal+", "canal", "rmc", "eurosport", "lequipe", "l'equipe", 
        "ocs", "cine", "ciné", "w9", "tmc", "tfx", "gulli", "tiji", "france 2", 
        "france 3", "france 4", "france 5", "france 24", "bfm", "planete", "animaux"
    ]
    if any(tag in full_text for tag in french_tags) or has_word(french_kw, full_text):
        return "FRENCH"

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

                final_url = line_str.replace(".m3u8", ".ts")

                group_title = classify_channel_s1(channel_name, orig_group, final_url)
                if group_title:
                    logo = ""
                    if 'tvg-logo="' in current_extinf:
                        logo = current_extinf.split('tvg-logo="')[1].split('"')[0]

                    if final_url in seen_urls:
                        continue

                    entry = f'#EXTINF:-1 tvg-logo="{logo}" group-title="{group_title}",{channel_name}\n{final_url}'
                    grouped_channels[group_title].append(entry)
                    seen_urls.add(final_url)
                    total_count += 1
                current_extinf = ""

    if "KIDS" in grouped_channels:
        grouped_channels["KIDS"] = grouped_channels["KIDS"][:4]

    m3u_lines = ["#EXTM3U"]
    for group in PREFERRED_ORDER_S1:
        if group in grouped_channels and grouped_channels[group]:
            m3u_lines.extend(grouped_channels[group])

    return "\n".join(m3u_lines), total_count


# ==============================================================================
# SECTION C: جلب ومعالجة المصدرين بشكل منفصل ومستقل
# ==============================================================================
def fetch_and_process_albasha(session):
    headers = {
        "User-Agent": "okhttp/3.9.1",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    payload = {
        "method": "o6",
        "event": "view"
    }

    print("\n🚀 [المسار الأول]: جاري الاتصال بـ API الباشا تيفي الجديد (o6) لصفحة kz.m3u...")
    try:
        response = session.post(ALBASHA_API_ENDPOINT, data=payload, headers=headers, timeout=20)
        if response.status_code == 200:
            try:
                channels_data = response.json()
                if isinstance(channels_data, list) and len(channels_data) > 0:
                    print(f"✅ تم استلام مصفوفة القنوات بنجاح ({len(channels_data)} عنصر).")
                    return process_json_kz(channels_data)
                else:
                    print("⚠️ استجابة API الباشا لم ترجع مصفوفة قنوات صحيحة.")
            except Exception as je:
                print(f"❌ خطأ أثناء قراءة JSON لسيرفر الباشا: {je}")
        else:
            print(f"❌ فشل الاتصال بسيرفر الباشا API. كود الحالة: {response.status_code}")
    except Exception as e:
        print(f"❌ خطأ شبكة أثناء جلب الباشا تيفي: {e}")

    return None, 0

def fetch_and_process_wanplus(session):
    print(f"\n🚀 [المسار الثاني]: جاري الاتصال بالـ API لتفعيل التطبيق الجديد (وان+) لصفحة s1.m3u ومجموعاتها الشاملة...")
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

    # 1. تنفيذ المسار الأول (الباشا تيفي API الجديد -> تحديث kz.m3u)
    kz_content, kz_count = fetch_and_process_albasha(session)
    update_specific_gist(session, GIST_KZ_ID, "kz.m3u", kz_content, kz_count)

    # 2. تنفيذ المسار الثاني (Wan+ الجديد -> تحديث s1.m3u)
    s1_content, s1_count = fetch_and_process_wanplus(session)
    update_specific_gist(session, GIST_S1_ID, "s1.m3u", s1_content, s1_count)

    print("\n✨ تم الانتهاء من تنفيذ السكربت الموحد بنجاح تام لجميع الصفحات!")

if __name__ == "__main__":
    main()
