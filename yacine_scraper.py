import os
import requests
from collections import defaultdict
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

# 1. جلب متغيرات البيئة من GitHub Secrets
GIST_ID = os.environ.get("GIST_ID")            # Gist الأول (الباشا - kz.m3u)
GIST_ID_NEW = os.environ.get("GIST_ID_NEW")    # Gist الثاني (التطبيق الجديد - s1.m3u)
GITHUB_TOKEN = os.environ.get("GIST_TOKEN")

# 2. إنشاء جلسة اتصال مستقرة
def create_session():
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

# 3. قائمة التصفية واستبعاد القنوات غير المرغوبة
EXCLUDE_TAGS = [
    "vip de", "vip uk", "vip ru", "vip bg", "vip pl", "vip es", "vip tr", "vip ph", "vip it", "vip br", "vip us", "vip dk", "vip hu", "vip ro",
    "de:", "uk:", "ru:", "bg:", "pl:", "es:", "ca:", "tr:", "ph:", "au:", "cz:", "usa:", "it:", "br:", "hu:", "us:", "ro:", "dk:", "usa)",
    " de ", " uk ", " ru ", " bg ", " pl ", " es ", " ca ", " tr ", " ph ", " au ", " cz ", " usa ", " it ", " br ", " hu ", " us ", " ro ", " dk ",
    "[de]", "[uk]", "[ru]", "[bg]", "[pl]", "[es]", "[ca]", "[tr]", "[ph]", "[au]", "[cz]", "[usa]", "[it]", "[br]", "[hu]", "[us]", "[ro]", "[dk]",
    "(de)", "(uk)", "(ru)", "(bg)", "(pl)", "(es)", "(ca)", "(tr)", "(ph)", "(au)", "(cz)", "(usa)", "(it)", "(br)", "(hu)", "(us)", "(ro)", "(dk)"
]

# 4. دالة التصنيف الموحدة للقنوات
def classify_channel(channel_name):
    name_lower = channel_name.lower()
    
    if any(tag in name_lower for tag in EXCLUDE_TAGS):
        return None

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

    doc_keywords = ["nat geo", "national geo", "discovery", "documentary", "الوثائقية", "وثائقية", "ushuaia", "histoire", "science"]
    if any(kw in name_lower for kw in doc_keywords):
        return "DOCUMENTARY"

    french_tags = ["fr:", "fr ", "(fr)", "[fr]", "france"]
    french_kw = ["tf1", "m6", "canal+", "canal", "rmc", "eurosport", "lequipe", "l'equipe", "ocs", "cine", "ciné", "w9", "tmc", "tfx"]
    if any(tag in name_lower for tag in french_tags) or any(kw in name_lower for kw in french_kw):
        return "FRENCH"

    return None

# 5. جلب وتصنيف قنوات الباشا تيفي (المهمة الأولى ⬅️ kz.m3u)
def fetch_al_basha_channels(session):
    api_url = "https://albashatv.site/api.php"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "okhttp/3.9.1"
    }
    payload = "method=o6&event=view"
    
    grouped_channels = defaultdict(list)
    seen_urls = set()
    total_count = 0

    print("🚀 [1/2] جلب وتصنيف قنوات الباشا تيفي...")
    try:
        response = session.post(api_url, headers=headers, data=payload, timeout=10)
        if response.status_code == 200:
            channels = response.json()
            
            if isinstance(channels, list):
                for channel in channels:
                    channel_name = channel.get('name', '').strip()
                    raw_url = channel.get('url', '').strip()
                    
                    if not raw_url or raw_url in seen_urls:
                        continue
                    
                    group_title = classify_channel(channel_name)
                    if not group_title:
                        continue
                    
                    logo = channel.get('logo', '').strip()
                    vlc_opts_str = "#EXTVLCOPT:http-header=Icy-MetaData: 1\n#EXTVLCOPT:http-user-agent=Mozilla/5.0"
                    
                    final_url = raw_url.strip().replace("live///", "live/").replace("live//", "live/")
                    final_url = final_url.replace("217.60.15.177:8080", "185.191.126.127:8080")
                    if final_url.endswith(".ts"):
                        final_url = final_url[:-3] + ".m3u8"
                    elif not final_url.endswith(".m3u8") and "?" not in final_url:
                        final_url = final_url + ".m3u8"
                    
                    entry = f'#EXTINF:-1 tvg-logo="{logo}" group-title="{group_title}",{channel_name}\n{vlc_opts_str}\n{final_url}'
                    grouped_channels[group_title].append(entry)
                    seen_urls.add(raw_url)
                    total_count += 1
    except Exception as e:
        print(f"❌ خطأ أثناء جلب الباشا: {e}")
        
    return grouped_channels, total_count

