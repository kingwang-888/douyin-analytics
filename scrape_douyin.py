# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
"""
Douyin Account Scraper v2 — 支持登录模式
================================================
功能：
  1. 首次运行：打开可见浏览器 → 扫码/验证码登录 → 自动保存Cookie
  2. 之后运行：自动加载Cookie → 无需重新登录
  
用法：
  python scrape_douyin.py          # 正常模式（先尝试用已有cookie）
  python scrape_douyin.py --login   # 强制重新登录（清除旧cookie）
"""
import asyncio
import json
import os
import re
import argparse
from pathlib import Path

from playwright.async_api import async_playwright

# ====== 5个目标账号（真实内部ID URL） ======
ACCOUNTS = [
    {"douyinId": "71214210408", "name": "鱿鱼说游",
     "url": "https://www.douyin.com/user/MS4wLjABAAAAyu1J-qZ9fXf0esDwO5SWzPDisSRXgGBsM1klJy7-NgQ"},
    {"douyinId": "58501769370", "name": "牛马说游戏",
     "url": "https://www.douyin.com/user/MS4wLjABAAAAbEhN014Hq0pA7k2yIRkQ7mOY46ZZZOH6w7uXIe994hHLp8o1Z17jCJYSOlVbCljt"},
    {"douyinId": "ming99888899", "name": "哈吉米说游戏",
     "url": "https://www.douyin.com/user/MS4wLjABAAAA44gOfrNdAaQmyCkA8mQA2x8TIQcm7dkitB-xHQebMLc"},
    {"douyinId": "TikTokxy123", "name": "阿密说游戏",
     "url": "https://www.douyin.com/user/MS4wLjABAAAAqA3963YexIxtbKepAIt59HgspQukXU-32MTaretPRWAvt7aNYaTCkiE00rfYPH8u"},
    {"douyinId": "520panchun", "name": "有料玩家",
     "url": "https://www.douyin.com/user/MS4wLjABAAAApYjIWIHhPLW84hb52ByouBaImWt1yZOtQxMFDqoYXAkAg-FroLMeFnZY4SnqAX8K"},
]

SCRIPT_DIR = Path(__file__).parent
SCREENSHOT_DIR = SCRIPT_DIR / "screenshots"
COOKIE_FILE = SCRIPT_DIR / "douyin_cookies.json"
SCREENSHOT_DIR.mkdir(exist_ok=True)


async def save_cookies(context):
    """保存浏览器Cookie到文件"""
    cookies = await context.cookies()
    with open(COOKIE_FILE, "w", encoding="utf-8") as f:
        json.dump(cookies, f, ensure_ascii=False, indent=2)
    print("  [✓] 已保存 {} 个Cookie到: {}".format(len(cookies), COOKIE_FILE))


async def load_cookies(context):
    """从文件加载Cookie到浏览器"""
    if not COOKIE_FILE.exists():
        return False
    try:
        with open(COOKIE_FILE, "r", encoding="utf-8") as f:
            cookies = json.load(f)
        await context.add_cookies(cookies)
        print("  [✓] 已加载 {} 个Cookie".format(len(cookies)))
        return True
    except Exception as e:
        print("  [!] 加载Cookie失败: {}".format(e))
        return False


def is_login_page(page_text, url):
    """检查是否还在登录页面（未登录状态）"""
    # 强登录页特征：URL 包含 passport/login，或页面主体是登录框
    login_url_indicators = ['passport', '/login', 'verify']
    url_lower = (url or '').lower()
    if any(ind in url_lower for ind in login_url_indicators):
        return True

    # 页面文字特征：大量登录关键词 + 没有已登录特征
    login_keywords = ['请登录', '密码登录', '短信登录', '扫码登录', '手机号登录',
                       '账号注册', '立即登录', '验证码', '一键登录']
    text = (page_text or '')
    login_score = sum(1 for kw in login_keywords if kw in text)

    # 已登录的特征：有用户相关内容
    logged_in_indicators = ['粉丝', '获赞', '作品', '关注', '首页推荐',
                             '+ 发布', '消息', '投稿', '创作中心',
                             '我的首页', '个人主页']
    has_logged_in = any(kw in text for kw in logged_in_indicators)

    # 登录分 >= 4 且没有已登录特征 → 在登录页
    if login_score >= 4 and not has_logged_in:
        return True

    return False


