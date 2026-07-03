import requests
import os

GIST_ID = os.environ.get("GIST_ID")
GITHUB_TOKEN = os.environ.get("GIST_TOKEN")

gist_api_url = f"https://api.github.com/gists/{GIST_ID}"
gist_headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

# تفريغ الملف ليكون سطراً واحداً فقط
update_data = {"files": {"kz.m3u": {"content": "#EXTM3U\n"}}}
response = requests.patch(gist_api_url, headers=gist_headers, json=update_data)
if response.status_code == 200:
    print("✔️ Gist reset successfully!")
else:
    print("❌ Failed to reset Gist.")
