"""profile README 自检 v3（整体优化后）。

判据：
 1. 个人信息片段零命中。
 2. 仓库引用只允许自有仓库 —— fork 必须零出现。
 3. README 声明的 star 数与线上 API 实测一致（无任何声明时 SKIP，不得算 PASS）。
 4. 顶部汇总五项数字与线上实测一致。
 5. 顶部大字 = streak 卡实时实测值；streak 必须带 date_format。
 6. 结构：主推项目唯一（1 个带截图的主力区块）+ 其他项目降级为小表。
 7. 功能模块在位（语言统计图 / 访客计数）。
 8. 外链可达。本机代理不通但 GitHub 侧可用的服务单独归类（见 camo_verify.py）。
 9. 阴性对照：PII / fork / 大字篡改 三类都必须被判 FAIL。

退出码：0 = 全过；1 = 命中缺陷；2 = 拒判（量具自身失效）。
"""
import json, os, re, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")

PATH = r"D:\DSH\DSH Desktop\gh_profile_opt\README.md"
text = open(PATH, encoding="utf-8").read()
lines = text.splitlines()

def gh(*a):
    r = subprocess.run(["gh"]+list(a), capture_output=True)
    return json.loads(r.stdout.decode("utf-8")) if r.returncode == 0 else None

repos = gh("api", "users/qiqqqqq517/repos?per_page=100")
if not repos:
    print("拒判：GitHub API 不可用，无法取得基准"); sys.exit(2)

FORK_NAMES = {x["name"] for x in repos if x["fork"]}
OWN_NAMES  = {x["name"] for x in repos if not x["fork"] and not x["archived"]}
STARS      = {x["name"]: x["stargazers_count"] for x in repos}
u = gh("api", "users/qiqqqqq517")
own_all = [x for x in repos if not x["fork"] and not x["archived"]]
langs = sorted({x["language"] for x in own_all if x["language"]})

# 本机代理会挡、但已用 camo 实测 GitHub 侧 200 的服务（不在此列的一律按 FAIL 处理）
CAMO_OK = {"github-readme-stats.vercel.app"}

fails, skips = [], []

print("=== 判据1：个人信息 ===")
for b in ["南通","大学","机械","智能制造","2025","涌淇","本科","大四","学院"]:
    n = text.count(b)
    if n: fails.append("PII:%s" % b)
    print("  %-4s %-8s 命中 %d" % ("PASS" if n==0 else "FAIL", b, n))

print("\n=== 判据2：只列自有仓库（fork 必须零出现）===")
found = set(re.findall(r"github\.com/qiqqqqq517/([A-Za-z0-9._-]+)", text))
found.discard("")
fork_hit = found & FORK_NAMES
extra    = found - OWN_NAMES - FORK_NAMES
print("  自有: %s" % sorted(OWN_NAMES))
print("  fork: %s" % sorted(FORK_NAMES))
print("  引用: %s" % sorted(found))
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
    print("  PASS 自有仓库均已出现")

print("\n=== 判据3：star 数与线上实测一致 ===")
declared = 0
for name in sorted(found & OWN_NAMES):
    # 在该仓库引用所在行 ±10 行窗口内找 ★N
    idxs = [i for i, l in enumerate(lines) if "qiqqqqq517/%s" % name in l]
    win = ""
    for i in idxs:
        win += "\n".join(lines[max(0, i-1): i+11])
    m = re.search(r"★\s*(\d+)", win)
    if not m:
        print("  INFO %-16s 线上 %d star，README 未标注" % (name, STARS[name]))
        continue
    declared += 1
    decl = int(m.group(1)); real = STARS[name]
    ok = decl == real
    if not ok: fails.append("STAR_DRIFT:%s declared=%d real=%d" % (name, decl, real))
    print("  %-4s %-16s 声明★%d 实测%d" % ("PASS" if ok else "FAIL", name, decl, real))
if declared == 0:
    skips.append("STAR_DECL_NONE")
    print("  SKIP 全文无任何 star 声明 —— 本项未判定（空比较不算通过）")

print("\n=== 判据4：顶部汇总五项与线上实测一致 ===")
ROW_RE = (r"\|\s*\*\*(\d+)\*\*\s*\|\s*\*\*(\d+)\*\*\s*\|\s*(\d+)\s*\|"
          r"\s*(\d+)\s*种\s*\|\s*\*\*(\d+)\*\*\s*\|")
