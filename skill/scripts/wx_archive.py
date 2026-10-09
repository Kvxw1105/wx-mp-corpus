# -*- coding: utf-8 -*-
"""批量抓取并归档：正文 + 元数据 + 图片 URL 清单

用法
----
    python wx_archive.py <sn清单.json> [输出目录]

输出
----
    <输出目录>/articles/<date>-<title>.md     每篇一个 markdown
    <输出目录>/articles/_index.json           索引

sn 清单格式同 wx_fetch.py（数组，每项含 biz/mid/idx/sn/title）。
"""
import sys
import io
import os
import re
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wx_fetch import fetch, polite_sleep, _fresh_session  # noqa: E402


def safe(s):
    s = re.sub(r'[\\/:*?"<>|]', "_", (s or "untitled")).strip()
    return s[:60]


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "out")
    art = os.path.join(out, "articles")
    os.makedirs(art, exist_ok=True)

    items = [x for x in json.load(open(sys.argv[1], encoding="utf-8")) if x.get("sn")]
    index = []
    s = _fresh_session()
    for i, x in enumerate(items, 1):
        a, _ = fetch(x["biz"], x["mid"], x["idx"], x["sn"], session=s)
        if not a:
            print(f"[{i:>2}/{len(items)}] FAIL {x['title'][:30]}")
            continue
        fn = f"{a.publish_date or '0000-00-00'}-{safe(a.title)}.md"
        path = os.path.join(art, fn)
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# {a.title}\n\n")
            f.write(f"- 公众号：{a.author}\n")
            f.write(f"- 发布：{a.publish_date}\n")
            f.write(f"- 阅读：{a.read_num or '?'}　赞：{a.like_num or '?'}\n")
            f.write(f"- 原文：{a.url}\n")
            f.write(f"- mid：{a.mid}　sn：{a.sn}\n\n---\n\n")
            f.write(a.text)
            if a.images:
                f.write("\n\n---\n\n## 图片\n\n")
                for u in a.images:
                    f.write(f"![]({u})\n")
        index.append({
            "title": a.title, "date": a.publish_date, "read": a.read_num,
            "like": a.like_num, "mid": a.mid, "sn": a.sn, "file": fn,
            "chars": len(a.text), "images": len(a.images),
        })
        print(f"[{i:>2}/{len(items)}] {a.publish_date} {a.title[:30]:32s} "
              f"{len(a.text):>5}字 {len(a.images):>2}图")
        polite_sleep()

    with open(os.path.join(art, "_index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print(f"\n★ 完成 {len(index)}/{len(items)}，输出目录：{art}")


if __name__ == "__main__":
    main()
