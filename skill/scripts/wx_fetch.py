# -*- coding: utf-8 -*-
"""
公众号文章采集器（chksm 解锁版）
================================

★ 核心发现（实测，400+ 次对照实验）
------------------------------------------------
访问 https://mp.weixin.qq.com/s?... 要拿到正文，两个条件同时成立：

  1. URL 里必须带 `chksm` 键 —— **值任意，甚至 64 个 0 都行**。
     服务端只用「有没有 chksm」判断请求是否来自正规链路，不校验值。
     带 sn 但不带 chksm 的"裸 URL" → 302 → wappoc_appmsgcaptcha（"未知错误"）。

  2. User-Agent 必须是**普通浏览器 UA**（Chrome/Safari 都行）。
     ★ 反直觉：`MicroMessenger` 微信 UA **是被拒绝的**（302）；
       普通 Chrome UA 才返回完整正文。流行项目里"伪装微信 UA"的做法是错的。

与 IP 无关、与 cookie 无关、与登录态无关。

用法
----
    python wx_fetch.py <sn清单.json>

sn 清单格式（数组，每项一篇）：
    [{"title": "...", "biz": "Mzk...==", "mid": "2247485363",
      "idx": "1", "sn": "8b4757..."}]

也可作为模块导入：
    from wx_fetch import fetch
    art, raw = fetch(biz, mid, idx, sn)
"""
import re
import time
import random
import requests
from html import unescape

CHKSM_PAD = "0" * 64
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def build_url(biz, mid, idx, sn, chksm=None):
    """构造能过闸门的 URL。chksm 值无所谓，键在就行。"""
    chksm = chksm or CHKSM_PAD
    return (f"https://mp.weixin.qq.com/s?__biz={biz}&mid={mid}&idx={idx}"
            f"&sn={sn}&chksm={chksm}")


def build_url_nosn(biz, mid, idx="1"):
    """无 sn 版本，也能 200，但拿不到正文（用来探索）。"""
    return f"https://mp.weixin.qq.com/s?__biz={biz}&mid={mid}&idx={idx}"


def _pick(pats, s):
    for p in pats:
        m = re.search(p, s, re.S)
        if m:
            return m.group(1)
    return None


def strip_html(h):
    if not h:
        return ""
    h = re.sub(r"<br\s*/?>", "\n", h)
    h = re.sub(r"</(p|section|div|li|h[1-6])>", "\n", h)
    h = re.sub(r"<[^>]+>", "", h)
    h = unescape(h)
    h = re.sub(r"[ \t\u00a0]+", " ", h)
    h = re.sub(r"\n{3,}", "\n\n", h)
    return h.strip()


class Article:
    def __init__(self, d):
        self.__dict__.update(d)

    def __repr__(self):
        return f"<Article {self.title[:24]!r} {self.read_num}/{self.like_num}>"


def _fresh_session():
    """★ 关键：系统代理常被外部程序改到 mitmproxy，Python 不认它的 CA
    → SSLCertVerificationError。这里无条件清空代理 + 关校验，保证谁调用都不踩坑。"""
    s = requests.Session()
    s.trust_env = False
    s.proxies = {"http": None, "https": None}
    s.verify = False
    try:
        import urllib3
        urllib3.disable_warnings()
    except Exception:
        pass
    return s


