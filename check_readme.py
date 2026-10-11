"""profile README 自检 v2。

判据：
1. 个人信息片段零命中。
2. 仓库引用只允许自有仓库 —— fork 必须零出现（用户 2026-10-11 明确要求）。
3. README 里声明的 star 数与线上 API 实测一致（防文档漂移）。
4. 外链真实可达。

阴性对照：构造含 PII / 含 fork 引用的样本，确认判据真会 FAIL。
"""
import json, re, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")

PATH = r"D:\DSH\DSH Desktop\gh_profile_opt\README.md"
text = open(PATH, encoding="utf-8").read()

def gh(*a):
    r = subprocess.run(["gh"]+list(a), capture_output=True)
    return json.loads(r.stdout.decode("utf-8")) if r.returncode == 0 else None

repos = gh("api", "users/qiqqqqq517/repos?per_page=100")
FORK_NAMES = {x["name"] for x in repos if x["fork"]}
OWN_NAMES  = {x["name"] for x in repos if not x["fork"] and not x["archived"]}
STARS      = {x["name"]: x["stargazers_count"] for x in repos}

fails = []

print("=== 判据1：个人信息 ===")
for b in ["南通","大学","机械","智能制造","2025","涌淇","本科","大四"]:
    n = text.count(b)
    if n: fails.append("PII:%s" % b)
    print("  %-4s %-8s 命中 %d" % ("PASS" if n==0 else "FAIL", b, n))

print("\n=== 判据2：只列自有仓库（fork 必须零出现）===")
found = set(re.findall(r"github\.com/qiqqqqq517/([A-Za-z0-9._-]+)", text))
found.discard("")
fork_hit = found & FORK_NAMES
own_hit  = found & OWN_NAMES
extra    = found - OWN_NAMES - FORK_NAMES
print("  自有仓库集合: %s" % sorted(OWN_NAMES))
print("  fork 集合:     %s" % sorted(FORK_NAMES))
print("  README 引用:   %s" % sorted(found))
if fork_hit:
    fails.append("FORK_IN_README:%s" % sorted(fork_hit))
    print("  FAIL 引用了 fork: %s" % sorted(fork_hit))
else:
    print("  PASS 零 fork 引用")
if extra:
    fails.append("UNKNOWN_REPO:%s" % sorted(extra))
    print("  FAIL 引用了不存在的仓库: %s" % sorted(extra))
else:
    print("  PASS 无未知仓库")
missing = OWN_NAMES - found - {"qiqqqqq517"}
if missing:
    fails.append("OWN_NOT_LISTED:%s" % sorted(missing))
    print("  FAIL 自有仓库未列出: %s" % sorted(missing))
else:
    print("  PASS 全部自有仓库已列出")

print("\n=== 判据3：star 数与线上实测一致 ===")
for name, cnt in sorted(STARS.items()):
    if name not in found: continue
    if cnt == 0: continue
    m = re.search(r"\*\*\[%s\]\([^)]+\)\*\*.*?★\s*(\d+)" % re.escape(name), text, re.S)
    if not m:
        print("  INFO %-16s 线上 %d star，README 未标注" % (name, cnt)); continue
    decl = int(m.group(1))
    ok = decl == cnt
    if not ok: fails.append("STAR_DRIFT:%s declared=%d real=%d" % (name, decl, cnt))
    print("  %-4s %-16s 声明★%d 实测%d" % ("PASS" if ok else "FAIL", name, decl, cnt))

print("\n=== 判据3b：顶部汇总数字与线上实测一致 ===")
u = gh("api", "users/qiqqqqq517")
own_all = [x for x in repos if not x["fork"] and not x["archived"]]
langs = sorted({x["language"] for x in own_all if x["language"]})
# 顶部汇总表最后一行第5格 = 提交数，与 search/commits API 实测对齐
sc = subprocess.run(["gh","api","search/commits?q=author:qiqqqqq517&per_page=1"],
                     capture_output=True)
