import os
import requests
import re
from collections import defaultdict
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

# 1. جلب متغيرات البيئة ومرونة تحديث أكثر من صفحة Gist في نفس الوقت
GITHUB_TOKEN = os.environ.get("GIST_TOKEN")

TARGET_GIST_IDS = []
for env_key in ["GIST_ID", "GIST_ID_1", "GIST_ID_2", "GIST_ID_NEW"]:
    gist_val = os.environ.get(env_key)
    if gist_val and gist_val not in TARGET_GIST_IDS:
        TARGET_GIST_IDS.append(gist_val)

if not TARGET_GIST_IDS:
    TARGET_GIST_IDS = [
        "9c22160f66145ec833f3df816ed80239",
        "2b7f88f1e20b990504349ccd761b4de3"
    ]

APP2_M3U_URL = os.environ.get(
    "APP2_M3U_URL",
    "http://185.191.126.127:8080/get.php?username=b0:99:d7:15:88:50&password=3090914536649669&type=m3u_plus&output=ts"
)

# 2. إنشاء جلسة اتصال مستقرة
def create_session():
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries, pool_connections=30, pool_maxsize=30)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

# 3. قائمة التصفية لاستبعاد الدول والقنوات غير المرغوبة
EXCLUDE_TAGS = [
    "vip de", "vip uk", "vip ru", "vip bg", "vip pl", "vip es", "vip tr", "vip ph", "vip it", "vip br", "vip us", "vip dk", "vip hu", "vip ro",
    "de:", "uk:", "ru:", "bg:", "pl:", "es:", "ca:", "tr:", "ph:", "au:", "cz:", "usa:", "it:", "br:", "hu:", "us:", "ro:", "dk:", "usa)",
    " de ", " uk ", " ru ", " bg ", " pl ", " es ", " ca ", " tr ", " ph ", " au ", " cz ", " usa ", " it ", " br ", " hu ", " us ", " ro ", " dk ",
    "[de]", "[uk]", "[ru]", "[bg]", "[pl]", "[es]", "[ca]", "[tr]", "[ph]", "[au]", "[cz]", "[usa]", "[it]", "[br]", "[hu]", "[us]", "[ro]", "[dk]",
    "(de)", "(uk)", "(ru)", "(bg)", "(pl)", "(es)", "(ca)", "(tr)", "(ph)", "(au)", "(cz)", "(usa)", "(it)", "(br)", "(hu)", "(us)", ".ro)", "(dk)"
]

# 4. دالة التصنيف والفرز المعدلة والمصفاة بدقة
def classify_channel(channel_name):
    name_lower = channel_name.lower().strip()
    
    # استبعاد التاجات والكلمات المستبعدة
    if any(tag in name_lower for tag in EXCLUDE_TAGS):
        return None

    # 🛠️ [شرط خاص]: استبعاد القنوات التي تبدأ بـ usa أو تحتوي على usa h
    if name_lower.startswith("usa") or "usa h" in name_lower:
        return None

    # 🛠️ [تعديل 1]: إضافة باقة تود (BEIN TOD)
    if "tod" in name_lower:
        return "BEIN TOD"

    # 🛠️ [تعديل 2]: تصفية ودقة باقة بيين سبورت (beIN Sports)
    if "bein" in name_lower:
        # قنوات بيين الفرنسية
        if any(kw in name_lower for kw in ["fr", "france", "french", "فرنسية", "فرنسيه"]):
            if "bein sport" in name_lower or "bein sports" in name_lower:
                return "BEIN SPORT FR"
            return "FRENCH"

        # قنوات بيين الترفيهية والإعلامية
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

        # تشترط بيين سبورت العربية وجود عبارة "bein sport" أو "bein sports" صراحةً
        if "bein sport" in name_lower or "bein sports" in name_lower:
            return "BEIN SPORT AR"
            
        # استبعاد أي قناة تحتوي على bein فقط بدون sport ولا تتبع الميديا
        return None

    # 🛠️ [تعديل 3]: باقة القنوات الفرنسية (FRENCH)
    french_tags = ["fr:", "fr ", "(fr)", "[fr]", "france"]
    french_kw = [
        "tf1", "m6", "canal+", "canal", "rmc", "eurosport", "lequipe", "l'equipe", 
        "ocs", "cine", "ciné", "w9", "tmc", "tfx", "gulli", "tiji", "france 2", 
        "france 3", "france 4", "france 5", "france 24", "bfm"
    ]
    if any(tag in name_lower for tag in french_tags) or any(kw in name_lower for kw in french_kw):
        return "FRENCH"

    # بقية الباقات والأقسام
    if any(kw in name_lower for kw in ["alwan sport", "alwan sports", "الوان سبورت", "ألوان سبورت", "الوان الرياضية", "ألوان الرياضية"]):
        return "ALWAN SPORT"

    if "fajer" in name_lower or "الفجر" in name_lower:
        return "AL FAJER"

    kids_keywords = [
        "tom and jerry", "tom & jerry", "توم وجيري", "توم وجري", "masha", "ماشا", 
        "dora", "دورا", "spacetoon", "سبيستون", "سبيس تون", "wanasat", "وناسة", 
        "baraem", "براعم", "cn arabia", "cartoon network", "كرتون نتورك", "jeem", 
        "تلفزيون جيم", "قناة جيم", "gulli", "tiji", "disney kids", "nickelodeon", "اطفال", "أطفال"
    ]
    if any(kw in name_lower for kw in kids_keywords):
        return "KIDS"

    algeria_keywords = [
        "algeria", "algerie", "algérie", "algerien", "entv", "الجزائر", "الجزائرية", 
        "الهداف", "el heddaf", "el bilad", "البلاد", "الشروق", "echorouk", "النهار", 
        "ennahar", "samira", "سميرة", "numidia", "نوميديا", "الوطنية", "el watania", "al24"
    ]
    if any(kw in name_lower for kw in algeria_keywords):
        return "ALGERIA"

    news_keywords = ["al jazeera", "الجزيرة", "al arabiya", "العربية", "الحدث", "sky news", "سكاي نيوز", "bbc arabic", "فرانس 24", "france 24", "اخبار", "إخبارية", "اخبارية"]
    if any(kw in name_lower for kw in news_keywords):
        return "ARABIC NEWS"

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

    doc_keywords = ["nat geo", "national geo", "discovery", "documentary", "الوثائقية", "وثائقية", "ushuaia", "histoire", "science"]
    if any(kw in name_lower for kw in doc_keywords):
        return "DOCUMENTARY"

    return None

