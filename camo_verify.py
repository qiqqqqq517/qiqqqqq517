"""推送前验证：新加模块在 GitHub 侧（camo）是否真能渲染。

本机 curl 对 vercel.app 全 000（代理问题），不能据此判断。
方法：先把 README 推上去，再抓渲染页的 camo↔原图映射逐条验状态。
本脚本只做「推送后」的核验，推送由外层命令完成。
"""
import re, subprocess, sys, time
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

# camo 有缓存，推送后稍等再抓
time.sleep(6)
html = sh(["curl.exe","-s","-L","--max-time","40","-A","Mozilla/5.0",
           "https://github.com/qiqqqqq517"])
print("页面 HTML 长度: %d" % len(html))

pairs = re.findall(
    r'<img[^>]+src="(https://camo\.githubusercontent\.com/[^"]+)"[^>]*?data-canonical-src="([^"]+)"',
    html)
pairs += re.findall(
    r'<img[^>]+data-canonical-src="([^"]+)"[^>]*?src="(https://camo\.githubusercontent\.com/[^"]+)"',
    html)

EXPECT = ["streak-stats.demolab.com", "next.ossinsight.io",
          "github-readme-stats.vercel.app/api/top-langs",
          "komarev.com/ghpvc",
          "raw.githubusercontent.com/qiqqqqq517/shangkeschedule"]

print("\n%-56s %-12s %s" % ("原图", "camo状态", ""))
print("-" * 92)
seen, got = set(), []
for a, b in pairs:
    camo, orig = (a, b) if "camo" in a else (b, a)
    if orig in seen: continue
    seen.add(orig)
    st = status(camo)
    mark = "✅" if st.startswith("200") else "❌"
    print("%-56s %-12s %s" % (orig[:54], st, mark))
    got.append((orig, st))

print("\n=== 逐模块判定 ===")
fails = []
for want in EXPECT:
    hit = [(o, s) for o, s in got if want in o]
    if not hit:
        print("  ❌ %-46s 未出现在渲染页（图未渲染）" % want)
        fails.append(want); continue
    o, s = hit[0]
    ok = s.startswith("200")
    if not ok: fails.append(want)
    print("  %s %-46s camo=%s" % ("✅" if ok else "❌", want, s))

print("\nVERDICT:", "ALL PASS" if not fails else "FAIL -> %s" % fails)
sys.exit(0 if not fails else 1)
