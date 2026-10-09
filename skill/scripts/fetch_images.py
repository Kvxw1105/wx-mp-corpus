# -*- coding: utf-8 -*-
"""下载「图片消息」类型文章的图集。

★ 背景
------
有一类文章是「图集 + 配文」——`item_show_type` = 8/10 + `picture_page_info_list`，
正文很短（往往只有歌词 + 话题标签），真正的内容在 1242×1656 的图文卡片里。
→ 必须把图下载下来才算采到内容，只看正文字数会误判成"采集失败"。

用法
----
    python fetch_images.py <sn清单.json> [输出目录]

sn 清单格式同 wx_fetch.py（数组，每项含 biz/mid/sn/title）。

输出
----
    <输出目录>/{mid}-{name}-{k}.jpg   去重后的图集
    <输出目录>/_index.json            mid → 图片清单
"""
import io
import json
import os
import re
import sys
import hashlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import requests  # noqa: E402
import urllib3  # noqa: E402
from wx_fetch import build_url, UA  # noqa: E402

urllib3.disable_warnings()


def session():
    s = requests.Session()
    s.trust_env = False
    s.proxies = {"http": None, "https": None}
    s.verify = False
    return s


def collect(biz, mid, sn, name, out, s):
    """抓一篇的图集。返回落盘的文件名列表。"""
    try:
        r = s.get(build_url(biz, mid, "1", sn),
                  headers={"User-Agent": UA}, timeout=30)
        py = r.content.decode("utf-8", "ignore")
    except Exception as e:
        # ★ 网络抖动（ChunkedEncodingError / IncompleteRead 等）不该让整批崩掉
        print(f"   ! 页面请求失败 {mid}: {type(e).__name__}: {e}")
        return []
    # picture_page_info_list 内的 cdn_url 是正片；data-src / og:image 兜底
    urls = re.findall(r"cdn_url:\s*'(https://mmbiz[^']+)'", py)
    urls += re.findall(r'data-src="(https?://mmbiz[^"]+)"', py)
    urls = list(dict.fromkeys(urls))

    saved, seen = [], set()
    for u in urls:
        try:
            ir = s.get(u, headers={"User-Agent": UA}, timeout=30)
            if ir.status_code != 200 or len(ir.content) < 3000:
                continue
            h = hashlib.md5(ir.content).hexdigest()
            if h in seen:          # 同一张图的不同压缩版，去重
                continue
            seen.add(h)
            ext = "jpg" if ("jpeg" in u or "jpg" in u or "wx_fmt=jpeg" in u) else "png"
            fn = f"{mid}-{name}-{len(saved)}.{ext}"
            open(os.path.join(out, fn), "wb").write(ir.content)
            saved.append(fn)
        except Exception as e:
            print(f"   ! {type(e).__name__}: {e}")
    return saved


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "out", "images")
    os.makedirs(out, exist_ok=True)

    items = [x for x in json.load(open(sys.argv[1], encoding="utf-8")) if x.get("sn")]
    s = session()
    index = {}
    idx_path = os.path.join(out, "_index.json")
    if os.path.exists(idx_path):
        index = json.load(open(idx_path, encoding="utf-8"))

    for x in items:
        mid, sn = str(x["mid"]), x["sn"]
        name = re.sub(r"[^\w\u4e00-\u9fff]", "", x.get("title") or "")[:10] or "img"
        files = collect(x["biz"], mid, sn, name, out, s)
        if files:
            index[mid] = {"title": x.get("title"), "read": x.get("read"),
                          "files": files}
            print(f"[{len(files)}张] {(x.get('title') or '')[:36]}")
    json.dump(index, open(idx_path, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"\n共 {len(index)} 篇有图集，"
          f"{sum(len(v['files']) for v in index.values())} 张图")


if __name__ == "__main__":
    main()
