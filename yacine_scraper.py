import base64
import requests
import json
import time
import os
import re
import random
import urllib.parse
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

# جلب معلومات الـ Gist من متغيرات البيئة الآمنة (GitHub Secrets)
GIST_ID = os.environ.get("GIST_ID")
GITHUB_TOKEN = os.environ.get("GIST_TOKEN")

# قائمة النطاقات المستقرة والفعالة لتطبيق ياسين تيفي
YACINE_DOMAINS = [
    "https://def.yacinelive.com",
    "https://ver3.yacinelive.com",
    "https://v31.yacinelive.com"
]

# ==================== دالة تشفير وفك تشفير AES-128-CBC مخصصة (بايثون صافية) لدراما لايف ====================
s_box = [
    0x63, 0x7c, 0x77, 0x7b, 0xf2, 0x6b, 0x6f, 0xc5, 0x30, 0x01, 0x67, 0x2b, 0xfe, 0xd7, 0xab, 0x76,
    0xca, 0x82, 0xc9, 0x7d, 0xfa, 0x59, 0x47, 0xf0, 0xad, 0xd4, 0xa2, 0xaf, 0x9c, 0xa4, 0x72, 0xc0,
    0xb7, 0xfd, 0x93, 0x26, 0x36, 0x3f, 0xf7, 0xcc, 0x34, 0xa5, 0xe5, 0xf1, 0x71, 0xd8, 0x31, 0x15,
    0x04, 0xc7, 0x23, 0xc3, 0x18, 0x96, 0x05, 0x9a, 0x07, 0x12, 0x80, 0xe2, 0xeb, 0x27, 0xb2, 0x75,
    0x09, 0x83, 0x2c, 0x1a, 0x1b, 0x6e, 0x5a, 0xa0, 0x52, 0x3b, 0xd6, 0xb3, 0x29, 0xe3, 0x2f, 0x84,
    0x53, 0xd1, 0x00, 0xed, 0x20, 0xfc, 0xb1, 0x5b, 0x6a, 0xcb, 0xbe, 0x39, 0x4a, 0x4c, 0x58, 0xcf,
    0xd0, 0xef, 0xaa, 0xfb, 0x43, 0x4d, 0x33, 0x85, 0x45, 0xf9, 0x02, 0x7f, 0x50, 0x3c, 0x9f, 0xa8,
    0x51, 0xa3, 0x40, 0x8f, 0x92, 0x9d, 0x38, 0xf5, 0xbc, 0xb6, 0xda, 0x21, 0x10, 0xff, 0xf3, 0xd2,
    0xcd, 0x0c, 0x13, 0xec, 0x5f, 0x97, 0x44, 0x17, 0xc4, 0xa7, 0x7e, 0x3d, 0x64, 0x5d, 0x19, 0x73,
    0x60, 0x81, 0x4f, 0xdc, 0x22, 0x2a, 0x90, 0x88, 0x46, 0xee, 0xb8, 0x14, 0xde, 0x5e, 0x0b, 0xdb,
    0xe0, 0x32, 0x3a, 0x0a, 0x49, 0x06, 0x24, 0x5c, 0xc2, 0xd3, 0xac, 0x62, 0x91, 0x95, 0xe4, 0x79,
    0xe7, 0xc8, 0x37, 0x6d, 0x8d, 0xd5, 0x4e, 0xa9, 0x6c, 0x56, 0xf4, 0xea, 0x65, 0x7a, 0xae, 0x08,
    0xba, 0x78, 0x25, 0x2e, 0x1c, 0xa6, 0xb4, 0xc6, 0xe8, 0xdd, 0x74, 0x1f, 0x4b, 0xbd, 0x8b, 0x8a,
    0x70, 0x3e, 0xb5, 0x66, 0x48, 0x03, 0xf6, 0x0e, 0x61, 0x35, 0x57, 0xb9, 0x86, 0xc1, 0x1d, 0x9e,
    0xe1, 0xf8, 0x98, 0x11, 0x69, 0xd9, 0x8e, 0x94, 0x9b, 0x1e, 0x87, 0xe9, 0xce, 0x55, 0x28, 0xdf,
    0x8c, 0xa1, 0x89, 0x0d, 0xbf, 0xe6, 0x42, 0x68, 0x41, 0x99, 0x2d, 0x0f, 0xb0, 0x54, 0xbb, 0x16
]

