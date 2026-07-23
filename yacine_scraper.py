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
    retries = Retry(total=5, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

# 3. قائمة التصفية لاستبعاد القنوات غير المرغوبة
EXCLUDE_TAGS = [
    "vip de", "vip uk", "vip ru", "vip bg", "vip pl", "vip es", "vip tr", "vip ph", "vip it", "vip br", "vip us", "vip dk", "vip hu", "vip ro",
    "de:", "uk:", "ru:", "bg:", "pl:", "es:", "ca:", "tr:", "ph:", "au:", "cz:", "usa:", "it:", "br:", "hu:", "us:", "ro:", "dk:", "usa)",
    " de ", " uk ", " ru ", " bg ", " pl ", " es ", " ca ", " tr ", " ph ", " au ", " cz ", " usa ", " it ", " br ", " hu ", " us ", " ro ", " dk ",
    "[de]", "[uk]", "[ru]", "[bg]", "[pl]", "[es]", "[ca]", "[tr]", "[ph]", "[au]", "[cz]", "[usa]", "[it]", "[br]", "[hu]", "[us]", "[ro]", "[dk]",
    "(de)", "(uk)", "(ru)", "(bg)", "(pl)", "(es)", "(ca)", "(tr)", "(ph)", "(au)", "(cz)", "(usa)", "(it)", "(br)", "(hu)", "(us)", "(ro)", "(dk)"
]

# 4. دالة التصنيف وتوزيع القنوات
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

# 5. جلب وتجميع القنوات وإقران الشفرات تلقائياً
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

    print("📡 جاري الاتصال بتطبيق الباشا وجلب القنوات وتوليد التوكينات تلقائياً...")
    try:
        response = session.post(api_url, headers=headers, data=payload, timeout=20)
        if response.status_code == 200:
            channels = response.json()
            
            if not isinstance(channels, list):
                print("⚠️ تنبيه: استجابة السيرفر غير متوافقة.")
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
                
                # استخراج حقل الشفرة التلقائي من استجابة السيرفر
                token_val = (
                    channel.get('token', '').strip() or 
                    channel.get('sec', '').strip() or 
                    channel.get('auth', '').strip() or 
                    channel.get('key', '').strip() or 
                    channel.get('hash', '').strip()
                )
                
                vlc_opts = ["#EXTVLCOPT:http-header=Icy-MetaData: 1"]
                if basha_ua:
                    vlc_opts.append(f'#EXTVLCOPT:http-user-agent={basha_ua}')
                if referer:
                    vlc_opts.append(f'#EXTVLCOPT:http-referrer={referer}')
                if cookie:
                    vlc_opts.append(f'#EXTVLCOPT:http-cookie={cookie}')
                
                vlc_opts_str = "\n".join(vlc_opts)
                
                # تنظيف مسار البث
                final_url = raw_url.strip().replace("live///", "live/").replace("live//", "live/")
                
                # إضافة شفرة التوكين إن وجدت في بيانات القناة
                if token_val and "?token=" not in final_url:
                    final_url = f"{final_url}?token={token_val}"
                
                entry = f'#EXTINF:-1 tvg-logo="{logo}" group-title="{group_title}",{channel_name}\n'
                entry += f'{vlc_opts_str}\n'
                entry += f'{final_url}'
                
                grouped_channels[group_title].append(entry)
                seen_urls.add(raw_url)
                total_count += 1
                
    except Exception as e:
        print(f"❌ خطأ أثناء جلب البيانات: {e}")
        
    return grouped_channels, total_count

# 6. تحديث الـ Gist في GitHub
def main():
    if not GIST_ID or not GITHUB_TOKEN:
        print("❌ خطأ: لم يتم العثور على GIST_ID أو GIST_TOKEN!")
        return

    session = create_session()
    grouped_channels, total_count = fetch_al_basha_channels(session)
    
    if total_count == 0:
        print("\n🛡️ [درع الحماية]: لم يتم جلب قنوات جديدة، تم حفظ الملف الحالي لحمايته.")
        return

    preferred_order = [
        "BEIN SPORT AR",
        "ALWAN SPORT",
        "AL FAJER",
        "BEIN SPORT FR",
        "BEIN MEDIA",
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
                print(f"\n🎉 تم تحديث الـ Gist بنجاح! تم استخراج وإقران الشفرات لـ ({total_count}) قناة وتعمل الآن على VLC والريسيفر.")
            else:
                print(f"\n❌ فشل تحديث الـ Gist. كود الحالة: {patch_resp.status_code}")
        else:
            print(f"\n❌ فشل الوصول إلى Gist API: {get_gist.status_code}")
    except Exception as e:
        print(f"\n❌ خطأ: {e}")

if __name__ == "__main__":
    main()
