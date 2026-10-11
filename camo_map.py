"""用 data-canonical-src 建立 camo↔原图 映射，判定各服务在 GitHub 侧的真实可用性。

GitHub 渲染外链图时写 <img src="camo..." data-canonical-src="原URL">，
据此可精确知道每条 camo 对应哪个服务、以及抓取成功(200)还是失败(404/502)。
这是唯一能区分「本机网络不通」与「服务真死」的证据。
"""
import re, subprocess, sys
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

PAGES = [
    ("qiqqqqq517(我方)", "https://github.com/qiqqqqq517"),
    ("awesome-templates", "https://github.com/durgeshsamariya/awesome-github-profile-readme-templates"),
    ("anuraghazra", "https://github.com/anuraghazra"),
]

pairs = []
for label, url in PAGES:
    html = sh(["curl.exe","-s","-L","--max-time","30","-A","Mozilla/5.0",url])
    # <img ... src="camo..." ... data-canonical-src="原图">
    found = re.findall(
        r'<img[^>]+src="(https://camo\.githubusercontent\.com/[^"]+)"[^>]*?data-canonical-src="([^"]+)"',
        html)
    found += re.findall(
        r'<img[^>]+data-canonical-src="([^"]+)"[^>]*?src="(https://camo\.githubusercontent\.com/[^"]+)"',
        html)
    print("=== %s : %d 条 camo↔原图 ===" % (label, len(found)))
    for a, b in found:
        camo, orig = (a, b) if "camo" in a else (b, a)
        pairs.append((camo, orig))

print("\n%-46s %-12s %s" % ("原图（服务）", "camo状态", "主机"))
print("-" * 96)
seen = set()
for camo, orig in pairs:
    if orig in seen:
        continue
    seen.add(orig)
    host = re.match(r"https?://([^/]+)", orig)
    host = host.group(1) if host else "?"
    st = status(camo)
    mark = "✅" if st.startswith("200") else "❌"
    print("%-46s %-12s %s %s" % (orig[:44], st, host, mark))
