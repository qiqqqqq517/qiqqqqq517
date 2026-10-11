"""644 能不能着重展示？先验证它站得住。

三个口径冲突：
  streak 卡合计贡献 = 644   （第三方服务自算，含 commit+PR+issue+review）
  主页 Contribution activity = 689 （GitHub 算，近一年窗口）
  search/commits = 571      （仅 commit）

做法：重新拉一次 streak 卡确认现值；再用 API 逐项累加尝试对账 644。
对不上就如实标注口径，不硬凑。
"""
import json, re, subprocess, sys, os
sys.stdout.reconfigure(encoding="utf-8")

def sh(*a):
    r = subprocess.run(a, capture_output=True)
    return r.returncode, r.stdout.decode("utf-8","replace"), r.stderr.decode("utf-8","replace")

def api(path):
    rc, out, err = sh("gh","api",path)
    return json.loads(out) if rc == 0 else None

print("=== 1. streak 卡现值 ===")
OUT = r"D:\DSH\DSH Desktop\gh_profile_opt\_fmt\live.svg"
os.makedirs(os.path.dirname(OUT), exist_ok=True)
URL = ("https://streak-stats.demolab.com?user=qiqqqqq517&theme=dark"
       "&hide_border=true&locale=zh_Hans"
       "&date_format=%5BY%E5%B9%B4%5Dn%E6%9C%88j%E6%97%A5")
code = "000"
for _ in range(3):
    rc, out, err = sh("curl.exe","-s","-o",OUT,"-w","%{http_code}","-L",
                      "--max-time","30","-A","Mozilla/5.0",URL)
    code = out.strip() or "000"
    if code == "200": break
if code == "200":
    svg = open(OUT, encoding="utf-8", errors="replace").read()
    t = [re.sub(r"<[^>]+>","",x).strip() for x in re.findall(r"<text[^>]*>(.*?)</text>",svg,re.S)]
    t = [c for c in t if c]
    print("  渲染文本: %s" % " | ".join(t))
    m = re.search(r"(\d+)\s*\|\s*合计贡献", " | ".join(t))
    print("  合计贡献 = %s" % (m.group(1) if m else "未解析到"))
else:
    print("  HTTP %s" % code)

print("\n=== 2. API 逐项累加对账 ===")
commits = api("search/commits?q=author:qiqqqqq517&per_page=1")
prs     = api("search/issues?q=author:qiqqqqq517+type:pr&per_page=1")
issues  = api("search/issues?q=author:qiqqqqq517+type:issue&per_page=1")
revs    = api("search/issues?q=reviewer:qiqqqqq517+type:pr&per_page=1")
rows = [("commit(作者)",  commits["total_count"] if commits else None),
        ("PR(作者)",      prs["total_count"]     if prs     else None),
        ("Issue(作者)",   issues["total_count"]  if issues  else None),
        ("PR review(审阅)", revs["total_count"]  if revs    else None)]
for name, v in rows:
    print("  %-18s %s" % (name, v))
known = [v for _, v in rows if v is not None]
if known:
    print("  %-18s %d" % ("可累加小计", sum(known)))

print("\n=== 3. 结论 ===")
print("  644 无法由上述公开 API 精确复现（含 fork 上游提交与 review 细节，服务算法不公开）。")
print("  处理方式：README 标注为「合计贡献」并注明来源为 streak 卡，不冒充可核数字。")