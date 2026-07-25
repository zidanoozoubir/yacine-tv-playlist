import os
import requests
from collections import defaultdict
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

# 1. جلب متغيرات البيئة الآمنة من GitHub Secrets
GITHUB_TOKEN = os.environ.get("GIST_TOKEN")
GIST_ID_1 = os.environ.get("GIST_ID_1") or os.environ.get("GIST_ID")  # الصفحة الأولى (kz.m3u - الباشا)
GIST_ID_2 = os.environ.get("GIST_ID_2") or os.environ.get("GIST_ID_NEW")  # الصفحة الثانية (s1.m3u - التطبيق الثاني)

# رابط مصدر التطبيق الثاني (تلقائي أو مخصص عبر secrets)
APP2_M3U_URL = os.environ.get(
    "APP2_M3U_URL",
    "http://185.191.126.127:8080/get.php?username=b0:99:d7:15:88:50&password=3090914536649669&type=m3u_plus&output=ts"
)

# 2. إنشاء جلسة اتصال مستقرة ومقاومة للانقطاع والحظر
def create_session():
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

# 3. قائمة التصفية لاستبعاد الدول/القنوات غير المرغوبة
EXCLUDE_TAGS = [
    "vip de", "vip uk", "vip ru", "vip bg", "vip pl", "vip es", "vip tr", "vip ph", "vip it", "vip br", "vip us", "vip dk", "vip hu", "vip ro",
    "de:", "uk:", "ru:", "bg:", "pl:", "es:", "ca:", "tr:", "ph:", "au:", "cz:", "usa:", "it:", "br:", "hu:", "us:", "ro:", "dk:", "usa)",
    " de ", " uk ", " ru ", " bg ", " pl ", " es ", " ca ", " tr ", " ph ", " au ", " cz ", " usa ", " it ", " br ", " hu ", " us ", " ro ", " dk ",
    "[de]", "[uk]", "[ru]", "[bg]", "[pl]", "[es]", "[ca]", "[tr]", "[ph]", "[au]", "[cz]", "[usa]", "[it]", "[br]", "[hu]", "[us]", "[ro]", "[dk]",
    "(de)", "(uk)", "(ru)", "(bg)", "(pl)", "(es)", "(ca)", "(tr)", "(ph)", "(au)", "(cz)", "(usa)", "(it)", "(br)", "(hu)", "(us)", "(ro)", "(dk)"
]

# 4. دالة الفرز والتصنيف الدقيق الشاملة والمحدثة لكلتا الصفحتين
def classify_channel(channel_name):
    name_lower = channel_name.lower()
    
    # استبعاد الواسمات الأجنبية غير المطلوبة
    if any(tag in name_lower for tag in EXCLUDE_TAGS):
        return None

    # 1. قنوات TOD CHANNEL
    if "tod" in name_lower:
        return "TOD CHANNEL"

    # 2. قنوات شوتايم SHOWTIME
    if any(kw in name_lower for kw in ["showtime", "show time", "شوتايم", "شو تايم"]):
        return "SHOWTIME"

    # 3. قنوات هوم سينما HOME CINEMA
    if any(kw in name_lower for kw in ["home cinema", "homecinema", "هوم سينما", "هومسينما", "home_cinema"]):
        return "HOME CINEMA"

    # 4. قنوات MH
    mh_tags = ["mh:", "mh ", "(mh)", "[mh]", "mh_", "mh-"]
    if any(tag in name_lower for tag in mh_tags) or name_lower.startswith("mh ") or name_lower == "mh":
        return "MH"

    # معالجة قنوات beIN بكل فئاتها
    if "bein" in name_lower:
        if any(kw in name_lower for kw in ["fr", "france", "french", "فرنسية", "فرنسيه"]):
            return "BEIN SPORT FR"
            
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
            
        return "BEIN SPORT AR"

    # قنوات ألوان الرياضية
    if any(kw in name_lower for kw in ["alwan sport", "alwan sports", "الوان سبورت", "ألوان سبورت", "الوان الرياضية", "ألوان الرياضية"]):
        return "ALWAN SPORT"

    # قنوات الفجر
    if "fajer" in name_lower or "الفجر" in name_lower:
        return "AL FAJER"

    # قنوات الأطفال
    kids_keywords = [
        "tom and jerry", "tom & jerry", "توم وجيري", "توم وجري", "masha", "ماشا", 
        "dora", "دورا", "spacetoon", "سبيستون", "سبيس تون", "wanasat", "وناسة", 
        "baraem", "براعم", "cn arabia", "cartoon network", "كرتون نتورك", "jeem", 
        "تلفزيون جيم", "قناة جيم", "gulli", "tiji", "disney kids", "nickelodeon", "اطفال", "أطفال"
    ]
    if any(kw in name_lower for kw in kids_keywords):
        return "KIDS"

    # قنوات الجزائر
    algeria_keywords = [
        "algeria", "algerie", "algérie", "algerien", "entv", "الجزائر", "الجزائرية", 
        "الهداف", "el heddaf", "el bilad", "البلاد", "الشروق", "echorouk", "النهار", 
        "ennahar", "samira", "سميرة", "numidia", "نوميديا", "الوطنية", "el watania", "al24"
    ]
    if any(kw in name_lower for kw in algeria_keywords):
        return "ALGERIA"

    # القنوات الإخبارية العربية
    news_keywords = ["al jazeera", "الجزيرة", "al arabiya", "العربية", "الحدث", "sky news", "سكاي نيوز", "bbc arabic", "فرانس 24", "france 24", "اخبار", "إخبارية", "اخبارية"]
    if any(kw in name_lower for kw in news_keywords):
        return "ARABIC NEWS"

    # قنوات ألوان للأفلام
    if "alwan" in name_lower or "ألوان" in name_lower or "الوان" in name_lower:
        return "ALWAN MOVIES"

    # قنوات روتانا
    if "rotana" in name_lower or "روتانا" in name_lower:
        return "ROTANA"

    # قنوات MBC
    if "mbc" in name_lower or "ام بي سي" in name_lower or "إم بي سي" in name_lower:
        return "MBC GROUP"

    # قنوات بوكس أوفيس
    if any(kw in name_lower for kw in ["box office", "boxoffice", "box-office", "بوكس أوفيس", "بوكس اوفيس"]):
        return "BOX OFFICE"

    # قنوات نتفليكس
    if "netflix" in name_lower or "نتفليكس" in name_lower or "نتفلكس" in name_lower:
        return "NETFLIX"

    # قنوات أمازون برايم
    if "amazon" in name_lower or "prime" in name_lower or "أمازون" in name_lower or "امازون" in name_lower:
        return "AMAZON PRIME"

    # قنوات HBO
    if "hbo" in name_lower:
        return "HBO"

    # قنوات وثائقية
    doc_keywords = ["nat geo", "national geo", "discovery", "documentary", "الوثائقية", "وثائقية", "ushuaia", "histoire", "science"]
    if any(kw in name_lower for kw in doc_keywords):
        return "DOCUMENTARY"

    # القنوات الفرنسية العامة
    french_tags = ["fr:", "fr ", "(fr)", "[fr]", "france"]
    french_kw = ["tf1", "m6", "canal+", "canal", "rmc", "eurosport", "lequipe", "l'equipe", "ocs", "cine", "ciné", "w9", "tmc", "tfx"]
    if any(tag in name_lower for tag in french_tags) or any(kw in name_lower for kw in french_kw):
        return "FRENCH"

    return None

