import os
import requests
from collections import defaultdict
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

# 1. جلب متغيرات البيئة الآمنة من GitHub Secrets
GITHUB_TOKEN = os.environ.get("GIST_TOKEN")
GIST_ID_1 = os.environ.get("GIST_ID_1") or os.environ.get("GIST_ID")  # الصفحة الأولى (kz.m3u - الباشا)
GIST_ID_2 = os.environ.get("GIST_ID_2") or os.environ.get("GIST_ID_NEW")  # الصفحة الثانية (s1.m3u - التطبيق الثاني)

# معالجة رابط التطبيق الثاني
env_app2_url = os.environ.get("APP2_M3U_URL")
if env_app2_url and env_app2_url.strip():
    APP2_M3U_URL = env_app2_url.strip()
else:
    APP2_M3U_URL = "http://185.191.126.127:8080/get.php?username=b0:99:d7:15:88:50&password=3090914536649669&type=m3u_plus&output=ts"

# 2. إنشاء جلسة اتصال مستقرة ومقاومة للانقطاع والحظر
def create_session():
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

# 3. قائمة التصفية لاستبعاد الدول/القنوات غير المرغوبة (تطبق فقط على القنوات التي لا تنتمي للمجموعات الـ 21)
EXCLUDE_TAGS = [
    "vip de", "vip uk", "vip ru", "vip bg", "vip pl", "vip es", "vip tr", "vip ph", "vip it", "vip br", "vip us", "vip dk", "vip hu", "vip ro",
    "de:", "uk:", "ru:", "bg:", "pl:", "es:", "ca:", "tr:", "ph:", "au:", "cz:", "usa:", "it:", "br:", "hu:", "us:", "ro:", "dk:", "usa)",
    " de ", " uk ", " ru ", " bg ", " pl ", " es ", " ca ", " tr ", " ph ", " au ", " cz ", " usa ", " it ", " br ", " hu ", " us ", " ro ", " dk ",
    "[de]", "[uk]", "[ru]", "[bg]", "[pl]", "[es]", "[ca]", "[tr]", "[ph]", "[au]", "[cz]", "[usa]", "[it]", "[br]", "[hu]", "[us]", "[ro]", "[dk]",
    "(de)", "(uk)", "(ru)", "(bg)", "(pl)", "(es)", "(ca)", "(tr)", "(ph)", "(au)", "(cz)", "(usa)", "(it)", "(br)", "(hu)", "(us)", "(ro)", "(dk)"
]