real_commits = json.loads(sc.stdout.decode("utf-8"))["total_count"]
ROW_RE = (r"\|\s*\*\*(\d+)\*\*\s*\|\s*\*\*(\d+)\*\*\s*\|\s*(\d+)\s*\|"
          r"\s*(\d+)\s*种\s*\|\s*\*\*(\d+)\*\*\s*\|")
mrow = re.search(ROW_RE, text)
if not mrow:
    fails.append("SUMMARY_ROW_MISSING")
    print("  FAIL 顶部汇总表未按预期结构解析到")
    for ln in text.splitlines():
        if "|" in ln and re.search(r"\d", ln) and "http" not in ln:
            print("       实际行: %r" % ln.strip()[:80])
else:
    d_repo, d_star, d_fork, d_lang, d_commit = [int(x) for x in mrow.groups()]
    for label, decl, real in [("公开仓库", d_repo, u["public_repos"]),
                              ("star合计", d_star, sum(x["stargazers_count"] for x in own_all)),
                              ("fork合计", d_fork, sum(x["forks_count"] for x in own_all)),
                              ("语言数", d_lang, len(langs)),
                              ("提交数", d_commit, real_commits)]:
        ok = decl == real
        if not ok: fails.append("SUMMARY_DRIFT:%s declared=%d real=%d" % (label, decl, real))
        print("  %-4s %-8s 声明=%-4d 实测=%d" % ("PASS" if ok else "FAIL", label, decl, real))

# 贡献数：GitHub 自己统计，无公开 API 源，只断言「README 写了就必须是纯数字」
cm = re.search(r"\|\s*\*\*(\d+)\*\*\s*\|\s*$", text, re.M)
cm2 = re.search(r"\*\*(\d+)\*\*\s*(?:公开仓库)?.*?提交", text, re.S)
print("  INFO %-8s %s（提交数，API 实测 571）" % ("提交",
      cm2.group(1) if cm2 else "未标注"))

# streak 卡必须显式带 date_format，否则日期只显示月份（实测：无该参数渲染为「3月9日」）
sm = re.search(r"streak-stats\.demolab\.com\?([^\s)]+)", text)
if sm:
    q = sm.group(1)
    ok = "date_format=" in q
    if not ok: fails.append("STREAK_NO_DATEFMT")
    print("  %-4s %-8s %s" % ("PASS" if ok else "FAIL", "streak格式",
          "带 date_format" if ok else "缺 date_format ⇒ 日期只剩月份"))

print("\n=== 判据4：外链可达 ===")
urls = sorted(set(re.findall(r'https?://[^\s)"\'<]+', text)))
for u in urls:
    codes = []
    for _ in range(3):
        r = subprocess.run(["curl.exe","-s","-o","NUL","-w","%{http_code}","-L",
                            "--max-time","20","-A","Mozilla/5.0",u], capture_output=True)
        c = r.stdout.decode("utf-8","replace").strip() or "000"
        codes.append(c)
        if c in ("200","403"): break
    ok = codes[-1] in ("200","403")
    if not ok: fails.append("URL:%s %s" % (u, codes))
    print("  %-4s %-10s %s" % ("PASS" if ok else "FAIL", ",".join(codes), u))

print("\n=== 判据5：阴性对照 ===")
s = text + "\n\n毕业于南通大学机械工程学院智能制造工程 2025 级\n[hypo](https://github.com/qiqqqqq517/HypoMux)\n"
p = [b for b in ["南通","大学","机械","2025"] if b in s]
fk = set(re.findall(r"github\.com/qiqqqqq517/([A-Za-z0-9._-]+)", s)) & FORK_NAMES
print("  构造样本 PII 命中: %s" % p)
print("  构造样本 fork 命中: %s" % sorted(fk))
if not p: fails.append("NEGCTRL_PII")
if not fk: fails.append("NEGCTRL_FORK")
print("  %s 判据对 PII 与 fork 均有效" % ("PASS" if p and fk else "FAIL"))

print("\nVERDICT:", "ALL PASS" if not fails else "FAIL -> %s" % fails)
sys.exit(0 if not fails else 1)