# 5. [التطبيق الأول]: جلب وتنقية قنوات تطبيق الباشا (صفحة kz.m3u)
def fetch_app1_channels(session):
    api_url = "https://albashatv.site/api.php"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Connection": "Keep-Alive",
        "User-Agent": "okhttp/3.9.1"
    }
    payload = "method=o6&event=view"
    
    grouped_channels = defaultdict(list)
    seen_urls = set()
    total_count = 0

    print("📡 [تطبيق 1 - kz.m3u]: جاري الاتصال بتطبيق الباشا تيفي...")
    try:
        response = session.post(api_url, headers=headers, data=payload, timeout=20)
        if response.status_code == 200:
            channels = response.json()
            if not isinstance(channels, list):
                print("⚠️ [تطبيق 1]: استجابة السيرفر غير متوافقة.")
                return grouped_channels, 0

            for channel in channels:
                channel_name = channel.get('name', '').strip()
                raw_url = channel.get('url', '').strip()
                
                if not raw_url or raw_url in seen_urls:
                    continue
                
                group_title = classify_channel(channel_name)
                if not group_title:
                    continue
                
                basha_ua = channel.get('user_agent', '').strip()
                referer = channel.get('refrens', '').strip()
                cookie = channel.get('cookie', '').strip()
                logo = channel.get('logo', '').strip()
                
                vlc_opts = ["#EXTVLCOPT:http-header=Icy-MetaData: 1"]
                if basha_ua:
                    vlc_opts.append(f'#EXTVLCOPT:http-user-agent={basha_ua}')
                if referer:
                    vlc_opts.append(f'#EXTVLCOPT:http-referrer={referer}')
                if cookie:
                    vlc_opts.append(f'#EXTVLCOPT:http-cookie={cookie}')
                
                vlc_opts_str = "\n".join(vlc_opts)
                final_url = raw_url.strip().replace("live///", "live/").replace("live//", "live/")
                
                entry = f'#EXTINF:-1 tvg-logo="{logo}" group-title="{group_title}",{channel_name}\n'
                entry += f'{vlc_opts_str}\n'
                entry += f'{final_url}'
                
                grouped_channels[group_title].append(entry)
                seen_urls.add(raw_url)
                total_count += 1
            print(f"🎯 [تطبيق 1]: تم استخراج ({total_count}) قناة بنجاح.")
    except Exception as e:
        print(f"❌ [تطبيق 1]: خطأ أثناء جلب البيانات: {e}")
        
    return grouped_channels, total_count

