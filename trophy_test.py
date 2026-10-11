"""确认 trophy（奖杯墙）服务在 GitHub 侧的真实可用性。

已知：参考对象 Lvshujun0918 的 trophy camo = 404（GitHub 自己也抓不到）。
另找若干「README 里真的写了 trophy」的 profile 复核，避免单点结论。
判据：camo 状态 200=可用 / 404·502=不可用。
"""
import base64, json, re, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")

def sh(a, t=30):
    try:
        return subprocess.run(a, capture_output=True, timeout=t).stdout.decode("utf-8","replace")
    except Exception:
        return ""

def status(u):
    s = ""
    for _ in range(3):
        s = sh(["curl.exe","-s","-o","NUL","-w","%{http_code} %{size_download}",
                "-L","--max-time","25","-A","Mozilla/5.0",u]).strip()
        if s and not s.startswith("000"):
            return s
    return s or "000 0"

# 用代码搜索找 README 里含 trophy 的仓库
res = None
try:
    res = json.loads(sh(["gh","api",
        "search/code?q=%22github-profile-trophy%22+in:file+filename:README.md&per_page=8"]))
except Exception:
    pass

cands = []
if res and res.get("items"):
    for it in res["items"][:8]:
        cands.append(it["repository"]["full_name"])
print("候选仓库: %s" % cands)

for repo in cands:
    r = subprocess.run(["gh","api","repos/%s/readme"%repo], capture_output=True)
    if r.returncode != 0: continue
    raw = base64.b64decode(json.loads(r.stdout.decode("utf-8"))["content"]).decode("utf-8")
    if "trophy" not in raw: continue
    urls = list(dict.fromkeys(re.findall(
        r'https?://[^\s"\'<>)\]]*trophy[^\s"\'<>)\]]*', raw)))
    print("\n--- %s ---" % repo)
    print("  README trophy URL: %s" % [u[:88] for u in urls[:3]])
    html = sh(["curl.exe","-s","-L","--max-time","30","-A","Mozilla/5.0",
               "https://github.com/%s"%repo])
    pairs = re.findall(
        r'<img[^>]+src="(https://camo\.githubusercontent\.com/[^"]+)"[^>]*?data-canonical-src="([^"]+)"',
        html)
    hit = [(c,o) for c,o in pairs if "trophy" in o]
    if not hit:
        print("  渲染页未找到 trophy 的 camo（可能未渲染/被裁剪）")
    for c, o in hit[:3]:
        print("  %s\n     -> %s" % (o[:88], status(c)))
