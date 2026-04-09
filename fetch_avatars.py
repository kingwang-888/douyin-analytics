import urllib.request
import re
import json

accounts = [
    ('鱿鱼说游', 'https://www.douyin.com/user/MS4wLjABAAAAyu1J-qZ9fXf0esDwO5SWzPDisSRXgGBsM1klJy7-NgQ'),
    ('牛马说游戏', 'https://www.douyin.com/user/MS4wLjABAAAAbEhN014Hq0pA7k2yIRkQ7mOY46ZZZOH6w7uXIe994hHLp8o1Z17jCJYSOlVbCljt'),
    ('哈吉米说游戏', 'https://www.douyin.com/user/MS4wLjABAAAA44gOfrNdAaQmyCkA8mQA2x8TIQcm7dkitB-xHQebMLc'),
    ('阿密说游戏', 'https://www.douyin.com/user/MS4wLjABAAAAqA3963YexIxtbKepAIt59HgspQukXU-32MTaretPRWAvt7aNYaTCkiE00rfYPH8u'),
    ('有料玩家', 'https://www.douyin.com/user/MS4wLjABAAAApYjIWIHhPLW84hb52ByouBaImWt1yZOtQxMFDqoYXAkAg-FroLMeFnZY4SnqAX8K'),
]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

results = {}

for name, url in accounts:
    try:
        print(f'Fetching {name}...')
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode('utf-8', errors='ignore')

        # 搜索所有 douyinpic 相关的头像URL
        avatar_urls = re.findall(r'https?://[^\s"\'\\]+avatar[^\s"\'\\]+', html)

        # 找 100x100 规格的头像（最清晰）
        best = None
        for u in avatar_urls:
            if '100x100' in u or '300x300' in u:
                best = u
                break

        if not best and avatar_urls:
            best = avatar_urls[0]

        if best:
            results[name] = best
            print(f'  SUCCESS: {best}')
        else:
            print(f'  FAILED: no avatar found')
            results[name] = None

    except Exception as e:
        print(f'  ERROR: {e}')
        results[name] = None

# 保存结果
with open('d:/xy/Desktop/网页动态表/avatars.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print('\n=== 结果汇总 ===')
for name, url in results.items():
    print(f'{name}: {url}')
