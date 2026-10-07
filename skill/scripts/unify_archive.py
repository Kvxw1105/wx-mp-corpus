# -*- coding: utf-8 -*-
"""
归档标准化 + 阅读友好合集生成器

用法：
    python unify_archive.py <工作目录> [号名]

    <工作目录>  含 out/articles/ 和 _list_merged.json 的目录
    [号名]      输出文件名前缀，默认取工作目录名

输入（约定）：
    <LAB>/out/articles/*.md        原始归档（脚本抓取产物）
    <LAB>/_list_merged.json        权威清单 [{title,read,like,date}]
    <LAB>/out/articles/_index.json 可选索引 [{mid,sn,read,like,chars,...}]

输出：
    <LAB>/out/articles_clean/*.md           标准化单篇
    <LAB>/out/<号名>-全文合集.md            可通读合集
"""
import os, re, json, glob, sys

if len(sys.argv) < 2:
    print(__doc__)
    sys.exit(1)

LAB = sys.argv[1].rstrip("/\\")
NAME = sys.argv[2] if len(sys.argv) > 2 else os.path.basename(LAB)
ART = os.path.join(LAB, "out/articles")
CLEAN = os.path.join(LAB, "out/articles_clean")
MERGED = os.path.join(LAB, "_list_merged.json")

# ---------- 载入权威清单（缺失不致命） ----------
merged = []
if os.path.exists(MERGED):
    merged = json.load(open(MERGED, encoding="utf-8"))
else:
    print(f"[warn] 未找到 {MERGED}，阅读量将只能从归档文件内读取")

_idx_path = os.path.join(ART, "_index.json")
idx = {}
if os.path.exists(_idx_path):
    idx = {x["mid"]: x for x in json.load(open(_idx_path, encoding="utf-8")) if x.get("mid")}

def norm(s):
    return re.sub(r"[\s，。！？、·：；“”\"'‘’（）()《》\-—….,!?]+", "", s or "")

# 建 title -> read/like/date 的映射（多候选）
by_title = {}
for x in merged:
    by_title.setdefault(norm(x["title"])[:14], []).append(x)

# ---------- 日期标准化 ----------
MONTH_CN = {f"{i}月": i for i in range(1, 13)}

def parse_date_field(raw, title):
    """把归档文件里混乱的日期字段转成 (sortkey, display)"""
    # 优先精确的 YYYY-MM-DD
    m = re.search(r"(20\d\d)-(\d\d)-(\d\d)", raw or "")
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}", f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    # 从清单里按标题找
    k = norm(title)[:14]
    for cand in by_title.get(k, []):
        d = cand.get("date") or ""
        m2 = re.search(r"(20\d\d)-(\d\d)-(\d\d)", d)
        if m2:
            y, mo, dd = int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
            # 2026-10-06(今天) 这种有问题，日期本身可能不准
            return f"{y:04d}-{mo:02d}-{dd:02d}", f"{y}-{mo:02d}-{dd:02d}"
        m3 = re.search(r"(\d{1,2})月(\d{1,2})日", d)
        if m3:
            return f"2026-{int(m3.group(1)):02d}-{int(m3.group(2)):02d}", f"2026-{int(m3.group(1)):02d}-{int(m3.group(2)):02d}"
        m4 = re.search(r"(\d{1,2})月(\d{1,2})日", raw or "")
        if m4:
            return f"2026-{int(m4.group(1)):02d}-{int(m4.group(2)):02d}", f"2026-{int(m4.group(1)):02d}-{int(m4.group(2)):02d}"
    # 兜底：从标题/文件名猜
    m5 = re.search(r"(\d{1,2})月(\d{1,2})日", raw or "")
    if m5:
        return f"2026-{int(m5.group(1)):02d}-{int(m5.group(2)):02d}", f"2026-{int(m5.group(1)):02d}-{int(m5.group(2)):02d}"
    return "9999-99-99", "日期未知"

# ---------- 扫描归档文件 ----------
records = {}  # mid -> record