def fetch(biz, mid, idx, sn, chksm=None, timeout=30, session=None, retry=3):
    """抓一篇。返回 (Article | None, raw_html)。"""
    s = session or _fresh_session()
    # ★ 即便调用方传了 session，也强制清空代理（防止系统代理劫持）
    try:
        s.trust_env = False
        s.proxies = {"http": None, "https": None}
        s.verify = False
    except Exception:
        pass
    url = build_url(biz, mid, idx, sn, chksm)
    last = None
    for attempt in range(retry):
        try:
            r = s.get(url, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"},
                      timeout=timeout, allow_redirects=False)
            if r.status_code == 302:
                last = "302"
                time.sleep(1.5 * (attempt + 1))
                continue
            py = r.content.decode("utf-8", "ignore")
            # ★ 三种模板都要认：
            #   1. 普通图文   = rich_media_content / id="js_content"
            #   2. 卡片分享图 = common_share_image_content，正文在 og:description
            #   3. 图片消息   = picture_page_info_list / item_show_type，正文在
            #                  text_page_info.content（"小绿书"图文笔记）
            _has3 = ('rich_media_content' in py
                     or 'property="og:description"' in py
                     or 'text_page_info' in py)
            if not _has3:
                last = "no-js_content"
                time.sleep(1.0 * (attempt + 1))
                continue
            is_card = 'rich_media_content' not in py

            a = Article({
                "biz": biz, "mid": mid, "idx": idx, "sn": sn, "url": url,
                "title": unescape(_pick([
                    r'property="og:title"\s+content="(.+?)"',
                    r"var\s+msg_title\s*=\s*'([^']+)'",
                    r'var\s+msg_title\s*=\s*"([^"]+)"',
                    r'<h1[^>]*id="activity-name"[^>]*>(.*?)</h1>'], py) or "").strip(),
                "author": strip_html(_pick([
                    r'var\s+nickname\s*=\s*htmlDecode\("(.+?)"\)',
                    r'var\s+nickname\s*=\s*"([^"]*)"',
                    r'id="js_name"[^>]*>(.*?)<'], py) or ""),
                "publish_ts": _pick([r'var\s+ct\s*=\s*"(\d+)"',
                                     r'var\s+create_time\s*=\s*"(\d+)"'], py),
                "read_num": _pick([r'var\s+read_num\s*=\s*"(\d+)"',
                                   r'"read_num"\s*:\s*(\d+)'], py),
                "like_num": _pick([r'var\s+like_num\s*=\s*"(\d+)"',
                                   r'"like_num"\s*:\s*(\d+)'], py),
                "raw_len": len(r.content),
            })
            body = _pick([r'id="js_content"[^>]*>(.*?)</div>\s*<script',
                          r'id="js_content"[^>]*>(.*?)</div>\s*</div>'], py)
            a.html = body or ""
            if body:
                a.text = strip_html(body)
            elif is_card:
                # ★ 卡片模板：正文在 og:description。它是「HTML 属性值」里内嵌
                #   「JS 字符串」，所以转义是双层的，必须按顺序解：
                #     ① \x26lt;  →  &lt;   （先解 JS 的 \x26 = &）
                #     ② &lt;     →  <      （再解 HTML 实体）
                t = _pick([r'property="og:description"\s+content="(.*?)"'], py) or ""
                if t.strip():
                    t = re.sub(r"\\x26", "&", t)              # \x26 -> &
                    t = t.replace("\\x0a", "\n").replace("\\n", "\n")
                    t = unescape(t)                           # &lt; -> <
                    t = re.sub(r'<a[^>]*wx_topic_link[^>]*>(.*?)</a>', r'\1', t, flags=re.S)
                else:
                    # ★ 图片消息模板：正文在 text_page_info.content
                    t = _pick([r'text_page_info\s*:\s*\{[^}]*?content\s*:\s*\'((?:[^\'\\]|\\.)*)\''],
                              py) or ""
                    if t:
                        t = re.sub(r"\\x26", "&", t)
                        t = t.replace("\\x0a", "\n").replace("\\n", "\n")
                        t = unescape(t)
                a.text = strip_html(t)
            else:
                a.text = ""
            a.images = list(dict.fromkeys(
                re.findall(r'data-src="(https?://mmbiz[^"]+)"', py) or
                re.findall(r'<img[^>]+src="(https?://mmbiz[^"]+)"', py) or
                re.findall(r'property="og:image"\s+content="(https?://mmbiz[^"]+)"', py)
            ))
            a.is_card = is_card
            if a.publish_ts:
                a.publish_date = time.strftime("%Y-%m-%d", time.localtime(int(a.publish_ts)))
            else:
                a.publish_date = None
            return a, py
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
            time.sleep(1.5 * (attempt + 1))
    return None, f"FAILED after {retry}: {last}"


def polite_sleep(a=0.7, b=1.6):
    time.sleep(random.uniform(a, b))


if __name__ == "__main__":
    import sys, io, json
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    items = [x for x in json.load(open(sys.argv[1], encoding="utf-8")) if x.get("sn")]
    s = _fresh_session()
    ok = 0
    for x in items:
        a, _ = fetch(x["biz"], x["mid"], x["idx"], x["sn"], session=s)
        if a:
            ok += 1
            print(f"[{a.publish_date}] {a.title[:34]:36s} 正文{len(a.text):>6}字 图{len(a.images):>3}张")
        else:
            print(f"[FAIL] {x['title'][:30]}")
        polite_sleep()
    print(f"\n{ok}/{len(items)}")