mrow = re.search(ROW_RE, text)
real_prs = json.loads(subprocess.run(
    ["gh","api","search/issues?q=author:qiqqqqq517+type:pr&per_page=1"],
    capture_output=True).stdout.decode("utf-8"))["total_count"]
if not mrow:
    fails.append("SUMMARY_ROW_MISSING")
    print("  FAIL 顶部汇总表未解析到")
else:
    d_repo, d_star, d_fork, d_lang, d_pr = [int(x) for x in mrow.groups()]
    for label, decl, real in [("公开仓库", d_repo, u["public_repos"]),
                              ("star合计", d_star, sum(x["stargazers_count"] for x in own_all)),
                              ("fork合计", d_fork, sum(x["forks_count"] for x in own_all)),
                              ("语言数", d_lang, len(langs)),
                              ("PR数", d_pr, real_prs)]:
        ok = decl == real
        if not ok: fails.append("SUMMARY_DRIFT:%s declared=%d real=%d" % (label, decl, real))
        print("  %-4s %-8s 声明=%-4d 实测=%d" % ("PASS" if ok else "FAIL", label, decl, real))

print("\n=== 判据5：顶部大字 = streak 实测；streak 带 date_format ===")
BIG_RE = re.compile(r"^#\s*(\d+)\s*次贡献\s*·\s*(\d+)\s*天最长连续\s*$", re.M)
bm = BIG_RE.search(text)
LIVE = os.path.join(os.path.dirname(PATH), "_fmt", "live.svg")
if not bm:
    fails.append("BIGSTAT_MISSING")
    print("  FAIL 顶部大字未解析到")
elif not os.path.exists(LIVE):
    skips.append("STREAK_LIVE_MISSING")
    print("  SKIP streak 实时图缺失（先跑 verify_644.py），本项未判定")
    print("       大字声明: %s 次贡献 / %s 天最长" % (bm.group(1), bm.group(2)))
else:
    svg = open(LIVE, encoding="utf-8", errors="replace").read()
    tt = " | ".join(re.sub(r"<[^>]+>", "", x).strip()
                    for x in re.findall(r"<text[^>]*>(.*?)</text>", svg, re.S))
    cm2 = re.search(r"(\d+)\s*\|\s*合计贡献", tt)
    lm = re.search(r"\|\s*(\d+)\s*\|\s*最长连续贡献", tt)
    for label, decl, real in [("合计贡献", int(bm.group(1)), int(cm2.group(1)) if cm2 else -1),
                              ("最长连续", int(bm.group(2)), int(lm.group(1)) if lm else -1)]:
        ok = real != -1 and decl == real
        if not ok: fails.append("BIGSTAT_DRIFT:%s declared=%d real=%d" % (label, decl, real))
        print("  %-4s %-8s 大字=%-4d streak实测=%s" %
              ("PASS" if ok else "FAIL", label, decl, real if real != -1 else "解析失败"))

sm = re.search(r"streak-stats\.demolab\.com\?([^\s)]+)", text)
if sm:
    ok = "date_format=" in sm.group(1)
    if not ok: fails.append("STREAK_NO_DATEFMT")
    print("  %-4s %-8s %s" % ("PASS" if ok else "FAIL", "streak格式",
          "带 date_format" if ok else "缺 date_format ⇒ 日期只剩月份"))

print("\n=== 判据6：结构（主推唯一 + 其他降级）===")
h2 = [l for l in lines if l.startswith("## ")]
print("  H2 区块 %d 个: %s" % (len(h2), [h[:34] for h in h2]))
# 主推区块 = 含 shangkeschedule 且含截图的 H2
main_blocks = [h for h in h2 if "shangkeschedule" in h.lower()]
if len(main_blocks) != 1:
    fails.append("MAIN_BLOCK_COUNT:%d" % len(main_blocks))
    print("  FAIL 主推项目区块数应为 1，实际 %d" % len(main_blocks))
else:
    print("  PASS 主推项目唯一: %s" % main_blocks[0][:40])
# 其他项目区块必须是小表（无截图）
other_idx = [i for i, l in enumerate(lines) if l.startswith("## ") and "其他项目" in l]
if not other_idx:
    fails.append("OTHER_SECTION_MISSING")
    print("  FAIL 缺少「其他项目」区块")
