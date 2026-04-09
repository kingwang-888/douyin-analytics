# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
"""
sync_to_html.py — 将爬虫采集结果自动同步到 HTML 仪表板
============================================================
用法：
  python sync_to_html.py              # 读取最新 scrape_results.json 并更新 douyin-analytics.html
  python sync_to_html.py --force      # 强制同步（即使数据看起来相同）

工作流程：
  1. 读取 scrape_results.json（爬虫输出）
  2. 用新数据替换 douyin-analytics.html 中的 accountsData
  3. 更新日期戳和统计数字
"""
import json
import re
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
RESULTS_FILE = SCRIPT_DIR / "scrape_results.json"
HTML_FILE = SCRIPT_DIR / "douyin-analytics.html"


def load_scrape_results():
    if not RESULTS_FILE.exists():
        print("ERROR: 未找到采集文件: {}".format(RESULTS_FILE))
        print("   请先运行: python scrape_douyin.py")
        return None
    
    with open(RESULTS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    print("OK: 已加载 {} 个账号的采集数据".format(len(data)))
    return data


def load_html():
    if not HTML_FILE.exists():
        print("ERROR: 未找到HTML文件: {}".format(HTML_FILE))
        return None
    
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        return f.read()


# ====== 账号静态配置 ======
ACCOUNT_CONFIGS = {
    "71214210408": {
        "id": 1, "name": "鱿鱼说游", "douyinId": "71214210408",
        "profileUrl": "https://www.douyin.com/user/MS4wLjABAAAAyu1J-qZ9fXf0esDwO5SWzPDisSRXgGBsM1klJy7-NgQ",
        "avatar_letter": "鱿",
        "avatarBg": "linear-gradient(135deg, #ff6b35, #f7418f)",
        "category": "游戏解说/娱乐",
        "statusColor": "#07c160", "level": "S级", "trend": "上升",
        "score": 88, "scoreColor": "#07c160",
        "totalPlays": "6650万", "totalComments": "8.2万",
        "avgPlay": "151万", "likeRate": "1.14%", "commentRate": "0.12%",
        "strengths": ["获赞量最高","作品数量较多(44)","内容风格鲜明有趣","游戏品类覆盖广"],
        "weaknesses": ["部分视频时长偏长导致完播率下降","更新频率可进一步提升"],
        "bio_default": "我是鱿鱼带你们了解最新游戏资讯",
        "location_default": "广东·深圳",
    },
    "58501769370": {
        "id": 2, "name": "牛马说游戏", "douyinId": "58501769370",
        "profileUrl": "https://www.douyin.com/user/MS4wLjABAAAAbEhN014Hq0pA7k2yIRkQ7mOY46ZZZOH6w7uXIe994hHLp8o1Z17jCJYSOlVbCljt",
        "avatar_letter": "牛",
        "avatarBg": "linear-gradient(135deg, #667eea, #764ba2)",
        "category": "游戏攻略/无畏契约",
        "statusColor": "#00c9d4", "level": "A级", "trend": "上升",
        "score": 78, "scoreColor": "#00c9d4",
        "totalPlays": "4280万", "totalComments": "5.6万",
        "avgPlay": "82万", "likeRate": "0.78%", "commentRate": "0.13%",
        "strengths": ["作品数量最多(52条)","专注垂直赛道","攻略内容实用性强","更新节奏稳定"],
        "weaknesses": ["点赞率偏低可优化封面","互动率有提升空间"],
        "bio_default": "Game to the World!",
        "location_default": "广东",
    },
    "ming99888899": {
        "id": 3, "name": "哈吉米说游戏", "douyinId": "ming99888899",
        "profileUrl": "https://www.douyin.com/user/MS4wLjABAAAA44gOfrNdAaQmyCkA8mQA2x8TIQcm7dkitB-xHQebMLc",
        "avatar_letter": "吉",
        "avatarBg": "linear-gradient(135deg, #f093fb, #f5576c)",
        "category": "游戏杂谈/多品类",
        "statusColor": "#faad14", "level": "A级", "trend": "波动",
        "score": 75, "scoreColor": "#faad14",
        "totalPlays": "5120万", "totalComments": "11.2万",
        "avgPlay": "142万", "likeRate": "1.10%", "commentRate": "0.22%",
        "strengths": ["评论互动率最高(0.22%)","多品类覆盖受众广","个人风格辨识度强"],
        "weaknesses": ["数据波动较大需稳定产出","品类分散可能影响标签精准度"],
        "bio_default": "人要有梦想没有梦想跟咸鱼有什么区别.",
        "location_default": "江西·上饶",
    },
    "TikTokxy123": {
        "id": 4, "name": "阿密说游戏", "douyinId": "TikTokxy123",
        "profileUrl": "https://www.douyin.com/user/MS4wLjABAAAAqA3963YexIxtbKepAIt59HgspQukXU-32MTaretPRWAvt7aNYaTCkiE00rfYPH8u",
        "avatar_letter": "密",
        "avatarBg": "linear-gradient(135deg, #4facfe, #00f2fe)",
        "category": "手游攻略/教学",
        "statusColor": "#1890ff", "level": "B级", "trend": "上升",
        "score": 72, "scoreColor": "#1890ff",
        "totalPlays": "3650万", "totalComments": "4.1万",
        "avgPlay": "96万", "likeRate": "1.20%", "commentRate": "0.11%",
        "strengths": ["点赞率高(1.20%)","手游教学定位清晰","内容实用性较强"],
        "weaknesses": ["平均播放量偏低","B级账号整体竞争力待提升"],
        "bio_default": "最有趣的灵魂 也是最有趣的游戏资讯",
        "location_default": "广东",
    },
    "520panchun": {
        "id": 5, "name": "有料玩家", "douyinId": "520panchun",
        "profileUrl": "https://www.douyin.com/user/MS4wLjABAAAApYjIWIHhPLW84hb52ByouBaImWt1yZOtQxMFDqoYXAkAg-FroLMeFnZY4SnqAX8K",
        "avatar_letter": "料",
        "avatarBg": "linear-gradient(135deg, #fa709a, #fee140)",
        "category": "游戏资讯/盘点",
        "statusColor": "#faad14", "level": "B级", "trend": "恢复中",
        "score": 60, "scoreColor": "#faad14",
        "totalPlays": "2950万", "totalComments": "2.1万",
        "avgPlay": "590万", "likeRate": "1.64%", "commentRate": "0.07%",
        "strengths": ["点赞率最高(1.64%)","选题角度新颖","信息整合能力强","已恢复更新(从1条到5条)"],
        "weaknesses": ["作品数仍然偏少(5条)","整体数据呈恢复期需持续观察","缺乏稳定日更节奏"],
        "bio_default": "游戏热点挖掘机，每日速递新游爆料，带你玩转游戏圈！",
        "location_default": "广东",
    },
}


def build_account_data(scrape_data):
    """将爬虫采集的数据转换为 JS accountsData 格式"""
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    accounts_js = []
    total_videos_int = 0

    for item in scrape_data:
        did = item.get("douyinId", "")
        cfg = ACCOUNT_CONFIGS.get(did)

        if not cfg:
            print("  WARN: 未知账号 {} ({})".format(did, item.get("name")))
            continue

        # === 提取 bio / location ===
        raw_text = item.get("rawText", "")
        
        bio_val = item.get("description")
        if not bio_val or bio_val == "null":
            bio_val = cfg.get("bio_default", "")

        loc_val = item.get("location")
        if not loc_val:
            for lp in [r"([\u4e00-\u9fa5]+·[\u4e00-\u9fa5]+)", r"(广东|江西|北京|上海)"]:
                m = re.search(lp, raw_text)
                if m:
                    loc_val = m.group(1)
                    break
            if not loc_val:
                loc_val = cfg.get("location_default", "")

        # === 计算总视频数 ===
        try:
            vs = str(item.get("videos") or "0").replace("条", "").strip()
            total_videos_int += int(float(re.sub(r"[万亿]", "", vs)))
        except Exception:
            pass

        avatar_url = item.get("avatarUrl")

        entry = {}
        entry["id"] = cfg["id"]
        entry["name"] = item.get("nickname") or cfg["name"]
        entry["douyinId"] = cfg["douyinId"]
        entry["profileUrl"] = cfg["profileUrl"]
        entry["avatarUrl"] = avatar_url  # 真实头像URL (可能为None)
        entry["avatar"] = cfg["avatar_letter"]
        entry["avatarBg"] = cfg["avatarBg"]
        entry["category"] = cfg["category"]
        entry["bio"] = bio_val
        entry["location"] = loc_val
        entry["statusColor"] = cfg["statusColor"]
        entry["level"] = cfg["level"]
        entry["trend"] = cfg["trend"]
        entry["fans"] = item.get("fans", "?")
        entry["following"] = item.get("following", "?")
        entry["totalLikes"] = item.get("likes", "?")
        entry["videos"] = str(item.get("videos", "?")).replace("条", "")
        entry["totalPlays"] = cfg["totalPlays"]
        entry["totalComments"] = cfg["totalComments"]
        entry["avgPlay"] = cfg["avgPlay"]
        entry["likeRate"] = cfg["likeRate"]
        entry["commentRate"] = cfg["commentRate"]
        entry["score"] = cfg["score"]
        entry["scoreColor"] = cfg["scoreColor"]
        entry["strengths"] = cfg["strengths"]
        entry["weaknesses"] = cfg["weaknesses"]

        # optimization 建议 (保持原样不动态生成)
        opt_list = []
        if did == "71214210408":
            opt_list = [
                {"title":"优化视频前3秒黄金开头","desc":"游戏解说类视频前3秒定生死，用高燃画面+悬念提问留住观众","priority":"high","color":"#ff4d4f"},
                {"title":"主动互动提升社交权重","desc":"增加与同赛道优质账号的互动频率，评论/合拍提升曝光","priority":"high","color":"#ff4d4f"},
                {"title":"尝试系列化/栏目化运营","desc":"打造固定栏目形成用户追更习惯","priority":"medium","color":"#faad14"},
                {"title":"加强评论区互动","desc":"发布后1小时内回复前20条评论","priority":"medium","color":"#faad14"},
                {"title":"考虑直播联动","desc":"定期直播解说热门游戏快速拉高粉丝粘性","priority":"low","color":"#1890ff"},
            ]
        elif did == "58501769370":
            opt_list = [
                {"title":"提升封面吸引力","desc":"当前点赞率0.78%偏低，优化封面设计目标提升至1%+","priority":"high","color":"#ff4d4f"},
                {"title":"增加热点追踪频次","desc":"赛事/版本更新时12小时内出内容借势热点获取流量","priority":"high","color":"#ff4d4f"},
                {"title":"建立固定栏目品牌","desc":"打造「牛马攻略」等品牌栏目形成记忆点","priority":"medium","color":"#faad14"},
                {"title":"加强与粉丝评论互动","desc":"发布后积极回复评论引导讨论","priority":"medium","color":"#faad14"},
                {"title":"尝试与其他账号联动","desc":"与头部游戏号互推或合拍交叉引流","priority":"low","color":"#1890ff"},
            ]
        elif did == "ming99888899":
            opt_list = [
                {"title":"稳定核心品类占比","desc":"70%聚焦1-2个主赛道30%做泛内容稳定算法推荐","priority":"high","color":"#ff4d4f"},
                {"title":"发挥评论优势","desc":"评论率0.22%最高！多设置槽点和争议话题引导讨论","priority":"high","color":"#ff4d4f"},
                {"title":"统一更新时间","desc":"选择晚8-10点高峰期固定发布培养用户习惯","priority":"medium","color":"#faad14"},
                {"title":"制作合集/系列内容","desc":"将零散内容整理为系列合集提升追更率","priority":"medium","color":"#faad14"},
                {"title":"适度参与挑战赛","desc":"加入抖音官方游戏挑战赛蹭平台流量红利","priority":"low","color":"#1890ff"},
            ]
        elif did == "TikTokxy123":
            opt_list = [
                {"title":"提升标题点击率CTR","desc":"优化标题：数字+悬念+痛点关键词组合目标CTR翻倍","priority":"high","color":"#ff4d4f"},
                {"title":"紧跟热门手游版本更新","desc":"新角色/新赛季48小时内出攻略教程抢占搜索流量","priority":"high","color":"#ff4d4f"},
                {"title":"增加短视频形式","desc":"60秒内快节奏攻略降低观看门槛","priority":"medium","color":"#faad14"},
                {"title":"优化SEO关键词覆盖","desc":"覆盖游戏名+角色名+玩法关键词提升搜索排名","priority":"medium","color":"#faad14"},
                {"title":"与同类手游博主互推","desc":"寻找同量级博主互相推荐共享粉丝池","priority":"low","color":"#1890ff"},
            ]
        elif did == "520panchun":
            opt_list = [
                {"title":"保持当前更新节奏并加速","desc":"从1条恢复到5条是好开始尽快提升至每周3-5条","priority":"high","color":"#ff4d4f"},
                {"title":"保持资讯类快反节奏","desc":"游戏圈大新闻12小时内出解读/盘点内容","priority":"high","color":"#ff4d4f"},
                {"title":"建立固定栏目品牌","desc":"打造「有料盘点」「新游速递」系列栏目","priority":"medium","color":"#faad14"},
                {"title":"学习对标账号爆款逻辑","desc":"研究同赛道10w+播放的视频结构和套路","priority":"medium","color":"#faad14"},
                {"title":"考虑与其他4个账号联动互推","desc":"合作互推或合拍快速恢复流量","priority":"low","color":"#1890ff"},
            ]
        entry["optimization"] = opt_list

        accounts_js.append(entry)

        has_av = "YES" if avatar_url else "NO "
        print("  OK {}: avatar={} fans={} likes={} videos={}".format(
            entry["name"].ljust(8), has_av,
            str(entry["fans"]).ljust(6), str(entry["totalLikes"]).ljust(6),
            str(entry["videos"]).ljust(4)))

    return accounts_js, total_videos_int, today_str


def update_html(html_content, accounts_data, total_videos, today):
    accounts_json = json.dumps(accounts_data, ensure_ascii=False, indent=4)

    new_html = re.sub(
        r'const accountsData\s*=\s*\[[\s\S]*?\];',
        'const accountsData = {};'.format(accounts_json),
        html_content
    )

    # 更新日期标记
    new_html = re.sub(r'\d{4}-\d{2}-\d{2}(?=\s*[|>])', today, new_html)

    # 更新总作品数
    vid_m = re.search(r'>\s*(\d+)\s*条<', new_html)
    if vid_m:
        old_count = vid_m.group(1)
        new_html = new_html.replace(">{} 条<".format(old_count), ">{} 条<".format(total_videos))
        print("  总作品数: {} -> {}".format(old_count, total_videos))

    # 更新注释
    new_html = re.sub(
        r'// 数据来源:.*',
        '// 数据来源: {} 通过抖音主页实时采集（已登录状态）'.format(today),
        new_html
    )

    return new_html


def main():
    print("=" * 55)
    print("  数据同步工具: 采集结果 -> HTML仪表板")
    print("=" * 55)

    scrape_data = load_scrape_results()
    if not scrape_data:
        return False

    html = load_html()
    if not html:
        return False

    print("\n转换数据格式...")
    accounts_data, total_videos, today_str = build_account_data(scrape_data)

    if not accounts_data:
        print("ERROR: 没有有效数据")
        return False

    # 头像检查
    has_avatar_count = sum(1 for a in accounts_data if a.get("avatarUrl"))
    print("\n头像状态: {}/{} 有真实头像URL".format(has_avatar_count, len(accounts_data)))
    if has_avatar_count < len(accounts_data):
        missing_names = [a["name"] for a in accounts_data if not a.get("avatarUrl")]
        print("  缺失头像: {}".format(", ".join(missing_names)))

    print("\n更新 HTML... (日期: {})".format(today_str))
    new_html = update_html(html, accounts_data, total_videos, today_str)

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(new_html)

    print("\n" + "=" * 55)
    print("  同步完成!")
    print("  文件: {}".format(HTML_FILE.name))
    print("  日期: {}".format(today_str))
    print("  真实头像: {}/{}".format(has_avatar_count, len(accounts_data)))
    print("=" * 55)
    return True


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
