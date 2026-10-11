"""整体优化取证：① camo 可达性（本机不通≠GitHub 抓不到）② 仓库界面现状盘点。"""
import json, re, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")

def curl(url, extra=None):
    cmd = ["curl.exe","-s","-L","--max-time","30","-A","Mozilla/5.0"] + (extra or []) + [url]
    r = subprocess.run(cmd, capture_output=True)
    return r.returncode, r.stdout

def gh(*a):
    r = subprocess.run(["gh"] + list(a), capture_output=True)
    return json.loads(r.stdout.decode("utf-8")) if r.returncode == 0 else None

print("=== ① camo 可达性测试（用参考对象页面反查 GitHub 侧能否抓到）===")
rc, body = curl("https://github.com/Lvshujun0918")
html = body.decode("utf-8", "replace")
print("  参考页 HTML 长度: %d" % len(html))
camos = re.findall(r'https://camo\.githubusercontent\.com/[0-9a-f]{8,}/[0-9a-f]{8,}(?:/[^\s"\'<>]*)?', html)
camos = list(dict.fromkeys(camos))
print("  camo 链接数: %d" % len(camos))
# 逐条抓 camo，看 GitHub 侧是否拿到了真图
for c in camos[:6]:
    rc2, b2 = curl(c, ["-o","NUL","-w","%{http_code} %{size_download}"])
    print("    %s  -> %s" % (c[:78], b2.decode("utf-8","replace").strip()))
# 直接看 README 里出现的图床域名，判断哪些真被 GitHub 渲染
hosts = sorted(set(re.findall(r'https?://([a-z0-9.\-]+)/[^\s"\'<>)]*\.(?:png|svg|jpg|jpeg|gif)', html, re.I)))
print("  页面内出现的图床域名: %s" % hosts)

print("\n=== ② 仓库界面现状盘点 ===")
repos = gh("api", "users/qiqqqqq517/repos?per_page=100&sort=updated") or []
own = [x for x in repos if not x["fork"] and not x["archived"]]
for r in sorted(own, key=lambda x: -x["stargazers_count"]):
    print("  %-18s ★%-3d 描述=%s" % (r["name"], r["stargazers_count"],
          ("有(%d字)" % len(r["description"])) if r["description"] else "【空】"))
    print("        topics=%s  homepage=%s  license=%s  has_issues=%s" % (
        r.get("topics") or "【无】", r.get("homepage") or "【无】",
        (r.get("license") or {}).get("spdx_id") or "【无】", r.get("has_issues")))

print("\n=== ③ 当前主页渲染出的图床（判断哪些真在渲染）===")
rc, body2 = curl("https://github.com/qiqqqqq517")
h2 = body2.decode("utf-8", "replace")
print("  页面 HTML 长度: %d" % len(h2))
hosts2 = sorted(set(re.findall(r'https?://([a-z0-9.\-]+)/[^\s"\'<>)]*\.(?:png|svg|jpg|jpeg|gif)', h2, re.I)))
print("  图床域名: %s" % hosts2)
print("  含 streak-stats: %s | 含 ossinsight: %s | 含 komarev: %s" % (
    "streak-stats" in h2, "ossinsight" in h2, "komarev" in h2))