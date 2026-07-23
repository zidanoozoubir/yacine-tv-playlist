import os
import time
import requests
from collections import defaultdict
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

# 1. جلب متغيرات البيئة الخاصة بـ GitHub Gist
GIST_ID = os.environ.get("GIST_ID")
GITHUB_TOKEN = os.environ.get("GIST_TOKEN")

# 2. إنشاء جلسة اتصال مستقرة
def create_session():
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

# 3. قائمة القنوات/الدول غير المرغوبة (استبعاد تام)
EXCLUDE_TAGS = [
    "vip de", "vip uk", "vip ru", "vip bg", "vip pl", "vip es", "vip tr", "vip ph", "vip it", "vip br", "vip us", "vip dk", "vip hu", "vip ro",
    "de:", "uk:", "ru:", "bg:", "pl:", "es:", "ca:", "tr:", "ph:", "au:", "cz:", "usa:", "it:", "br:", "hu:", "us:", "ro:", "dk:", "usa)",
    " de ", " uk ", " ru ", " bg ", " pl ", " es ", " ca ", " tr ", " ph ", " au ", " cz ", " usa ", " it ", " br ", " hu ", " us ", " ro ", " dk ",
    "[de]", "[uk]", "[ru]", "[bg]", "[pl]", "[es]", "[ca]", "[tr]", "[ph]", "[au]", "[cz]", "[usa]", "[it]", "[br]", "[hu]", "[us]", "[ro]", "[dk]",
    "(de)", "(uk)", "(ru)", "(bg)", "(pl)", "(es)", "(ca)", "(tr)", "(ph)", "(au)", "(cz)", "(usa)", "(it)", "(br)", "(hu)", "(us)", "(ro)", "(dk)"
]

# 4. دالة التصنيف المتقدمة وتوزيع القنوات
def classify_channel(channel_name):
    name_lower = channel_name.lower()
    
    # استبعاد القنوات الأجنبية غير المرغوبة
    if any(tag in name_lower for tag in EXCLUDE_TAGS):
        return None

    # معالجة قنوات beIN وتفكيكها إلى (رياضة عربية - رياضة فرنسية - ترفيه وأفلام)
    if "bein" in name_lower:
        # قنوات beIN الرياضية الفرنسية
        if any(kw in name_lower for kw in ["fr", "france", "french", "فرنسية", "فرنسيه"]):
            return "BEIN SPORT FR"
            
        # قنوات beIN الإعلامية والترفيهية (أفلام، مسلسلات، سينما، دراما)
        bein_media_keywords = [
            "movie", "movies", "cinema", "سينما", "drama", "دراما", 
            "series", "مسلسلات", "gourmet", "box office", "boxoffice", 
            "pop up", "popup", "media", "entertainment", "junior", "افلام", "أفلام"
        ]
        if any(kw in name_lower for kw in bein_media_keywords):
            return "BEIN MEDIA"
            
        # المتبقي هو قنوات beIN الرياضية العربية
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

    # قنوات ألوان للأفلام والسينما
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

# 5. جلب وتجميع القنوات
def fetch_al_basha_channels(session):
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

    print("🚀 جاري جلب وتجميع القنوات وفرز مجموعة BEIN MEDIA الترفيهية...")
    try:
        response = session.post(api_url, headers=headers, data=payload, timeout=15)
        if response.status_code == 200:
            channels = response.json()
            
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
                final_url = raw_url.replace("live///", "live/").strip()
                
                entry = f'#EXTINF:-1 tvg-logo="{logo}" group-title="{group_title}",{channel_name}\n'
                entry += f'{vlc_opts_str}\n'
                entry += f'{final_url}'
                
                grouped_channels[group_title].append(entry)
                seen_urls.add(raw_url)
                total_count += 1
                
            print(f"🎯 تم الفرز والترتيب بنجاح لأكثر من ({total_count}) قناة.")
    except Exception as e:
        print(f"❌ خطأ أثناء جلب القنوات: {e}")
        
    return grouped_channels

# 6. تحديث ملف Gist
def main():
    if not GIST_ID or not GITHUB_TOKEN:
        print("❌ خطأ: متغيرات البيئة GIST_ID أو GIST_TOKEN غير معرفة!")
        return

    session = create_session()
    grouped_channels = fetch_al_basha_channels(session)
    
    preferred_order = [
        "BEIN SPORT AR",   # 1. بي إن سبورتس الرياضية العربية
        "ALWAN SPORT",     # 2. ألوان الرياضية
        "AL FAJER",        # 3. قنوات الفجر
        "BEIN SPORT FR",   # 4. بي إن سبورتس الفرنسية
        "BEIN MEDIA",      # 5. بي إن الترفيهية للأفلام والمسلسلات (جديد)
        "KIDS",            # 6. قنوات الأطفال
        "ALGERIA",         # 7. قنوات الجزائر
        "ARABIC NEWS",     # 8. الأخبارية العربية
        # بقية المجموعات:
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
    
    gist_api_url = f"https://api.github.com/gists/{GIST_ID}"
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
                print("🎉 تم التحديث بنجاح! تم التعديل وفصل مجموعة BEIN MEDIA بنجاح.")
            else:
                print(f"❌ فشل رفع الملف. الكود: {patch_resp.status_code}")
        else:
            print(f"❌ فشل الاتصال بـ Gist API. الكود: {get_gist.status_code}")
    except Exception as e:
        print(f"❌ خطأ: {e}")

if __name__ == "__main__":
    main()