def is_fully_logged_in(page_text, url):
    """检查是否已完成登录（用于确认可以继续采集）"""
    return not is_login_page(page_text, url)


async def do_login(context, page):
    """引导用户手动登录抖音 — 等待用户完成登录后按回车确认"""
    print("\n" + "=" * 60)
    print("  🔐 请在浏览器窗口中完成抖音登录")
    print("  支持方式：扫码登录 / 密码登录 / 短信登录")
    print("  " + "-" * 56)
    print("  ⚠️  登录成功后 → 回到【本终端】按【回车键】继续！")
    print("=" * 60)

    # 先访问抖音首页触发登录框
    await page.goto("https://www.douyin.com/", wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(3)

    # 启动后台线程等待用户按回车
    import threading
    confirmed = threading.Event()

    def wait_for_enter():
        try:
            input("\n  >>> 登录完成后请按回车键继续 <<<\n")
            confirmed.set()
        except (EOFError, KeyboardInterrupt):
            pass

    input_thread = threading.Thread(target=wait_for_enter, daemon=True)
    input_thread.start()

    print("  ⏳ 等待你操作浏览器完成登录...（无时间限制，不急）")

    # 后台轮询检测状态并给反馈
    last_status = None
    while not confirmed.is_set():
        await asyncio.sleep(2)

        try:
            current_url = page.url
            body_text = ""
            try:
                body_text = await page.evaluate("() => document.body ? document.body.innerText : ''")
            except Exception:
                pass

            if not is_fully_logged_in(body_text, current_url):
                if last_status != "waiting":
                    print("  ⏳ 检测到仍在登录页，请在浏览器中完成登录...")
                    last_status = "waiting"
            else:
                if last_status != "detected":
                    print("  ✅ 检测到你已登录！现在请回到终端按【回车】继续 >>>")
                    last_status = "detected"
        except Exception:
            pass  # 页面未就绪，忽略

    # 用户已按回车，等页面稳定
    await asyncio.sleep(2)

    # 最终验证一次
    final_url = page.url
    final_text = ""
    try:
        final_text = await page.evaluate("() => document.body ? document.body.innerText : ''")
    except Exception:
        pass

    if is_fully_logged_in(final_text, final_url):
        print("\n  [✓] 登录确认成功！开始采集数据...")
    else:
        print("\n  [!] 页面可能还在登录状态，但将按你的确认继续采集")
    return True


async def extract_account_data(page, account):
    """
    从已登录的抖音主页提取完整账号数据。
    提取策略：
      1. 尝试通过页面DOM结构化选择器获取
      2. 通过正则匹配页面文本中的数字
      3. 通过截图辅助确认
    """
    data = {
        "douyinId": account["douyinId"],
        "name": account["name"],
        "url": account["url"],
        "nickname": None,
        "avatarUrl": None,
        "fans": None,
        "likes": None,
        "following": None,
        "videos": None,
        "description": None,
        "location": None,
        "rawText": "",
        "verified": False,
    }

    try:
        # 访问账号主页
        resp = await page.goto(account["url"], wait_until="domcontentloaded", timeout=30000)
        print("  HTTP状态: {}".format(resp.status if resp else "N/A"))

        # 等待动态内容加载
        await asyncio.sleep(5)

        # 额外等待：确保 SSR 数据已注入
        await asyncio.sleep(2)

        # 检查是否需要登录
        body_text = await page.evaluate("""() => {
            return document.body ? document.body.innerText : '';
        }""")
        data["rawText"] = (body_text or "")[:5000]
        
        if not is_fully_logged_in(body_text or "", ""):
            print("  [!] 页面可能未登录，数据可能不完整")
            # 仍然尝试提取，但标记警告

        # 截图保存
        safe_name = "real_{}".format(account["douyinId"])
        ss_path = SCREENSHOT_DIR / "{}.png".format(safe_name)
        await page.screenshot(path=str(ss_path), full_page=False)
        print("  [📷] 截图: {}".format(ss_path))

        # ====== 1. 头像URL ======
        # ★★★ 策略优先级：RENDER_DATA(SSR) > meta标签 > DOM选择器 > 最大图 ★★★
        avatar_info = await page.evaluate("""() => {
            // ===== 方法A: 从 RENDER_DATA (SSR数据) 提取 — 最可靠 =====
            try {
                const scripts = document.querySelectorAll('script[id="__NEXT_DATA__"], script[type="application/json"]');
                for (const s of scripts) {
                    const text = s.textContent || '';
                    if (!text) continue;
                    let data;
                    try { data = JSON.parse(text); } catch(e) {}
                    if (!data) continue;
                    
                    // 搜索所有包含 "avatar" 的路径
                    function findAvatar(obj, depth=0) {
                        if (!obj || typeof obj !== 'object' || depth > 10) return null;
                        if (Array.isArray(obj)) {
                            for (const item of obj) {
                                const r = findAvatar(item, depth+1);
                                if (r && r.includes('douyinpic')) return r;
                            }
                        } else {
                            for (const key of Object.keys(obj)) {
                                const val = obj[key];
                                if (typeof val === 'string') {
                                    if ((val.includes('avatar') || val.includes('aweme-avatar')) && val.includes('douyinpic')) {
                                        return val;
                                    }
                                    // 也检查 URL 列表中的头像
                                    if (val.startsWith('http') && (val.includes('100x100') || val.includes('300x300')) && val.includes('tos-cn')) {
                                        return val;
                                    }
                                } else if (val && typeof val === 'object') {
                                    const r = findAvatar(val, depth+1);
                                    if (r && r.includes('douyinpic')) return r;
                                }
                            }
                        }
                    }
                    const result = findAvatar(data);
                    if (result) return {src: result, method: 'RENDER_DATA'};
                }
            } catch(e) {}

            // ===== 方法B: 从页面内联脚本提取 =====
            try {
                const allScripts = document.querySelectorAll('script:not([src])');
                for (const s of allScripts) {
                    const text = s.textContent || '';
                    if (text.includes('avatarLarger') || text.includes('avatar_thumb')) {
                        const match = text.match(/"avatar(Larger|Thumb|medium|large)"[^}]*?"uri"\s*:\s*"([^"]+)"/i);
                        if (match && match[2]) {
                            return {src: match[2], method: 'inline_script:' + match[1]};
                        }
                    }
                    // 直接找 douyinpic + 100x100 或 300x300 的完整URL
                    const urlMatch = text.match(/(https?:\/\/[^"'\\]*douyinpic[^"'\\]*(?:100x100|300x300|aweme-avatar)[^"'\\]*)/i);
                    if (urlMatch) {
                        return {src: urlMatch[1], method: 'inline_script_url'};
                    }
                }
            } catch(e) {}

            // ===== 方法C: DOM选择器（原逻辑）=====
            const selectors = [
                '[data-e2e="user-avatar"] img',
                '.user-avatar img', '.avatar-container img',
                '[class*="avatar"] img',
                'img[src*="aweme-avatar"]', 
                'img[src*="tos-cn"][src*="avatar"]',
            ];
            
            for (const sel of selectors) {
                const el = document.querySelector(sel);
                if (el && el.src && !el.src.includes('data:image')) return {src: el.src, method: 'selector:' + sel};
            }

            // ===== 方法D: 找最大的接近正方形的图片 =====
            const imgs = Array.from(document.querySelectorAll('img'));
            let best = null, maxArea = 0;
            for (const img of imgs) {
                if (img.naturalWidth > 80 && img.src &&
                    !img.src.includes('icon') && !img.src.includes('logo') && 
                    !img.src.includes('sprite') && !img.src.includes('bg-')) {
                    const area = img.naturalWidth * img.naturalHeight;
                    const ratio = Math.max(img.naturalWidth, img.naturalHeight) / Math.min(img.naturalWidth, img.naturalHeight);
                    // 头像特征：正方形、中等大小（80~400px）、来自CDN
                    if (area > maxArea && ratio < 2.0 && area < 200000) {
                        maxArea = area;
                        best = {src: img.src, method: 'largest_square'};
                    }
                }
            }
            
            // 如果找到的是通栏大图（太大了），返回null
            if (best && best.src) {
                return best;
            }
            return null;
        }""")
        avatar_info = await page.evaluate("""() => {
            const selectors = [
                '.user-avatar img', '.avatar-container img',
                '[class*="avatar"] img', '[class*="Avatar"] img',
                '.account-avatar img', '.profile-avatar img',
                '[class*="userAvatar"] img', '[class*="UserAvatar"] img',
                'img[src*="aweme"]', 'img[src*="tos-cn"]',
                'img[src*="bytedance"]', 'img[src*="byteimg"]',
                // 抖音新版选择器
                '[data-e2e="user-avatar"] img',
                '[class*="profile"] [class*="avatar"] img'
            ];
            
            // 方法1: 直接选择器
            for (const sel of selectors) {
                const el = document.querySelector(sel);
                if (el && el.src && !el.src.includes('data:image')) return {src: el.src, method: 'selector:' + sel};
            }
            
            // 方法2: 找最大的头像尺寸图片
            const imgs = Array.from(document.querySelectorAll('img'));
            let best = null, maxArea = 0;
            for (const img of imgs) {
                if (img.naturalWidth > 80 && img.src &&
                    !img.src.includes('icon') && !img.src.includes('logo') && 
                    !img.src.includes('sprite')) {
                    const area = img.naturalWidth * img.naturalHeight;
                    // 头像通常是接近正方形的
                    const ratio = Math.max(img.naturalWidth, img.naturalHeight) / Math.min(img.naturalWidth, img.naturalHeight);
                    if (area > maxArea && ratio < 2.0) {
                        maxArea = area;
                        best = {src: img.src, method: 'largest:' + img.naturalWidth + 'x' + img.naturalHeight};
                    }
                }
            }
            return best;
        }""")
        
        if avatar_info:
            data["avatarUrl"] = avatar_info.get("src") if isinstance(avatar_info, dict) else avatar_info
            method = avatar_info.get("method", "") if isinstance(avatar_info, dict) else "unknown"
            print("  [👤] 头像: {} ... ({})".format(str(data["avatarUrl"])[:80], method))
        else:
            print("  [👤] 头像: 未找到")

        # ====== 2. 昵称 ======
        nickname = await page.evaluate("""() => {
            const sels = [
                '[class*="nickname"]', '[class*="userName"]', 
                '[class*="user-name"]', '[class*="author-name"]',
                '[class*="NickName"]', '[class*="nickName"]',
                '[data-e2e="user-info"] h1', '[data-e2e="user-info"] [class*="name"]',
                'h1', 'h2 span', '[class*="title"]'
            ];
            for (const sel of sels) {
                for (const el of document.querySelectorAll(sel)) {
                    const t = (el.innerText || '').trim();
                    if (t && t.length >= 2 && t.length <= 20 && 
                        !t.includes('登录') && !t.includes('注册') && !t.includes('首页'))
                        return t;
                }
            }
            return null;
        }""")
        data["nickname"] = nickname
        print("  [📝] 昵称: {}".format(nickname))

        # ====== 3. 结构化数据提取（核心） ======
        # 使用多种策略提取数字数据
        extracted = await page.evaluate("""() => {
            const results = {};
            
            // 策略A: 查找包含特定关键词的元素
            const patterns = [
                {key: 'fans', keywords: ['粉丝', '关注者'], label: 'fans'},
                {key: 'likes', keywords: ['获赞', '总赞', '点赞'], label: 'likes'},
                {key: 'following', keywords: ['关注'], exclude: ['粉丝'], label: 'following'},
                {key: 'videos', keywords: ['作品', '视频'], label: 'videos'},
            ];
            
            // 收集所有文本节点中的数字信息
            const allElements = document.querySelectorAll('*');
            const numberItems = [];
            
            for (const el of allElements) {
                // 只看叶子节点（无子元素的）
                if (el.children.length > 0) continue;
                
                const text = (el.innerText || '').trim();
                if (!text || text.length > 30) continue;
                
                // 匹配带单位的数字：如 15.1万、1000、2.5亿
                const numMatch = text.match(/^(\\d+[,.]?\\d*)([万亿\\s]*)$/);
                if (!numMatch) continue;
                
                const parentText = (el.parentElement?.innerText || '').slice(0, 50);
                numberItems.push({
                    value: text,
                    parentHint: parentText,
                    tag: el.tagName,
                    cls: (el.className || '').toString().slice(0, 50),
                });
            }
            
            results.numberItems = numberItems.slice(0, 30);
            
            // 尝试找具体的计数容器
            // 抖音通常用类似这样的结构展示数据
            const countSels = [
                '[class*="count"]', '[class*="Count"]',
                '[class*="number"]', '[class*="Number"]',
                '[class*="stat"]', '[class*="Stat"]',
                '[data-e2e]'
            ];
            
            results.countElements = [];
            for (const sel of countSels) {
                for (const el of document.querySelectorAll(sel)) {
                    const t = (el.innerText || '').trim();
                    if (t && /\\d/.test(t)) {
                        results.countElements.push({
                            selector: sel,
                            text: t,
                            e2e: el.getAttribute('data-e2e'),
                            className: (el.className || '').toString().slice(0, 60)
                        });
                    }
                }
            }
            results.countElements = results.countElements.slice(0, 20);
            
            // 获取简介/description
            const descSels = [
                '[class*="signature"]', '[class*="Signature"]',
                '[class*="desc"]', '[class*="Desc"]',
                '[class*="bio"]', '[class*="Bio"]',
                '[data-e2e="user-signature"]',
                '[data-e2e="user-desc"]'
            ];
            for (const sel of descSels) {
                const el = document.querySelector(sel);
                if (el) {
                    const t = (el.innerText || '').trim();
                    if (t && t.length > 3 && t.length < 200) {
                        results.description = t;
                        break;
                    }
                }
            }
            
            // 地区
            const locSels = ['[class*="location"]', '[class*="Location"]', '[class*="region"]'];
            for (const sel of locSels) {
                const el = document.querySelector(sel);
                if (el) {
                    const t = (el.innerText || '').trim();
                    if (t && t.length <= 10) { results.location = t; break; }
                }
            }

            // 认证标识
            results.verified = !!document.querySelector('[class*="verify"], [class*="verified"], [class*="auth"]');
            
            return results;
        }""")

        print("  [🔢] 发现 {} 个数字元素, {} 个计数容器".format(
            len(extracted.get('numberItems', [])),
            len(extracted.get('countElements', []))))
        
        # 打印调试信息
        for item in extracted.get('countElements', [])[:15]:
            print("         <{} e2e='{}'> {}".format(
                (item.get('className','') or '')[:30],
                item.get('e2e',''), item.get('text','')))
        
        for item in extracted.get('numberItems', [])[:10]:
            print("         数值={} | parent={}".format(item['value'], (item.get('parentHint','') or '')[:40]))

        # ====== 从提取结果中解析各字段 ======
        # ★★★ 优先级: e2e结构化 > DOM关键词 > 正则文本 > 兜底 ★★★
        raw_text = data["rawText"]

        # 方法1 (最高优先级): e2e 属性精确匹配
        if extracted.get('countElements'):
            for ce in extracted['countElements']:
                text_val = (ce.get('text') or '').strip()
                e2e_val = (ce.get('e2e') or '').lower()

                vm = re.match(r'^([0-9]+\.?[0-9]*)([万亿wW]?)$', text_val)
                if not vm:
                    continue

                if ('user-info-fan' in e2e_val or ('fan' in e2e_val and 'follow' not in e2e_val)) and not data.get('fans'):
                    data['fans'] = text_val
                    print("  [e2e] fans = {} ({})".format(data['fans'], e2e_val))

                elif ('user-info-like' in e2e_val or ('like' in e2e_val)) and not data.get('likes'):
                    data['likes'] = text_val
                    print("  [e2e] likes = {} ({})".format(data['likes'], e2e_val))

                elif ('user-info-follow' in e2e_val or ('follow' in e2e_val and 'fan' not in e2e_val)) and not data.get('following'):
                    data['following'] = text_val
                    print("  [e2e] following = {} ({})".format(data['following'], e2e_val))

                elif ('tab-count' in e2e_val) and not data.get('videos'):
                    data['videos'] = text_val
                    print("  [e2e] videos = {} ({})".format(data['videos'], e2e_val))

        # 方法2: DOM 关键词模糊匹配
        if extracted.get('countElements'):
            fan_cands, like_cands, foll_cands, vid_cands = [], [], [], []
            for c in extracted['countElements']:
                t = (c.get('text') or '').strip()
                e2 = (c.get('e2e') or '').lower()
                if not re.match(r'^\d', t): continue
                if any(k in e2 for k in ['fan']): fan_cands.append(t)
                if any(k in e2 for k in ['like','heart']): like_cands.append(t)
                if any(k in e2 for k in ['follow']) and 'fan' not in e2: foll_cands.append(t)
                if any(k in e2 for k in ['video','tab-count']): vid_cands.append(t)

            if not data.get('fans') and fan_cands: data['fans'] = fan_cands[0]; print("  [DOM] fans =", data['fans'])
            if not data.get('likes') and like_cands: data['likes'] = like_cands[0]; print("  [DOM] likes =", data['likes'])
            if not data.get('following') and foll_cands: data['following'] = foll_cands[0]; print("  [DOM] following =", data['following'])
            if not data.get('videos') and vid_cands: data['videos'] = vid_cands[0]; print("  [DOM] videos =", data['videos'])

        # 方法3: 正则文本匹配（兜底）
        regex_patterns = [
            (r'[粉星][丝公][\s:\n]+([0-9]+\.?[0-9]*[万亿])', 'fans'),
            (r'(?:获赞|总赞)[\s:\n]+([0-9]+\.?[0-9]*[万亿])', 'likes'),
            (r'关[注註][\s:\n]+([0-9]+)', 'following'),
            (r'作[品品][\s:\n]+([0-9]+)', 'videos'),
        ]
        for pattern, key in regex_patterns:
            if data.get(key): continue
            m = re.search(pattern, raw_text)
            if m:
                data[key] = m.group(1).strip()
                print("  [正则] {} = {} (可能不准)".format(key, data[key]))

        # 方法3: 兜底 - 按顺序取大数字
        if not all([data.get('fans'), data.get('likes')]):
            all_numbers = re.findall(r'([0-9]+\.?[0-9]*[万亿]?)', raw_text)
            big_nums = [n for n in all_numbers if re.search(r'[万亿]', n) or float(re.sub(r'[万亿]','',n)) >= 100]
            keys_to_fill = ['fans', 'likes', 'following']
            idx = 0
            for key in keys_to_fill:
                if not data.get(key) and idx < len(big_nums):
                    data[key] = big_nums[idx]
                    print("  [兜底] {} = {}".format(key, data[key]))
                    idx += 1

        # 简介/地区
        if extracted.get('description'):
            data["description"] = extracted["description"]
            print("  [📋] 简介: {}".format(data["description"][:80]))
        if extracted.get('location'):
            data["location"] = extracted["location"]
            print("  [📍] 地区: {}".format(data["location"]))
        data["verified"] = extracted.get("verified", False)

        # 最终结果汇总
        print("\n  ──── 采集结果 ────")
        for k in ['nickname', 'fans', 'likes', 'following', 'videos', 'description', 'location']:
            v = data.get(k)
            if v:
                display = str(v) if len(str(v)) < 80 else str(v)[:80]+'...'
                print("  ✓ {}: {}".format(k, display))
            else:
                print("  ✗ {}: 未采集到".format(k))

    except Exception as e:
        print("  [ERROR] 采集失败: {}".format(e))
        import traceback
        traceback.print_exc()
        data["error"] = str(e)

    return data


async def main():
    parser = argparse.ArgumentParser(description='抖音账号数据采集工具 v2')
    parser.add_argument('--login', action='store_true', help='强制重新登录（清除旧Cookie）')
    parser.add_argument('--headless', action='store_true', help='无头模式（仅当有有效Cookie时有效）')
    args = parser.parse_args()

    print("=" * 60)
    print("  🎮 抖音账号数据采集工具 v2 (支持登录)")
    print("=" * 60)

    # 如果要求强制登录，删除旧Cookie
    if args.login and COOKIE_FILE.exists():
        COOKIE_FILE.unlink()
        print("  [!] 已清除旧Cookie，将重新登录")

    need_login = True
    if not args.login and COOKIE_FILE.exists():
        need_login = False
        print("  [ℹ️] 发现已有Cookie文件")

    results = []

    async with async_playwright() as p:
        # 启动浏览器（首次需要登录时必须可见）
        browser = await p.chromium.launch(
            headless=args.headless and not need_login,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-infobars',
                '--no-sandbox',
            ]
        )

        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            locale="zh-CN",
        )
        
        # 反检测脚本
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
            // 覆盖 chrome 对象
            window.chrome = {runtime: {}, loadTimes: function(){}, csi: function(){}};
            // 覆盖 permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) =>
                parameters.name === 'notifications'
                    ? Promise.resolve({state: Notification.permission})
                    : originalQuery(parameters);
        """)

        page = await context.new_page()

        # ====== 登录流程 ======
        if need_login:
            success = await do_login(context, page)
            if success:
                await save_cookies(context)
                print("\n  [✅] Cookie已保存，后续运行无需重新登录！")
            else:
                print("\n  [❌] 登录超时。可以稍后重试，或使用 --login 参数重新登录")
                await browser.close()
                return
        else:
            # 加载已有Cookie
            loaded = await load_cookies(context)
            if loaded:
                # 验证Cookie是否有效
                print("\n  🔄 验证Cookie有效性...")
                await page.goto("https://www.douyin.com/", wait_until="domcontentloaded", timeout=20000)
                await asyncio.sleep(3)
                check_text = await page.evaluate("() => document.body ? document.body.innerText : ''")
                if not is_fully_logged_in(check_text, page.url):
                    print("  [!] Cookie可能已过期，需要重新登录")
                    print("  运行: python scrape_douyin.py --login")
                    need_login = True
                    success = await do_login(context, page)
                    if success:
                        await save_cookies(context)
                    else:
                        print("  [❌] 登录失败")
                        await browser.close()
                        return

        # ====== 开始采集数据 ======
        print("\n" + "=" * 60)
        print("  📊 开始采集 {} 个账号数据".format(len(ACCOUNTS)))
        print("=" * 60)

        for i, acct in enumerate(ACCOUNTS):
            print("\n[{}/{}] {} (抖音号: {})".format(i+1, len(ACCOUNTS), acct["name"], acct["douyinId"]))
            print("-" * 50)

            try:
                data = await extract_account_data(page, acct)
                results.append(data)
            except Exception as e:
                print("  [FAIL] {}".format(e))
                results.append({"douyinId": acct["douyinId"], "name": acct["name"], "error": str(e)})

            await asyncio.sleep(2)

        await browser.close()

    # ====== 保存结果 ======
    out_path = SCRIPT_DIR / "scrape_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 60)
    print("  ✅ 完成! 结果已保存到: {}".format(out_path))
    print("=" * 60)

    print("\n┌───────────── 采集汇总 ─────────────┐")
    for r in results:
        if r.get("error"):
            name_str = str(r['name'])[:8]
            err_str = str(r['error'])[:40]
            print("│ ❌ {} | 错误: {}".format(name_str.ljust(8), err_str))
        else:
            name_str = (r.get('nickname') or r['name'])[:8]
            fans_str = r.get('fans') or '?'
            likes_str = r.get('likes') or '?'
            videos_str = r.get('videos') or '?'
            avatar_str = '有头像' if r.get('avatarUrl') else '无头像'
            print("│ ✅ {} | 粉丝:{} 获赞:{} 作品:{} | {}".format(
                name_str.ljust(8),
                fans_str.ljust(8),
                likes_str.ljust(8),
                videos_str.ljust(6),
                avatar_str
            ))
    print("└─────────────────────────────────────┘")


if __name__ == "__main__":
    asyncio.run(main())