# 5. جلب وتنقية القنوات مع التعديلات الحصرية لـ s1.m3u
def fetch_and_process_app2(session):
    grouped_channels = defaultdict(list)
    total_count = 0
    seen_urls = set()

    target_url = APP2_M3U_URL.replace("output=m3u8", "output=ts")
    headers = {"User-Agent": "okhttp/3.9.1"}

    print("🚀 جاري جلب القنوات وتنبيتها بدقة...")
    try:
        response = session.get(target_url, headers=headers, timeout=20)
        if response.status_code == 200 and "#EXTM3U" in response.text:
            lines = response.text.splitlines()
            current_extinf = ""

            for line in lines:
                line_str = line.strip()
                if line_str.startswith("#EXTINF:"):
                    current_extinf = line_str
                elif line_str.startswith("http://") or line_str.startswith("https://"):
                    if current_extinf:
                        parts = current_extinf.split(",")
                        channel_name = parts[-1].strip() if len(parts) > 1 else "Channel"

                        group_title = classify_channel(channel_name)
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

            print(f"🎯 تم استخراج وتصنيف ({total_count}) قناة بنجاح.")
    except Exception as e:
        print(f"❌ خطأ شبكة أثناء جلب القنوات: {e}")

    return grouped_channels, total_count

# 6. تحديث كافـة صفحات الـ Gist المحددة
def update_gist(session, gist_id, final_m3u_content):
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
                        "content": final_m3u_content
                    }
                }
            }

            patch_resp = session.patch(gist_api_url, headers=gist_headers, json=update_payload)
            if patch_resp.status_code == 200:
                print(f"🎉 تم تحديث الصفحة ({filename}) للـ Gist [{gist_id}] بنجاح!")
            else:
                print(f"❌ فشل تحديث الـ Gist [{gist_id}]. كود الحالة: {patch_resp.status_code}")
        else:
            print(f"❌ فشل الوصول إلى Gist API لـ [{gist_id}]. كود الحالة: {get_gist.status_code}")
    except Exception as e:
        print(f"❌ خطأ غير متوقع أثناء التحديث لـ [{gist_id}]: {e}")

# 7. التنفيذ الرئيسي للترتيب والباقات
def main():
    if not GITHUB_TOKEN:
        print("❌ خطأ: لم يتم العثور على GIST_TOKEN في متغيرات البيئة!")
        return

    session = create_session()
    grouped_channels, total_count = fetch_and_process_app2(session)

    if total_count == 0:
        print("\n🛡️ [درع الحماية]: لم يتم استخراج أي قنوات جديدة أو السيرفر غير متوفر حالياً.")
        print("🛡️ تم إلغاء العملية للحفاظ على الصفحة الحالية بدون مسح.")
        return

    # 🛠️ [ترتيب الباقات المحدث]: TOD مباشرة تحت BEIN SPORT AR والقنوات الفرنسية مضمنة بوضوح
    preferred_order = [
        "BEIN SPORT AR", 
        "BEIN TOD",          # باقة تود مباشرة تحت بيين سبورت
        "BEIN SPORT FR", 
        "BEIN MEDIA", 
        "FRENCH",            # باقة القنوات الفرنسية
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
        "DOCUMENTARY"
    ]

    m3u_lines = ["#EXTM3U"]
    for group in preferred_order:
        if group in grouped_channels and grouped_channels[group]:
            m3u_lines.extend(grouped_channels[group])

    final_m3u_content = "\n".join(m3u_lines)

    print("\n🔐 جاري بدء تحديث كافـة صفحات الـ Gist...")
    for gist_id in TARGET_GIST_IDS:
        update_gist(session, gist_id, final_m3u_content)

if __name__ == "__main__":
    main()