for f in glob.glob(os.path.join(ART, "*.md")):
    txt = open(f, encoding="utf-8").read()
    base = os.path.basename(f)

    # 字段提取
    mi = re.search(r"mid[=：]\s*(\d+)", txt)
    si = re.search(r"sn[=：]\s*([0-9a-f]{32})", txt)
    ui = re.search(r"https?://mp\.weixin\.qq\.com/s\?[^\s\n]+", txt)
    mid = mi.group(1) if mi else ""
    sn = si.group(1) if si else ""
    url = ui.group(0) if ui else ""

    # 标题
    t0 = re.match(r"#\s*(.+)", txt)
    title = t0.group(1).strip() if t0 else base.replace(".md", "")

    # 阅读/赞
    rd = li = None
    mr = re.search(r"阅读[：:]\s*(\d+)", txt)
    ml = re.search(r"赞[：:]\s*(\d+)", txt)
    if mr: rd = int(mr.group(1))
    if ml: li = int(ml.group(1))

    # 正文（第一个 --- 之后）
    parts = txt.split("\n---\n", 1)
    body = parts[1].strip() if len(parts) > 1 else txt
    chars = len(re.sub(r"\s", "", body))

    # 日期
    dr = re.search(r"(?:发布(?:日期)?|日期)[：:]\s*(.+)", txt) or re.search(r"^(20\d\d-\d\d-\d\d)-", base)
    date_raw = dr.group(1).strip() if dr else base[:10]
    skey, disp = parse_date_field(date_raw if dr else "", title)

    # 用清单补全
    k = norm(title)[:14]
    if k in by_title:
        cand = by_title[k][0]
        if rd is None and cand.get("read"): rd = cand["read"]
        if li is None and cand.get("like"): li = cand["like"]
        if skey.startswith("9999"):
            skey, disp = parse_date_field(cand.get("date") or "", title)

    if mid in idx:
        if rd is None and idx[mid].get("read"): rd = idx[mid]["read"]
        if li is None and idx[mid].get("like"): li = idx[mid]["like"]

    key = mid or norm(title)[:16]
    rec = {
        "mid": mid, "sn": sn, "title": title, "url": url,
        "read": rd, "like": li, "date": disp, "sort": skey,
        "chars": chars, "body": body, "src": base,
    }
    # 同 mid 取正文字数多的（长文归档优先）
    if key not in records or rec["chars"] > records[key]["chars"]:
        records[key] = rec

recs = [r for r in records.values() if r["chars"] >= 40]
recs.sort(key=lambda r: (r["sort"], -(r["read"] or 0)))

# ---------- 输出标准化单篇 ----------
os.makedirs(CLEAN, exist_ok=True)
for r in recs:
    fn = f"{r['date']}-{re.sub(r'[\\\\/:*?\"<>|]', '_', r['title'])[:60]}.md"
    lines = [
        f"# {r['title']}", "",
        f"- 公众号：{NAME}",
        f"- 发布：{r['date']}",
        f"- 阅读：{r['read'] if r['read'] is not None else '—'}　赞：{r['like'] if r['like'] is not None else '—'}",
    ]
    if r["mid"]: lines.append(f"- mid：{r['mid']}　sn：{r['sn']}")
    if r["url"]: lines.append(f"- 原文：{r['url']}")
    lines += ["", "---", "", r["body"], ""]
    open(os.path.join(CLEAN, fn), "w", encoding="utf-8").write("\n".join(lines))

# ---------- 合集 ----------
def tier(n):
    if n is None: return "·"
    if n >= 1000: return "★★★★"
    if n >= 500: return "★★★"
    if n >= 300: return "★★"
    if n >= 100: return "★"
    return "·"

out = []
out.append(f"# {NAME}·历史文章全文合集")
out.append("")
out.append(f"> 共 {len(recs)} 篇｜按发布时间排序｜★ 为阅读量档位")
out.append("")
out.append("**说明**：本合集为离线归档，正文来自公众号原文页，阅读量为采集时快照。")
out.append("")
out.append("---")
out.append("")

# 四位数速览
four = [r for r in recs if r["read"] and r["read"] >= 1000]
out.append("## 阅读量四位数（重点）")
out.append("")
out.append("| 标题 | 阅读 | 赞 | 赞率 | 发布 |")
out.append("|---|---|---|---|---|")
for r in sorted(four, key=lambda r: -(r["read"] or 0)):
    t = r["title"].replace("|", "\\|")
    rate = f"{r['like']/r['read']*100:.2f}%" if r["read"] and r["like"] else "—"
    out.append(f"| {t} | {r['read']} | {r['like']} | {rate} | {r['date']} |")
out.append("")
out.append(f"合计 {len(four)} 篇（其中 {sum(1 for r in four if r['chars']>500)} 篇已获全文，{sum(1 for r in four if r['chars']<=500)} 篇为短图文卡片）")
out.append("")
out.append("---")
out.append("")

# 目录
out.append("## 全部目录")
out.append("")
out.append("| # | 发布 | 标题 | 阅读 | 赞 | 字 |")
out.append("|---|---|---|---|---|---|")
for i, r in enumerate(recs, 1):
    t = r["title"].replace("|", "\\|")
    rd = r["read"] if r["read"] is not None else "—"
    li = r["like"] if r["like"] is not None else "—"
    out.append(f"| {i} | {r['date']} | {t} | {rd} | {li} | {r['chars']} |")
out.append("")
out.append("---")
out.append("")

for i, r in enumerate(recs, 1):
    out.append(f"## {i}. {r['title']}")
    out.append("")
    out.append(f"`{r['date']}`　阅读 **{r['read'] if r['read'] is not None else '—'}**　赞 {r['like'] if r['like'] is not None else '—'}　{tier(r['read'])}　{r['chars']} 字")
    out.append("")
    out.append(r["body"])
    out.append("")
    out.append("---")
    out.append("")

COLLECTION = os.path.join(LAB, f"out/{NAME}-全文合集.md")
open(COLLECTION, "w", encoding="utf-8").write("\n".join(out))

print("篇数:", len(recs))
print("标准化单篇 ->", CLEAN)
print("合集 ->", COLLECTION)
four = [r for r in recs if r["read"] and r["read"] >= 1000]
print("四位数:", len(four), [r["title"][:16] for r in four])