inv_s_box = [
    0x52, 0x09, 0x6a, 0xd5, 0x30, 0x36, 0xa5, 0x38, 0xbf, 0x40, 0xa3, 0x9e, 0x81, 0xf3, 0xd7, 0xfb,
    0x7c, 0xe3, 0x39, 0x82, 0x9b, 0x2f, 0xff, 0x87, 0x34, 0x8e, 0x43, 0x44, 0xc4, 0xde, 0xe9, 0xcb,
    0x54, 0x7b, 0x94, 0x32, 0xa6, 0xc2, 0x23, 0x3d, 0xee, 0x4c, 0x95, 0x0b, 0x42, 0xfa, 0xc3, 0x4e,
    0x08, 0x2e, 0xa1, 0x66, 0x28, 0xd9, 0x24, 0xb2, 0x76, 0x5b, 0xa2, 0x49, 0x6d, 0x8b, 0xd1, 0x25,
    0x72, 0xf8, 0xf6, 0x64, 0x86, 0x68, 0x98, 0x16, 0xd4, 0xa4, 0x5c, 0xcc, 0x5d, 0x65, 0xb6, 0x92,
    0x6c, 0x70, 0x48, 0x50, 0xfd, 0xed, 0xb9, 0xda, 0x5e, 0x15, 0x46, 0x57, 0xa7, 0x8d, 0x9d, 0x84,
    0x90, 0xd8, 0xab, 0x00, 0x8c, 0xbc, 0xd3, 0x0a, 0xf7, 0xe4, 0x58, 0x05, 0xb8, 0xb3, 0x45, 0x06,
    0xd0, 0x2c, 0x1e, 0x8f, 0xca, 0x3f, 0x0f, 0x02, 0xc1, 0xaf, 0xbd, 0x03, 0x01, 0x13, 0x8a, 0x6b,
    0x3a, 0x91, 0x11, 0x41, 0x4f, 0x67, 0xdc, 0xea, 0x97, 0xf2, 0xcf, 0xce, 0xf0, 0xb4, 0xe6, 0x73,
    0x96, 0xac, 0x74, 0x22, 0xe7, 0xad, 0x35, 0x85, 0xe2, 0xf9, 0x37, 0xe8, 0x1c, 0x75, 0xdf, 0x6e,
    0x47, 0xf1, 0x1a, 0x71, 0x1d, 0x29, 0xc5, 0x89, 0x6f, 0xb7, 0x62, 0x0e, 0xaa, 0x18, 0xbe, 0x1b,
    0xfc, 0x56, 0x3e, 0x4b, 0xc6, 0xd2, 0x79, 0x20, 0x9a, 0xdb, 0xc0, 0xfe, 0x78, 0xcd, 0x5a, 0xf4,
    0x1f, 0xdd, 0xa8, 0x33, 0x88, 0x07, 0xc7, 0x31, 0xb1, 0x12, 0x10, 0x59, 0x27, 0x80, 0xec, 0x5f,
    0x60, 0x51, 0x7f, 0xa9, 0x19, 0xb5, 0x4a, 0x0d, 0x2d, 0xe5, 0x7a, 0x9f, 0x93, 0xc9, 0x9c, 0xef,
    0xa0, 0xe0, 0x3b, 0x4d, 0xae, 0x2a, 0xf5, 0xb0, 0xc8, 0xeb, 0xbb, 0x3c, 0x83, 0x53, 0x99, 0x61,
    0x17, 0x2b, 0x04, 0x7e, 0xba, 0x77, 0xd6, 0x26, 0xe1, 0x69, 0x14, 0x63, 0x55, 0x21, 0x0c, 0x7d
]

rcon = [0x00, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1b, 0x36]

def sub_bytes(state):
    for i in range(4):
        for j in range(4):
            state[i][j] = s_box[state[i][j]]

def inv_sub_bytes(state):
    for i in range(4):
        for j in range(4):
            state[i][j] = inv_s_box[state[i][j]]

def shift_rows(state):
    state[1] = state[1][1:] + state[1][:1]
    state[2] = state[2][2:] + state[2][:2]
    state[3] = state[3][3:] + state[3][:3]

def inv_shift_rows(state):
    state[1] = state[1][-1:] + state[1][:-1]
    state[2] = state[2][-2:] + state[2][:-2]
    state[3] = state[3][-3:] + state[3][:-3]

