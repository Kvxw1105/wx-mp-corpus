# scripts · 脚本集

四个脚本，对应流水线的四段。**全部不需要登录态**。

| 脚本 | 作用 | 依赖 |
|---|---|---|
| `wx_fetch.py` | 抓单篇正文（**核心**，chksm 解锁逻辑在这里） | requests |
| `wx_archive.py` | 批量抓取并归档为 Markdown | requests |
| `fetch_images.py` | 下载图集类文章的图（`cdn_url`） | requests |
| `unify_archive.py` | 归档标准化 + 生成通读合集 | 标准库 |

## 输入：sn 清单

三个抓取脚本都吃同一个输入 —— 一个 JSON 数组，每项一篇文章：

```json
[
  {
    "title": "示例标题",
    "biz": "Mzk5MDE2NzQ0NA==",
    "mid": "2247485363",
    "idx": "1",
    "sn": "8b4757551e8834e236583a1ebb4e3a83",
    "read": 2891,
    "like": 115
  }
]
```

各字段从哪来：

- `biz` —— 公众号唯一标识。从该号**任意一篇**文章的 URL 里拿（`__biz=` 后面那串），
  同一号所有文章都一样。
- `mid` / `idx` —— 文章 ID，也在 URL 里。
- `sn` —— ★ **必须从微信客户端点开文章时抓包拿到**。
  服务端强校验，不可盲扫（试过扫 mid 区间，全部返回空壳）。
- `read` / `like` —— 可选，仅用于归档时写进元数据；抓取本身不需要。

> ⚠️ `sn` 是最关键的字段，也是最难拿的。它**无法绕过**：
> 无 sn 或假 sn 一律返回约 31756 字节空壳，HTTP 200 不报错（静默失败）。

## 用法

```bash
pip install requests

# 1. 抓单篇（调试用，打印每篇字数/图数）
python wx_fetch.py sn清单.json

# 2. 批量抓取并归档
python wx_archive.py sn清单.json out

# 3. 下载图集类文章的图
python fetch_images.py sn清单.json out/images

# 4. 归档标准化 + 生成通读合集（换目录即可复用）
python unify_archive.py <工作目录> <号名>
```

## 作为模块用

```python
from wx_fetch import fetch

art, raw_html = fetch(biz, mid, idx, sn)
print(art.title, art.publish_date, len(art.text), "字")
```

## 目录约定

抓取脚本默认输出到 `out/`，与 `unify_archive.py` 的输入约定对齐：

```
<工作目录>/
  out/articles/*.md         wx_archive.py 的产物（原始归档）
  out/articles/_index.json  索引
  out/images/               fetch_images.py 的产物
  out/articles_clean/       unify_archive.py 的产物（标准化单篇）
  out/<号名>-全文合集.md     unify_archive.py 的产物（通读合集）
```
