"""整体优化取证 2：仓库界面（描述/主页/topics）PII 扫描 + 主页渲染确认。

用户要求「不要写隐私信息」覆盖的不只是 README —— 仓库描述、主页链接同样公开。
本脚本对全部自有仓库的这些字段跑 PII 判据，并带阴性对照。
"""
import json, re, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")

PII = ["南通", "大学", "机械", "智能制造", "2025级", "2025 级", "涌淇", "本科",
       "大四", "学院", "校区", "宿舍", "学号", "njust", "ntu"]

def gh(*a):
    r = subprocess.run(["gh"] + list(a), capture_output=True)
    return json.loads(r.stdout.decode("utf-8")) if r.returncode == 0 else None

repos = gh("api", "users/qiqqqqq517/repos?per_page=100") or []
own = [x for x in repos if not x["fork"]]
print("自有仓库 %d 个 / 全部 %d 个\n" % (len(own), len(repos)))

fails = []
print("%-18s %-8s %s" % ("仓库", "PII", "扫描字段"))
print("-" * 72)
for r in sorted(own, key=lambda x: x["name"]):
    fields = {
        "description": r.get("description") or "",
        "homepage":    r.get("homepage") or "",
        "topics":      " ".join(r.get("topics") or []),
        "name":        r["name"],
    }
    hits = []
    for k, v in fields.items():
        for p in PII:
            if p.lower() in v.lower():
                hits.append("%s:%s" % (k, p))
    if hits: fails.append((r["name"], hits))
    print("%-18s %-8s desc=%s home=%s topics=%s" % (
        r["name"], "⚠" + ",".join(hits) if hits else "clean",
        (r.get("description") or "【空】")[:34],
        (r.get("homepage") or "【空】")[:24],
        ",".join(r.get("topics") or [])[:30] or "【无】"))

print("\n=== 阴性对照：把 PII 注入样本，判据必须检出 ===")
sample = "南通大学机械工程学院智能制造工程 2025 级 涌淇"
got = [p for p in PII if p.lower() in sample.lower()]
print("  注入样本命中: %s" % got)
print("  %s 判据有效" % ("PASS" if got else "FAIL"))

print("\n=== 描述质量检查（仓库界面观感）===")
for r in sorted(own, key=lambda x: -x["stargazers_count"]):
    d = r.get("description") or ""
    issues = []
    if not d: issues.append("描述为空")
    if d and len(d) < 20: issues.append("描述过短(%d字)" % len(d))
    if not (r.get("topics")): issues.append("无 topics")
    if not (r.get("license")): issues.append("无 license")
    print("  %-18s ★%-3d %s" % (r["name"], r["stargazers_count"],
          "、".join(issues) if issues else "OK"))

print("\nVERDICT: %s" % ("FAIL -> %s" % fails if fails else "仓库界面无 PII"))