# 6. [التطبيق الثاني]: جلب وتنقية قنوات التطبيق الثاني (صفحة s1.m3u)
def fetch_app2_channels(session):
    grouped_channels = defaultdict(list)
    total_count = 0
    seen_urls = set()

    # تعديل رابط الطلب ليطلب مخرجات ts بدلاً من m3u8
    target_url = APP2_M3U_URL.replace("output=m3u8", "output=ts")
    # ترويسة متصفح قياسية لجلب ملف القائمة من السيرفر
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    print("🚀 [تطبيق 2 - s1.m3u]: جاري جلب القنوات للتطبيق الثاني...")
    try:
        response = session.get(target_url, headers=headers, timeout=25)
        print(f"📡 [تطبيق 2]: كود استجابة السيرفر: {response.status_code}")

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

                            # تحويل امتداد الروابط تلقائياً إلى .ts بدلاً من .m3u8 لمنع التقطيع وخطأ 403
                            final_url = line_str.replace(".m3u8", ".ts")
                            final_url = final_url.replace("217.60.15.177:8080", "185.191.126.127:8080")

                            if final_url in seen_urls:
                                continue

                            # ترويسة تشغيل البث على المشغلات
                            vlc_opts_str = "#EXTVLCOPT:http-header=Icy-MetaData: 1\n#EXTVLCOPT:http-user-agent=okhttp/3.9.1"

                            entry = f'#EXTINF:-1 tvg-logo="{logo}" group-title="{group_title}",{channel_name}\n{vlc_opts_str}\n{final_url}'
                            grouped_channels[group_title].append(entry)
                            seen_urls.add(final_url)
                            total_count += 1
                        current_extinf = ""

            print(f"🎯 [تطبيق 2]: تم استخراج ({total_count}) قناة بنجاح.")
        else:
            print(f"⚠️ [تطبيق 2]: السيرفر لم يرجع قائمة M3U صالحة. المعاينة:\n{response.text[:150]}")
    except Exception as e:
        print(f"❌ [تطبيق 2]: خطأ شبكة أثناء جلب القنوات: {e}")

    return grouped_channels, total_count

# 7. دالة تحديث صفحة Gist المحددة
def update_gist(session, target_gist_id, grouped_channels, total_count, app_label=""):
    if total_count == 0:
        print(f"🛡️ [درع الحماية - {app_label}]: تم إلغاء التحديث للحفاظ على القنوات القديمة شغالّة بدون مسح.")
        return

    preferred_order = [
        "BEIN SPORT AR",
        "TOD CHANNEL",
        "ALWAN SPORT",
        "AL FAJER",
        "BEIN SPORT FR",
        "BEIN MEDIA",
        "SHOWTIME",
        "HOME CINEMA",
        "MH",
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
        "DOCUMENTARY",
        "FRENCH"
    ]

    m3u_lines = ["#EXTM3U"]
    for group in preferred_order:
        if group in grouped_channels and grouped_channels[group]:
            m3u_lines.extend(grouped_channels[group])

    final_m3u_content = "\n".join(m3u_lines)

    gist_api_url = f"https://api.github.com/gists/{target_gist_id}"
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
                print(f"🎉 تم تحديث ({filename}) بنجاح لـ [{app_label}]! إجمالي القنوات: ({total_count}).")
            else:
                print(f"❌ فشل تحديث الـ Gist لـ [{app_label}]. كود الحالة: {patch_resp.status_code}")
        else:
            print(f"❌ فشل الوصول لـ Gist لـ [{app_label}]. كود الحالة: {get_gist.status_code}")
    except Exception as e:
        print(f"❌ خطأ غير متوقع أثناء الاتصال بـ GitHub لـ [{app_label}]: {e}")

# 8. التنفيذ الرئيسي الشامل للطرفين
def main():
    if not GITHUB_TOKEN:
        print("❌ خطأ: لم يتم العثور على GIST_TOKEN في متغيرات البيئة!")
        return

    session = create_session()

    # --- 1. تحديث الصفحة الأولى (kz.m3u - تطبيق الباشا) ---
    if GIST_ID_1:
        channels_1, count_1 = fetch_app1_channels(session)
        update_gist(session, GIST_ID_1, channels_1, count_1, app_label="الصفحة الأولى (kz.m3u)")
    else:
        print("⚠️ لم يتم تعيين GIST_ID_1 للصفحة الأولى.")

    print("\n" + "="*50 + "\n")

    # --- 2. تحديث الصفحة الثانية (s1.m3u - التطبيق الثاني) ---
    if GIST_ID_2:
        channels_2, count_2 = fetch_app2_channels(session)
        update_gist(session, GIST_ID_2, channels_2, count_2, app_label="الصفحة الثانية (s1.m3u)")
    else:
        print("⚠️ لم يتم تعيين GIST_ID_2 للصفحة الثانية.")

if __name__ == "__main__":
    main()