# 6. جلب وتصنيف قنوات التطبيق الجديد (المهمة الثانية ⬅️ s1.m3u)
def fetch_new_app_channels(session):
    new_app_url = "http://217.60.15.177:8080/get.php?username=b0:99:d7:15:88:50&password=3090914536649669&type=m3u_plus&output=m3u8"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    grouped_channels = defaultdict(list)
    total_count = 0

    print("🚀 [2/2] جلب وتصنيف قنوات التطبيق الجديد...")
    try:
        response = session.get(new_app_url, headers=headers, timeout=12)
        if response.status_code == 200:
            content = response.text
            lines = content.splitlines()
            
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
                                
                            vlc_opts_str = "#EXTVLCOPT:http-header=Icy-MetaData: 1\n#EXTVLCOPT:http-user-agent=Mozilla/5.0"
                            final_url = line_str.replace("217.60.15.177:8080", "185.191.126.127:8080")
                            
                            entry = f'#EXTINF:-1 tvg-logo="{logo}" group-title="{group_title}",{channel_name}\n{vlc_opts_str}\n{final_url}'
                            grouped_channels[group_title].append(entry)
                            total_count += 1
                        current_extinf = ""
    except Exception as e:
        print(f"❌ خطأ أثناء جلب التطبيق الجديد: {e}")
        
    return grouped_channels, total_count

# 7. دالة رفع المحتوى إلى Gist
def update_gist_file(session, gist_id, grouped_channels, total_count, gist_name_log):
    if not gist_id:
        print(f"⚠️ تنبيه: المعرف {gist_name_log} غير معرف في متغيرات البيئة!")
        return

    if total_count == 0:
        print(f"🛡️ لم يتم جلب قنوات جديدة لـ {gist_name_log}، تم إلغاء التحديث للحفاظ على القنوات.")
        return

    preferred_order = [
        "BEIN SPORT AR", "ALWAN SPORT", "AL FAJER", "BEIN SPORT FR", 
        "BEIN MEDIA", "KIDS", "ALGERIA", "ARABIC NEWS", "ALWAN MOVIES", 
        "ROTANA", "MBC GROUP", "BOX OFFICE", "NETFLIX", "AMAZON PRIME", 
        "HBO", "DOCUMENTARY", "FRENCH"
    ]
    
    m3u_lines = ["#EXTM3U"]
    for group in preferred_order:
        if group in grouped_channels and grouped_channels[group]:
            m3u_lines.extend(grouped_channels[group])
            
    final_m3u_content = "\n".join(m3u_lines)
    
    gist_api_url = f"https://api.github.com/gists/{gist_id}"
    gist_headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    
    try:
        get_gist = session.get(gist_api_url, headers=gist_headers, timeout=10)
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
                print(f"🎉 تم تحديث {gist_name_log} بنجاح لـ ({total_count}) قناة!")
            else:
                print(f"❌ فشل تحديث {gist_name_log}: {patch_resp.status_code}")
        else:
            print(f"❌ فشل الوصول لـ Gist ({gist_name_log}): {get_gist.status_code}")
    except Exception as e:
        print(f"❌ خطأ أثناء رفع {gist_name_log}: {e}")

# 8. التنفيذ الرئيسي
def main():
    if not GITHUB_TOKEN:
        print("❌ خطأ: GIST_TOKEN غير معرف!")
        return

    session = create_session()
    
    # المهمة الأولى: قنوات الباشا تيفي ⬅️ Gist 1 (kz.m3u)
    basha_groups, basha_count = fetch_al_basha_channels(session)
    update_gist_file(session, GIST_ID, basha_groups, basha_count, "GIST_ID (الباشا تيفي - kz.m3u)")
    
    print("-" * 50)
    
    # المهمة الثانية: قنوات التطبيق الجديد ⬅️ Gist 2 (s1.m3u)
    new_app_groups, new_app_count = fetch_new_app_channels(session)
    update_gist_file(session, GIST_ID_NEW, new_app_groups, new_app_count, "GIST_ID_NEW (التطبيق الجديد - s1.m3u)")

if __name__ == "__main__":
    main()