def xtime(a):
    return ((a << 1) ^ 0x1b) & 0xff if (a & 0x80) else (a << 1) & 0xff

def mix_single_column(r):
    t = r[0] ^ r[1] ^ r[2] ^ r[3]
    u = r[0]
    r[0] ^= t ^ xtime(r[0] ^ r[1])
    r[1] ^= t ^ xtime(r[1] ^ r[2])
    r[2] ^= t ^ xtime(r[2] ^ r[3])
    r[3] ^= t ^ xtime(r[3] ^ u)

def mix_columns(state):
    for i in range(4):
        col = [state[j][i] for j in range(4)]
        mix_single_column(col)
        for j in range(4):
            state[j][i] = col[j]

def multiply(x, y):
    res = 0
    for i in range(8):
        if (y & 1):
            res ^= x
        hi = x & 0x80
        x <<= 1
        if hi:
            x ^= 0x1b
        x &= 0xff
        y >>= 1
    return res

def inv_mix_columns(state):
    for i in range(4):
        col = [state[j][i] for j in range(4)]
        new_col = [
            multiply(0x0e, col[0]) ^ multiply(0x0b, col[1]) ^ multiply(0x0d, col[2]) ^ multiply(0x09, col[3]),
            multiply(0x09, col[0]) ^ multiply(0x0e, col[1]) ^ multiply(0x0b, col[2]) ^ multiply(0x0d, col[3]),
            multiply(0x0d, col[0]) ^ multiply(0x09, col[1]) ^ multiply(0x0e, col[2]) ^ multiply(0x0b, col[3]),
            multiply(0x0b, col[0]) ^ multiply(0x0d, col[1]) ^ multiply(0x09, col[2]) ^ multiply(0x0e, col[3])
        ]
        for j in range(4):
            state[j][i] = new_col[j]

def add_round_key(state, round_key):
    for i in range(4):
        for j in range(4):
            state[i][j] ^= round_key[i][j]

