"""决定性测试：GitHub 侧（camo）能否抓到 github-readme-stats / trophy 徽章。

本机 curl 走代理，vercel.app 全 000 不能代表 GitHub 抓不到 —— 用 camo 反查才准：
README 外链图会被 GitHub 转成 camo 链接，上游抓取失败 → camo 404/502，成功 → 200。
"""
import base64, json, re, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")

def sh(args, t=30):
    try:
        r = subprocess.run(args, capture_output=True, timeout=t)
        return r.stdout.decode("utf-8", "replace")
    except Exception:
        return ""

def ghj(path):
    try:
        return json.loads(sh(["gh", "api", path]))
    except Exception:
        return None

def camo_status(u):
    s = ""
    for _ in range(3):
        s = sh(["curl.exe","-s","-o","NUL","-w","%{http_code} %{size_download}",
                "-L","--max-time","25","-A","Mozilla/5.0",u]).strip()
        if s and not s.startswith("000"):
            return s
    return s or "000 0"

print("=== A. 反查：用了 github-readme-stats 的 README，其 camo 状态 ===")
res = ghj("search/code?q=%22github-readme-stats.vercel.app%22+in:file+extension:md&per_page=6")
if not res or "items" not in res:
    print("  代码搜索不可用: %s" % str(res)[:200])
else:
    print("  命中 %d 个文件" % res.get("total_count", 0))
    for it in res["items"][:3]:
        repo = it["repository"]["full_name"]
        print("\n  --- %s ---" % repo)
        r = subprocess.run(["gh", "api", "repos/%s/readme" % repo], capture_output=True)
        if r.returncode != 0:
            print("    README 读取失败"); continue
        raw = base64.b64decode(json.loads(r.stdout.decode("utf-8"))["content"]).decode("utf-8")
        urls = list(dict.fromkeys(re.findall(
            r'https?://github-readme-stats\.vercel\.app/[^\s"\'<>)\]]+', raw)))
        print("    README 内该服务图 %d 张" % len(urls))
        html = sh(["curl.exe","-s","-L","--max-time","30","-A","Mozilla/5.0",
                   "https://github.com/%s" % repo])
        camos = list(dict.fromkeys(re.findall(
            r'https://camo\.githubusercontent\.com/[0-9a-f]{8,}/[0-9a-f]{8,}', html)))
        print("    渲染页 camo %d 条" % len(camos))
        for c in camos[:6]:
            print("      %s -> %s" % (c[:66], camo_status(c)))

print("\n=== B. 我方主页 camo（当前实际渲染的图）===")
html = sh(["curl.exe","-s","-L","--max-time","30","-A","Mozilla/5.0",
           "https://github.com/qiqqqqq517"])
camos = list(dict.fromkeys(re.findall(
    r'https://camo\.githubusercontent\.com/[0-9a-f]{8,}/[0-9a-f]{8,}', html)))
for c in camos:
    print("  %s -> %s" % (c[:70], camo_status(c)))