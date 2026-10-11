"""判定徽章服务「GitHub 侧」是否可用。

关键：本机 curl 走代理（Clash 7897），vercel.app 全 000 不能证明 GitHub 抓不到。
正解 = 用 camo 反查：GitHub 渲染 README 时把外链图转成 camo 链接，
上游抓取失败时 camo 返回 404，成功返回 200。

做法：取已知使用这些服务的作者的 profile，把「raw README 里的原图 URL」
与「渲染页里的 camo URL」按顺序配对，逐条测 camo 状态。
"""
import base64, json, re, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")

def curl_text(url):
    r = subprocess.run(["curl.exe","-s","-L","--max-time","30","-A","Mozilla/5.0",url],
                       capture_output=True)
    return r.stdout.decode("utf-8", "replace")

def curl_status(url):
    for _ in range(3):
        r = subprocess.run(["curl.exe","-s","-o","NUL","-w","%{http_code} %{size_download}",
                            "-L","--max-time","30","-A","Mozilla/5.0",url], capture_output=True)
        s = r.stdout.decode("utf-8","replace").strip()
        if s and not s.startswith("000"):
            return s
    return s or "000 0"

TARGETS = ["anuraghazra", "ryo-ma", "qiqqqqq517"]

for who in TARGETS:
    print("=" * 74)
    print("profile: %s" % who)
    # 1) raw README 里的图片 URL（按出现顺序）
    raw = ""
    r = subprocess.run(["gh","api","repos/%s/%s/readme"%(who,who)], capture_output=True)
    if r.returncode == 0:
        raw = base64.b64decode(json.loads(r.stdout.decode("utf-8"))["content"]).decode("utf-8")
    src = re.findall(r'https?://[^\s"\'<>)\]]+\.(?:png|svg|jpe?g|gif)', raw, re.I)
    src = [u for u in dict.fromkeys(src) if "camo" not in u]
    print("  raw README 图 %d 张" % len(src))
    for u in src[:8]:
        print("     %s" % u[:96])
    # 2) 渲染页里的 camo（按顺序）
    html = curl_text("https://github.com/%s" % who)
    camos = re.findall(r'https://camo\.githubusercontent\.com/[0-9a-f]{8,}/[0-9a-f]{8,}', html)
    camos = list(dict.fromkeys(camos))
    print("  渲染页 camo %d 条" % len(camos))
    for c in camos[:8]:
        print("     %s -> %s" % (c[:70], curl_status(c)))