def key_expansion(key_bytes):
    words = []
    for i in range(4):
        words.append([key_bytes[4*i], key_bytes[4*i+1], key_bytes[4*i+2], key_bytes[4*i+3]])
    
    for i in range(4, 44):
        temp = list(words[i-1])
        if i % 4 == 0:
            temp = temp[1:] + temp[:1]
            temp = [s_box[b] for b in temp]
            temp[0] ^= rcon[i // 4]
        words.append([words[i-4][j] ^ temp[j] for j in range(4)])
    
    round_keys = []
    for r in range(11):
        r_key = []
        for i in range(4):
            r_key.append([words[4*r+j][i] for j in range(4)])
        round_keys.append(r_key)
    return round_keys

def aes_encrypt_block(block, round_keys):
    state = []
    for i in range(4):
        state.append([block[i], block[i+4], block[i+8], block[i+12]])
    
    add_round_key(state, round_keys[0])
    for r in range(1, 10):
        sub_bytes(state)
        shift_rows(state)
        mix_columns(state)
        add_round_key(state, round_keys[r])
        
    sub_bytes(state)
    shift_rows(state)
    add_round_key(state, round_keys[10])
    
    res = bytearray(16)
    for i in range(4):
        for j in range(4):
            res[i + 4*j] = state[i][j]
    return bytes(res)

def aes_decrypt_block(block, round_keys):
    state = []
    for i in range(4):
        state.append([block[i], block[i+4], block[i+8], block[i+12]])
        
    add_round_key(state, round_keys[10])
    for r in range(9, 0, -1):
        inv_shift_rows(state)
        inv_sub_bytes(state)
        add_round_key(state, round_keys[r])
        inv_mix_columns(state)
        
    inv_shift_rows(state)
    inv_sub_bytes(state)
    add_round_key(state, round_keys[0])
    
    res = bytearray(16)
    for i in range(4):
        for j in range(4):
            res[i + 4*j] = state[i][j]
    return bytes(res)

def aes_cbc_encrypt(data, key_bytes, iv_bytes):
    pad_len = 16 - (len(data) % 16)
    data += bytes([pad_len] * pad_len)
    
    round_keys = key_expansion(key_bytes)
    ciphertext = bytearray()
    prev = iv_bytes
    for i in range(0, len(data), 16):
        block = data[i:i+16]
        xored = bytes([block[j] ^ prev[j] for j in range(16)])
        encrypted = aes_encrypt_block(xored, round_keys)
        ciphertext.extend(encrypted)
        prev = encrypted
    return bytes(ciphertext)

def aes_cbc_decrypt(data, key_bytes, iv_bytes):
    round_keys = key_expansion(key_bytes)
    plaintext = bytearray()
    prev = iv_bytes
    for i in range(0, len(data), 16):
        block = data[i:i+16]
        decrypted = aes_decrypt_block(block, round_keys)
        xored = bytes([decrypted[j] ^ prev[j] for j in range(16)])
        plaintext.extend(xored)
        prev = block
        
    pad_len = plaintext[-1]
    return bytes(plaintext[:-pad_len])

# ==================== دوال تشفير وفك تشفير دراما لايف ====================
DRAMA_KEY = b"0123456789abcdef"
DRAMA_DEFAULT_IV = b"fedcba9876543210"

def drama_encrypt(data_str):
    data_bytes = data_str.encode('utf-8')
    iv_bytes = DRAMA_DEFAULT_IV
    encrypted = aes_cbc_encrypt(data_bytes, DRAMA_KEY, iv_bytes)
    encrypted_b64 = base64.b64encode(encrypted).decode('utf-8')
    iv_b64 = base64.b64encode(iv_bytes).decode('utf-8')
    return f"{encrypted_b64}:{iv_b64}"

def drama_decrypt(encrypted_str):
    if ":" in encrypted_str:
        parts = encrypted_str.split(":")
        encrypted_b64 = parts[0]
        iv_b64 = parts[1]
        iv_bytes = base64.b64decode(iv_b64)
    else:
        encrypted_b64 = encrypted_str
        iv_bytes = DRAMA_DEFAULT_IV
    encrypted_bytes = base64.b64decode(encrypted_b64)
    decrypted = aes_cbc_decrypt(encrypted_bytes, DRAMA_KEY, iv_bytes)
    return decrypted.decode('utf-8', errors='ignore')

# دالة مطابقة القنوات المطلوبة من دراما لايف بدقة متناهية
def is_drama_target(channel_name):
    name_lower = channel_name.lower()
    
    # 1. قنوات الفجر
    if "fajer" in name_lower or "fajr" in name_lower or "الفجر" in name_lower:
        return "Al Fajer"
        
    # 2. الألوان الرياضية
    if "alwan" in name_lower or "الوان" in name_lower or "ألوان" in name_lower:
        return "Alwan Sports"

    # 3. بيين سبورت ماكس
    if "max" in name_lower or "ماكس" in name_lower:
        return "beIN Sports Max"
    
    # 4. بيين سبورت الفرنسية أو العربية
    is_bein = "bein" in name_lower or "بي ان" in name_lower or "بين" in name_lower
    is_french = "fr" in name_lower or "french" in name_lower or "fr:" in name_lower or "fr " in name_lower or "(fr)" in name_lower or "[fr]" in name_lower or "france" in name_lower
    
    if is_bein and is_french:
        return "beIN Sports French"
    elif is_bein and not is_french:
        return "beIN Sports Arabic"
        
    return None

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
        except Exception as e:
            print(f"⚠️ فشل النطاق {domain} بسبب: {e}")
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
        "albashatv.site", "playcasta.online", "AL BASHA TV", "majed-koora.live"
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

# دالة ذكية لاستخراج الأقسام الحالية من الـ Gist لحمايتها في حال حدوث فشل مؤقت للـ API
def extract_section_by_headers(content, current_header, next_headers):
    if current_header not in content:
        return ""
    start_idx = content.find(current_header) + len(current_header)
    end_idx = len(content)
    for next_header in next_headers:
        if next_header in content:
            pos = content.find(next_header)
            if pos > start_idx and pos < end_idx:
                end_idx = pos
    return content[start_idx:end_idx].strip()

# دالة مطورة لمطابقة قنوات الأطفال المستهدفة بدقة عالية باللغتين
def matches_kids(channel_name):
    name_lower = channel_name.lower()
    if any(kw in name_lower for kw in ["tom and jerry", "tom & jerry", "توم وجيري", "توم وجري"]):
        return "Tom and Jerry"
    if "masha" in name_lower or "ماشا" in name_lower:
        return "Masha and the Bear"
    if "dora" in name_lower or "دورا" in name_lower:
        return "Dora"
    if "spacetoon" in name_lower or "سبيستون" in name_lower or "سبيس تون" in name_lower:
        return "Spacetoon"
    if "wanasa" in name_lower or "وناسة" in name_lower:
        return "Wanasat"
    if "baraem" in name_lower or "براعم" in name_lower:
        return "Baraem"
    if "cn arabia" in name_lower or "cartoon network" in name_lower or "كرتون نتورك" in name_lower:
        return "CN Arabia"
    
    if "jeem" in name_lower or "تلفزيون جيم" in name_lower or "قناة جيم" in name_lower or "جيم" in name_lower.split():
        return "Jeem"
    return None


# 1. جلب المحتوى الحالي من الـ Gist وتصفية قنواتك اليدوية
print("📂 جاري جلب محتوى الـ Gist الحالي للنسخ الاحتياطي وحفظ القنوات...")
gist_api_url = f"https://api.github.com/gists/{GIST_ID}"
gist_headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

static_clean = ""
current_content = ""
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

# ترويسات الأقسام لتسهيل استخراج الحالة السابقة كـ Fail-safe ذكي للـ Gist
headers_list = [
    "# ==================== مجموعة قنوات LIVE ====================",
    "# ==================== مجموعة قنوات AL BASHA TV ====================",
    "# ==================== مجموعة قنوات BEIN MAX YACINE TV ====================",
    "# ==================== مجموعة قنوات DRAMA LIVE ====================",
    "# ==================== قنواتك اليدوية والثابتة ===================="
]

# تفعيل جدار حماية حفظ الحالة السابقة للأقسام الأربعة لمنع تعطل أي باقة في حال الفشل
prev_live = extract_section_by_headers(current_content, headers_list[0], headers_list[1:])
prev_basha = extract_section_by_headers(current_content, headers_list[1], headers_list[2:])
prev_yacine = extract_section_by_headers(current_content, headers_list[2], headers_list[3:])
prev_drama = extract_section_by_headers(current_content, headers_list[3], headers_list[4:])

session = create_session()
final_m3u_content = ""

# 2. كشف وتجهيز باقة قنوات LIVE المباشرة ديناميكياً
print("\n⚽ جاري كشف وتجهيز مجموعة قنوات LIVE المباشرة...")
live_separator = "# ==================== مجموعة قنوات LIVE ===================="

live_content = ""
try:
    active_majed_channels = get_majed_dynamic_channels(session)
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
except Exception as e:
    print(f"⚠️ خطأ أثناء تحديث باقة LIVE: {e}")

# تعويض وقائي ذكي لباقة LIVE
if not live_content.strip() and prev_live.strip():
    print("🛡️ فشل جلب باقة LIVE، تم استرداد القنوات السابقة بنجاح لحمايتها من الحذف.")
    live_content = prev_live


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

# فصل قنوات الأطفال لتظهر في المقدمة دائماً
kids_channels_list = []
regular_channels_list = []

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
                
                # فحص ما إذا كانت القناة هي إحدى قنوات الأطفال المطلوبة أولاً
                kids_match = matches_kids(channel_name)
                if kids_match:
                    if use_basha_proxy:
                        final_basha_url = f"http://live-albashatv.site/stream?url={raw_url}"
                        entry = f'#EXTINF:-1 tvg-logo="" group-title="AL BASHA TV", {channel_name}\n{final_basha_url}\n'
                    else:
                        basha_ua = "okhttp/3.9.1"
                        final_basha_url = f"{raw_url}|User-Agent={basha_ua}"
                        entry = (
                            f'#EXTINF:-1 tvg-logo="" group-title="AL BASHA TV", {channel_name}\n'
                            f'#EXTVLCOPT:http-user-agent={basha_ua}\n'
                            f'{final_basha_url}\n'
                        )
                    kids_channels_list.append(entry)
                    seen_basha_urls.add(raw_url)
                    matched_count += 1
                    continue
                
                # وإلا نتابع تصفية القنوات العادية والـ Premium الأخرى
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
                        entry = f'#EXTINF:-1 tvg-logo="" group-title="AL BASHA TV", {channel_name}\n{final_basha_url}\n'
                    else:
                        basha_ua = "okhttp/3.9.1"
                        final_basha_url = f"{raw_url}|User-Agent={basha_ua}"
                        entry = (
                            f'#EXTINF:-1 tvg-logo="" group-title="AL BASHA TV", {channel_name}\n'
                            f'#EXTVLCOPT:http-user-agent={basha_ua}\n'
                            f'{final_basha_url}\n'
                        )
                    regular_channels_list.append(entry)
                    seen_basha_urls.add(raw_url)
                    matched_count += 1
    except Exception as e:
        print(f"❌ خطأ أثناء جلب قنوات الباشا: {e}")

# دمج باقة الأطفال في مقدمة باقة الباشا تيفي تليها القنوات العادية الأخرى
basha_content = "".join(kids_channels_list) + "".join(regular_channels_list)

# تعويض وقائي ذكي لباقة الباشا تيفي في حال فشل الاتصال المؤقت
if not basha_content.strip() and prev_basha.strip():
    print("🛡️ فشل جلب باقة الباشا ديناميكياً، تم استرداد القنوات السابقة بنجاح لحمايتها من الحذف.")
    basha_content = prev_basha
else:
    print(f"🎯 تم استخراج وتصفية ({matched_count}) قناة من الباشا بنجاح (بما في ذلك قنوات الأطفال بالمقدمة).")


# 4. جلب وتنسيق باقة قنوات ياسين تيفي (Yacine TV) ديناميكياً بالكامل
print("\n🚀 جاري جلب قنوات ياسين تيفي (Yacine TV)...")
yacine_separator = "# ==================== مجموعة قنوات BEIN MAX YACINE TV ===================="

# الفئات المستهدفة: 90 لجودة FHD، و 89 لجودة HD، و 91 لجودة SD المنخفضة
targets = {
    "/api/categories/90/channels": "FHD",
    "/api/categories/89/channels": "HD",
    "/api/categories/91/channels": "SD"
}

yacine_headers = {
    "Accept": "application/json",
    "Accept-Encoding": "gzip",
    "Connection": "Keep-Alive",
    "User-Agent": "okhttp/4.12.0"
}

# تصحيح الـ User-Agent وإعداد ترويسات الحماية
ua_value = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
referer_value = "https://re.ycn-redirect.com/"
origin_value = "https://re.ycn-redirect.com"

yacine_content = ""
for category_endpoint, quality in targets.items():
    print(f"🔄 جاري سحب باقة ياسين بجودة {quality}...")
    channels_data = fetch_and_decrypt_yacine_dynamic(session, category_endpoint, yacine_headers)
    
    if channels_data and 'data' in channels_data:
        channels_list = channels_data['data']
        
        # 1. تصفية قنوات BEIN سبورت وماكس المستهدفة أولاً
        filtered_channels = []
        for channel in channels_list:
            channel_name = channel.get('name') or ""
            channel_name_lower = channel_name.lower()
            
            is_target = (
                "max" in channel_name_lower or 
                "bein" in channel_name_lower or 
                "ماكس" in channel_name_lower or 
                "بين" in channel_name_lower or
                "sport" in channel_name_lower
            )
            if is_target:
                filtered_channels.append(channel)
                
        # 2. ترتيب القنوات تصاعدياً ورقمياً لضمان الفرز من 1 إلى 5 بشكل منظم
        def extract_number(name):
            nums = re.findall(r'\d+', name)
            return int(nums[0]) if nums else 999
            
        filtered_channels.sort(key=lambda x: extract_number(x.get('name', '')))
        
        # 3. البدء في استخراج الروابط وتصفية سيرفرات الـ DRM غير الشغالة
        for index, channel in enumerate(filtered_channels):
            channel_name = channel.get('name')
            channel_id = channel.get('id')
            
            print(f"   ⏳ [{index + 1}/{len(filtered_channels)}] جاري استخراج: {channel_name}...")
            channel_detail_endpoint = f"/api/channel/{channel_id}"
            detail_data = fetch_and_decrypt_yacine_dynamic(session, channel_detail_endpoint, yacine_headers)
            
            if detail_data and 'data' in detail_data:
                streams = detail_data['data']
                
                # تصفية وفلترة السيرفرات الصالحة للريسيفر و VLC (استبعاد ملفات .mpd ومسارات cenc المحمية)
                valid_urls = []
                for stream in streams:
                    raw_url = stream.get('url')
                    if not raw_url:
                        continue
                    
                    # تحويل روابط Redbee من mpd إلى m3u8 تلقائياً لضمان التوافق
                    if "/dash/.mpd" in raw_url:
                        raw_url = raw_url.replace("/dash/.mpd", "/playlist.m3u8")
                        
                    # استبعاد روابط DASH / DRM المشفرة بنظام Widevine لأنها مخصصة فقط لتطبيق ياسين وتتطلب مشغل مشفر
                    if ".mpd" in raw_url.lower() or "cenc" in raw_url.lower() or "/dash/" in raw_url.lower():
                        continue
                        
                    valid_urls.append(raw_url)
                
                # كتابة السيرفرات بالأسماء والتنسيق المرتب المطلوب
                for stream_idx, final_url in enumerate(valid_urls):
                    # التسمية النظيفة: السيرفر الأول يحمل اسم القناة مباشرة، والسيرفرات التالية يكتب بجانبها (S2) ثم (S3)...
                    if stream_idx == 0:
                        display_name = f"{channel_name} {quality}"
                    else:
                        display_name = f"{channel_name} {quality} (S{stream_idx + 1})"
                        
                    final_url_with_headers = f"{final_url}|User-Agent={ua_value}&Referer={referer_value}&Origin={origin_value}"
                    
                    # كتابة ترويسة EXTVLCOPT القياسية وتذييل الـ Pipe لتعمل القنوات بنسبة 100% على كافة الأجهزة
                    yacine_content += f'#EXTINF:-1 tvg-logo="" group-title="BEIN MAX YACINE TV", {display_name}\n'
                    yacine_content += f'#EXTVLCOPT:http-user-agent={ua_value}\n'
                    yacine_content += f'#EXTVLCOPT:http-referrer={referer_value}\n'
                    yacine_content += f'#EXTVLCOPT:http-origin={origin_value}\n'
                    yacine_content += f'{final_url_with_headers}\n'
                    print(f"      ✔️ نجاح استخراج السيرفر: {display_name}")
            
            # تأخير عشوائي ذكي (Jitter) يتراوح بين 0.4 و 1.2 ثانية لتفادي كشف السكربت كـ Bot أو حظر الـ IP
            time.sleep(random.uniform(0.4, 1.2))

# تعويض وقائي ذكي لباقة ياسين تيفي
if not yacine_content.strip() and prev_yacine.strip():
    print("🛡️ فشل جلب باقة ياسين تيفي، تم استرداد القنوات السابقة بنجاح لحمايتها من الحذف.")
    yacine_content = prev_yacine


# 5. جلب وتصفية باقة قنوات دراما لايف (Drama Live)
print("\n🚀 جاري جلب قنوات دراما لايف (Drama Live)...")
drama_separator = "# ==================== مجموعة قنوات DRAMA LIVE ===================="

# قائمة الفئات المطلوبة في دراما لايف (الرياضية والعربية لشمول الفجر والألوان)
drama_topics = ["sport", "arabic"]
drama_content = ""
seen_drama_urls = set()
drama_matched_count = 0

# إعداد المعاملات الافتراضية للطلب المشفر لدراما لايف
device_id_val = "24d1-9dd-ae90-4798-b5a5-3bb15626e0b0"
user_id_val = "_11410_1783427058075_12345"
timestamp_val = str(int(time.time() * 1000))

drama_regular_list = []

for topic in drama_topics:
    print(f"🔄 جاري سحب باقة دراما لايف لفئة {topic}...")
    
    # بناء الـ JSON للطلب
    topic_payload = {
        "user_id": user_id_val,
        "device_id": device_id_val,
        "version_neme": "186",
        "language": "fr",
        "timezone": "Europe/Paris",
        "ACTIVATED_TYPE": "direct",
        "OsStoreVersion": False,
        "isPremium": False,
        "isCoupon_active": False,
        "hideAds": False,
        "appCount": "{}",
        "main_sport": topic
    }
    
    # تشفير الطلب
    encrypted_payload_str = drama_encrypt(json.dumps(topic_payload))
    
    # إرسال طلب POST لجلب تصنيفات القنوات (نستخدم https مباشرة لتجنب تحويل طريقة الطلب)
    drama_url = "https://live.1spbgmu.com/api/live/livedrama/v13.0.0/getLiveByTopic"
    drama_req_headers = {
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; SM-S9210 Build/PQ3A.190705.05150936)"
    }
    
    try:
        response = session.post(drama_url, headers=drama_req_headers, data=encrypted_payload_str, timeout=15)
        if response.status_code in [200, 201]:
            decrypted_response = drama_decrypt(response.text)
            response_json = json.loads(decrypted_response)
            
            # التدقيق الذكي في مفتاح قائمة القنوات (دراما لايف يرسل القنوات تحت مفتاح "live")
            channels_list = []
            if response_json and "live" in response_json:
                channels_list = response_json["live"]
            elif response_json and "data" in response_json:
                channels_list = response_json["data"]
                
            for channel in channels_list:
                channel_name = channel.get("title") or channel.get("name") or ""
                channel_id = channel.get("id_live") or channel.get("id")
                
                if not channel_name or not channel_id:
                    continue
                    
                # تصفية القنوات الحصرية المطلوبة فقط (بيين، الفجر، الألوان)
                target_category = is_drama_target(channel_name)
                if not target_category:
                    continue
                    
                print(f"   ⏳ جاري استخراج بث: {channel_name} ({target_category})...")
                
                # طلب جلب السيرفرات لهذه القناة بالتحديد
                stream_payload = {
                    "type": "tv",
                    "id_live": channel_id
                }
                enc_stream_payload = drama_encrypt(json.dumps(stream_payload))
                
                streams_url = "https://live.1spbgmu.com/api/live/livedrama/v13.0.0/getLiveAllStreamsById"
                stream_response = session.post(streams_url, headers=drama_req_headers, data=enc_stream_payload, timeout=10)
                
                if stream_response.status_code in [200, 201]:
                    dec_streams = drama_decrypt(stream_response.text)
                    streams_json = json.loads(dec_streams)
                    
                    streams_list = []
                    if streams_json and "data" in streams_json:
                        streams_list = streams_json["data"]
                    elif streams_json and "live" in streams_json:
                        streams_list = streams_json["live"]
                        
                    for stream in streams_list:
                        stream_url = stream.get("url")
                        if not stream_url or stream_url in seen_drama_urls:
                            continue
                            
                        # جلب الترويسات المطلوبة لتشغيل بث دراما لايف بنجاح على الأجهزة والريسيفرات
                        stream_ua = stream.get("user_agent", "Dalvik/2.1.0 (Linux; U; Android 9; SM-S9210 Build/PQ3A.190705.05150936)")
                        stream_referer = stream.get("referer", "http://live.1spbgmu.com/")
                        
                        final_url_with_headers = f"{stream_url}|User-Agent={stream_ua}&Referer={stream_referer}"
                        display_name = f"{channel_name} (Drama Live)"
                        
                        # كتابة ترويسة EXTVLCOPT وتذييل الـ Pipe لتعمل القنوات بنسبة 100% على كافة الأجهزة والريسيفرات
                        entry = (
                            f'#EXTINF:-1 tvg-logo="" group-title="DRAMA LIVE", {display_name}\n'
                            f'#EXTVLCOPT:http-user-agent={stream_ua}\n'
                            f'#EXTVLCOPT:http-referrer={stream_referer}\n'
                            f'{final_url_with_headers}\n'
                        )
                        
                        drama_regular_list.append(entry)
                        seen_drama_urls.add(stream_url)
                        drama_matched_count += 1
                        break # نكتفي بأول سيرفر شغال للقناة
                time.sleep(random.uniform(0.3, 0.8)) # تأخير عشوائي لحماية السكربت من الحظر
    except Exception as e:
        print(f"❌ خطأ أثناء جلب قنوات دراما لايف لفئة {topic}: {e}")

# دمج المحتوى
drama_content = "".join(drama_regular_list)

# تعويض وقائي ذكي لباقة دراما لايف في حال فشل الاتصال المؤقت
if not drama_content.strip() and prev_drama.strip():
    print("🛡️ فشل جلب باقة دراما لايف ديناميكياً، تم استرداد القنوات السابقة بنجاح لحمايتها من الحذف.")
    drama_content = prev_drama
else:
    print(f"🎯 تم استخراج وتصفية ({drama_matched_count}) قناة من دراما لايف بنجاح.")


# دمج المحتوى بالترتيب مع الحفاظ الكامل على قنواتك اليدوية
final_m3u_content = f"#EXTM3U\n\n{live_separator}\n{live_content}\n\n{basha_separator}\n{basha_content}\n\n{yacine_separator}\n{yacine_content}\n\n{drama_separator}\n{drama_content}\n\n# ==================== قنواتك اليدوية والثابتة ====================\n{static_clean}"

# 5. تحديث الـ Gist الخاص بك
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