else:
    oi = other_idx[0]
    nxt = next((j for j in range(oi+1, len(lines)) if lines[j].startswith("## ")), len(lines))
    seg = "\n".join(lines[oi:nxt])
    has_img = bool(re.search(r"<img|!\[", seg))
    rows = len([l for l in seg.splitlines() if l.startswith("|")]) - 2  # 去掉表头+分隔
    ok = (not has_img) and 0 < rows <= 4
    if not ok: fails.append("OTHER_NOT_COMPACT:img=%s rows=%d" % (has_img, rows))
    print("  %-4s 其他项目: %d 行、无截图=%s（应为小字表格）" %
          ("PASS" if ok else "FAIL", rows, not has_img))

print("\n=== 判据7：功能模块在位 ===")
MODULES = [("语言统计图", "github-readme-stats.vercel.app/api/top-langs"),
           ("访客计数",   "komarev.com/ghpvc"),
           ("streak 卡",  "streak-stats.demolab.com"),
           ("ossinsight", "next.ossinsight.io/widgets")]
for label, needle in MODULES:
    ok = needle in text
    if not ok: fails.append("MODULE_MISSING:%s" % label)
    print("  %-4s %-10s %s" % ("PASS" if ok else "FAIL", label, needle))

print("\n=== 判据8：外链可达 ===")
urls = sorted(set(re.findall(r'https?://[^\s)"\'<>]+', text)))
for url in urls:
    host = re.match(r"https?://([^/]+)", url)
    host = host.group(1) if host else ""
    codes = []
    for _ in range(3):
        r = subprocess.run(["curl.exe","-s","-o","NUL","-w","%{http_code}","-L",
                            "--max-time","20","-A","Mozilla/5.0",url], capture_output=True)
        c = r.stdout.decode("utf-8","replace").strip() or "000"
        codes.append(c)
        if c in ("200","403"): break
    if codes[-1] in ("200","403"):
        print("  PASS %-10s %s" % (codes[-1], url[:88])); continue
    if host in CAMO_OK:
        print("  INFO 本机不可达 %s（该服务经 camo 实测 GitHub 侧 200 可用）" % host)
        continue
    fails.append("URL:%s %s" % (url, codes))
    print("  FAIL %-10s %s" % (",".join(codes), url[:88]))

print("\n=== 判据9：阴性对照 ===")
s = text + "\n\n毕业于南通大学机械工程学院智能制造工程 2025 级\n[hypo](https://github.com/qiqqqqq517/HypoMux)\n"
p = [b for b in ["南通","大学","机械","2025"] if b in s]
fk = set(re.findall(r"github\.com/qiqqqqq517/([A-Za-z0-9._-]+)", s)) & FORK_NAMES
print("  构造样本 PII 命中: %s" % p)
print("  构造样本 fork 命中: %s" % sorted(fk))
if not p: fails.append("NEGCTRL_PII")
if not fk: fails.append("NEGCTRL_FORK")
print("  %s 判据对 PII 与 fork 均有效" % ("PASS" if p and fk else "FAIL"))

if os.path.exists(LIVE):
    svg = open(LIVE, encoding="utf-8", errors="replace").read()
    tt = " | ".join(re.sub(r"<[^>]+>", "", x).strip()
                    for x in re.findall(r"<text[^>]*>(.*?)</text>", svg, re.S))
    cm3 = re.search(r"(\d+)\s*\|\s*合计贡献", tt)
    real_total = int(cm3.group(1)) if cm3 else 644
    tampered = text.replace("# %d 次贡献" % real_total, "# 999 次贡献")
    tm = BIG_RE.search(tampered)
    caught = (tm is not None) and (int(tm.group(1)) == 999) and (real_total != 999)
    if not caught: fails.append("NEGCTRL_BIGSTAT")
    print("  %s 大字判据：篡改成 999 后%s被检出" %
          ("PASS" if caught else "FAIL", "" if caught else "未被"))

# 结构判据的阴性对照：把主推项目复制成两份，必须被判 FAIL
dup = text.replace("## 🛠️ 其他项目", "## 📅 [上课 · ShangKeSchedule](https://github.com/qiqqqqq517/shangkeschedule)\n\n## 🛠️ 其他项目")
dup_h2 = [l for l in dup.splitlines() if l.startswith("## ")]
dup_main = [h for h in dup_h2 if "shangkeschedule" in h.lower()]
caught2 = len(dup_main) != 1
if not caught2: fails.append("NEGCTRL_STRUCT")
print("  %s 结构判据：主推区块复制成 2 份后%s被检出" %
      ("PASS" if caught2 else "FAIL", "" if caught2 else "未被"))

print("\nVERDICT:", "ALL PASS" if not fails else "FAIL -> %s" % fails)
if skips: print("SKIPPED:", skips)
sys.exit(0 if not fails else 1)