# 4. دالة الفرز والتصنيف الدقيق الشاملة للـ 21 مجموعة بدون استبعاد خاطئ
def classify_channel(channel_name, raw_group=""):
    combined = f"{channel_name} {raw_group}".lower()

    # --- 1. معالجة قنوات beIN بكل فئاتها ---
    if "bein" in combined:
        if any(kw in combined for kw in ["fr", "france", "french", "فرنسية", "فرنسيه"]):
            return "BEIN SPORT FR"
            
        bein_media_keywords = [
            "movie", "movies", "mov", "cinema", "سينما", "drama", "دراما", 
            "series", "مسلسلات", "gourmet", "gorment", "fatafeat", "فتافيت",
            "fox", "life", "action", "bbc", "earth", "star", "world",
            "baraeam", "baraem", "براعم", "jeem", "جيم", "nat geo", "national", "wild",
            "box office", "boxoffice", "pop up", "popup", "media", "entertainment", 
            "junior", "news", "اخبار", "أخبار", "افلام", "أفلام"
        ]
        if any(kw in combined for kw in bein_media_keywords):
            return "BEIN MEDIA"
            
        return "BEIN SPORT AR"

    # --- 2. قنوات TOD CHANNEL ---
    if "tod" in combined or "تود" in combined:
        return "TOD CHANNEL"

    # --- 3. قنوات ألوان الرياضية ---
    if any(kw in combined for kw in ["alwan sport", "alwan sports", "الوان سبورت", "ألوان سبورت", "الوان الرياضية", "ألوان الرياضية"]):
        return "ALWAN SPORT"

    # --- 4. قنوات الفجر ---
    if "fajer" in combined or "الفجر" in combined:
        return "AL FAJER"

    # --- 5. قنوات شوتايم SHOWTIME ---
    if any(kw in combined for kw in ["showtime", "show time", "شوتايم", "شو تايم", "show_time", "osn showtime"]):
        return "SHOWTIME"

    # --- 6. قنوات هوم سينما HOME CINEMA ---
    if any(kw in combined for kw in ["home cinema", "homecinema", "هوم سينما", "هومسينما", "home_cinema", "cinema home"]):
        return "HOME CINEMA"

    # --- 7. قنوات MH ---
    mh_tags = ["mh:", "mh ", "(mh)", "[mh]", "mh_", "mh-", "mh sports", "mh cinema"]
    if any(tag in combined for tag in mh_tags) or combined.startswith("mh ") or "mh" in raw_group.lower().split():
        return "MH"

    # --- 8. قنوات الأطفال ---
    kids_keywords = [
        "tom and jerry", "tom & jerry", "توم وجيري", "توم وجري", "masha", "ماشا", 
        "dora", "دورا", "spacetoon", "سبيستون", "سبيس تون", "wanasat", "وناسة", 
        "baraem", "براعم", "cn arabia", "cartoon network", "كرتون نتورك", "jeem", 
        "تلفزيون جيم", "قناة جيم", "gulli", "tiji", "disney kids", "nickelodeon", "اطفال", "أطفال", "kids"
    ]
    if any(kw in combined for kw in kids_keywords):
        return "KIDS"

    # --- 9. قنوات الجزائر ---
    algeria_keywords = [
        "algeria", "algerie", "algérie", "algerien", "entv", "الجزائر", "الجزائرية", 
        "الهداف", "el heddaf", "el bilad", "البلاد", "الشروق", "echorouk", "النهار", 
        "ennahar", "samira", "سميرة", "numidia", "نوميديا", "الوطنية", "el watania", "al24"
    ]
    if any(kw in combined for kw in algeria_keywords):
        return "ALGERIA"

    # --- 10. القنوات الإخبارية العربية ---
    news_keywords = ["al jazeera", "الجزيرة", "al arabiya", "العربية", "الحدث", "sky news", "سكاي نيوز", "bbc arabic", "فرانس 24", "france 24", "اخبار", "إخبارية", "اخبارية"]
    if any(kw in combined for kw in news_keywords):
        return "ARABIC NEWS"

    # --- 11. قنوات ألوان للأفلام ---
    if "alwan" in combined or "ألوان" in combined or "الوان" in combined:
        return "ALWAN MOVIES"

    # --- 12. قنوات روتانا ---
    if "rotana" in combined or "روتانا" in combined:
        return "ROTANA"

    # --- 13. قنوات MBC ---
    if "mbc" in combined or "ام بي سي" in combined or "إم بي سي" in combined:
        return "MBC GROUP"

    # --- 14. قنوات بوكس أوفيس ---
    if any(kw in combined for kw in ["box office", "boxoffice", "box-office", "بوكس أوفيس", "بوكس اوفيس"]):
        return "BOX OFFICE"

    # --- 15. قنوات نتفليكس ---
    if "netflix" in combined or "نتفليكس" in combined or "نتفلكس" in combined:
        return "NETFLIX"

    # --- 16. قنوات أمازون برايم ---
    if "amazon" in combined or "prime" in combined or "أمازون" in combined or "امازون" in combined:
        return "AMAZON PRIME"

    # --- 17. قنوات HBO ---
    if "hbo" in combined or "اتش بي او" in combined or "إتش بي أوه" in combined:
        return "HBO"

    # --- 18. قنوات وثائقية ---
    doc_keywords = ["nat geo", "national geo", "discovery", "documentary", "الوثائقية", "وثائقية", "ushuaia", "histoire", "science", "docu"]
    if any(kw in combined for kw in doc_keywords):
        return "DOCUMENTARY"

    # --- 19. القنوات الفرنسية العامة ---
    french_tags = ["fr:", "fr ", "(fr)", "[fr]", "france", "french", "fr|"]
    french_kw = ["tf1", "m6", "canal+", "canal", "rmc", "eurosport", "lequipe", "l'equipe", "ocs", "cine", "ciné", "w9", "tmc", "tfx"]
    if any(tag in combined for tag in french_tags) or any(kw in combined for kw in french_kw):
        return "FRENCH"

    # --- تصفية القنوات الأجنبية غير المطلوبة فقط إذا لم تنتم لأي من المجموعات الـ 21 أعلاه ---
    if any(tag in combined for tag in EXCLUDE_TAGS):
        return None

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
                raw_group = channel.get('category', channel.get('group', ''))
                
                if not raw_url or raw_url in seen_urls:
                    continue
                
                group_title = classify_channel(channel_name, raw_group)
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

    target_url = APP2_M3U_URL.replace("output=m3u8", "output=ts")
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

                        raw_group = ""
                        if 'group-title="' in current_extinf:
                            raw_group = current_extinf.split('group-title="')[1].split('"')[0]

                        group_title = classify_channel(channel_name, raw_group)
                        if group_title:
                            logo = ""
                            if 'tvg-logo="' in current_extinf:
                                logo = current_extinf.split('tvg-logo="')[1].split('"')[0]

                            final_url = line_str.replace(".m3u8", ".ts")
                            final_url = final_url.replace("217.60.15.177:8080", "185.191.126.127:8080")

                            if final_url in seen_urls:
                                continue

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
