"""整体优化前：实测各徽章/统计服务的可用性。

目的：找出能真正渲染的功能块（奖杯墙、语言统计、活动图、访客数等），
     以及每个服务的替代源。判据用「下载字节数 + 是否为有效图片/SVG」，
     不用 HTTP 200 —— 该服务族对坏参数也返回 200（已实测）。
"""
import os, re, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")

OUT = r"D:\DSH\DSH Desktop\gh_profile_opt\_svc"
os.makedirs(OUT, exist_ok=True)
U = "qiqqqqq517"

CANDS = [
    # 奖杯墙（参考对象用的那个已挂）
    ("trophy_原版vercel", "https://github-profile-trophy-tawny.vercel.app/?username=%s&theme=onedark&column=7" % U),
    ("trophy_官方",      "https://github-profile-trophy.vercel.app/?username=%s&theme=onedark&column=7" % U),
    ("trophy_heroku",    "https://github-profile-trophy.herokuapp.com/?username=%s&theme=onedark&column=7" % U),
    # 语言统计
    ("langs_vercel",     "https://github-readme-stats.vercel.app/api/top-langs/?username=%s&layout=compact&theme=dark" % U),
    ("langs_demolab",    "https://github-readme-stats-demolab.vercel.app/api/top-langs/?username=%s&layout=compact&theme=dark" % U),
    # 活动图
    ("activity_heroku",  "https://github-readme-activity-graph.vercel.app/graph?username=%s&theme=github-compact" % U),
    ("activity_demolab", "https://github-readme-activity-graph-demolab.vercel.app/graph?username=%s&theme=github-compact" % U),
    # 已确认可用
    ("streak_demolab",   "https://streak-stats.demolab.com?user=%s&theme=dark&hide_border=true" % U),
    ("ossinsight",       "https://next.ossinsight.io/widgets/official/compose-user-dashboard-stats/thumbnail.png?user_id=266937129&image_size=auto&color_scheme=dark"),
    # 访客计数
    ("views_komarev",    "https://komarev.com/ghpvc/?username=%s&label=Profile+views&color=0e75b6&style=flat" % U),
    # 常用补充
    ("followers_shields", "https://img.shields.io/github/followers/%s?label=Followers&style=flat&color=0e75b6" % U),
    ("stars_shields",     "https://img.shields.io/github/stars/%s?label=Stars&style=flat&color=0e75b6" % U),
]

def probe(url, path):
    """返回 (状态码, 字节数, 类型判断)"""
    code = "000"
    for _ in range(3):
        r = subprocess.run(["curl.exe","-s","-o",path,"-w","%{http_code}","-L",
                            "--max-time","25","-A","Mozilla/5.0",url], capture_output=True)
        code = r.stdout.decode("utf-8","replace").strip() or "000"
        if code == "200":
            break
    if code != "200" or not os.path.exists(path):
        return code, 0, "-"
    n = os.path.getsize(path)
    head = open(path, "rb").read(8)
    if head.startswith(b"\x89PNG"):   kind = "PNG"
    elif head.startswith(b"<svg") or b"<svg" in open(path,"rb").read(400):
        kind = "SVG"
    elif head.startswith(b"\xff\xd8"): kind = "JPEG"
    elif head.startswith(b"<"):        kind = "HTML/错误页"
    else:                              kind = "未知:%r" % head[:6]
    # SVG 里若含 error 文案，也算失败
    if kind == "SVG":
        txt = open(path, encoding="utf-8", errors="replace").read()
        if re.search(r"(Something went wrong|Not Found|error)", txt, re.I):
            kind = "SVG(错误内容)"
    return code, n, kind

print("%-20s %-6s %-9s %s" % ("服务", "状态", "字节", "类型"))
print("-" * 60)
ok = []
for name, url in CANDS:
    p = os.path.join(OUT, name + ".bin")
    c, n, k = probe(url, p)
    flag = "✅" if (c == "200" and n > 500 and k in ("PNG","SVG","JPEG")) else "❌"
    if flag == "✅": ok.append(name)
    print("%-20s %-6s %-9s %s %s" % (name, c, n, k, flag))

print("\n可用服务: %s" % ", ".join(ok))