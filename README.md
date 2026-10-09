<div align="center">

# wx-mp-corpus

**把一个公众号的历史文章，变成一条可复现的语料生产线。**

A reproducible pipeline that turns a WeChat Official Account's article history
into a readable corpus — full text **without login** — plus content research on top.

*Agent Skill · MIT · 正文抓取无需登录 · 无需付费工具*

</div>

---

## 这是什么

一套经过实战验证的微信公众号**语料采集 + 内容研究**方法论，以 Agent Skill 形态交付。

起点是一个很实际的问题：想通读某个公众号的全部历史文章，但——
官方不提供导出，第三方采集工具要付费，而"抓公众号"在坊间传说里又难又玄。

wx-mp-corpus 走的是另一条路：**把这件事拆成"要登录的"和"不要登录的"两半**，
然后发现真正难的那一半（正文）其实根本不需要登录。

> 首个完整验证：公众号「概念因子」全量采集 —— 42 篇列表 + 30 篇全文 + 30 张配图，
> 归档标准化后生成可通读合集（135 KB），并在其上完成一份 12 章内容研究报告
> （55 位学者 / 57 条概念 / 2 张交互图表）。见 [cases/](cases/)。

## 为什么不一样

核心结论一句话：**拿到公众号正文全文，不需要登录态、不需要 Cookie、不需要付费工具。**

只要 URL 带 `chksm` 键（值随便填）+ 一个普通的 Chrome UA 就行。这跟 IP、登录、Cookie 全都无关。

| | 典型采集工具 / 爬虫 | wx-mp-corpus |
|---|---|---|
| 正文获取 | 要登录 / 要 cookie / 要付费授权 | **URL 带 `chksm` + 普通浏览器 UA，无需登录** |
| 列表阅读量 | 常需付费工具或破解 | 走客户端 GUI（需登录），零成本 |
| 依赖 | 第三方二进制 / 付费授权 | 纯 HTTP + 一个脚本 |
| 对抗性 | 高（跟随平台改版） | 低（三模板判定，改版只需微调） |
| 边界 | 宣称"什么都能拿" | 拿不到就如实记录（`sn` 不可绕过） |

代价也如实说：**列表收割是 GUI 自动化，慢**（42 篇约 2 小时）；
正文抓取是纯 HTTP，**快**（30 篇约 5 分钟）。登录态才是瓶颈。

## 核心设计

```
列表收割（GUI 自动化，需登录）
   ↓ 42 篇元数据：标题 / 阅读 / 赞 / 日期
   ↓ 从每篇提取 mid + sn
正文抓取（纯 HTTP，无需登录）
   ↓ 三模板判定（普通图文 / 图集 / 分享卡）→ 全文
   ↓ 图集分支：下载 cdn_url 图
归档标准化（一个脚本）
   ↓ mid 去重 + 日期统一 + 元数据补全
通读合集（Markdown）
   ↓
内容研究（拆写作模板 / 统计引用班底 / 阅读量×赞率交叉分析）→ HTML 报告
```

## 安装

把 [`skill/`](skill/) 拷进你的 Agent skill 目录（如 `~/.agents/skills/wx-mp-corpus/`）。

前置条件：Python 3 + `requests`；列表收割环节需要一个已登录的微信 PC 客户端 + GUI 自动化能力。

适用于 Claude Code、Codex、ZCode 或任何支持 skill 的 Agent。

## 脚本

四个脚本**全部不需要登录**，可独立使用（输入格式与详细说明见 [`skill/scripts/`](skill/scripts/)）：

| 脚本 | 作用 |
|---|---|
| `wx_fetch.py` | 抓单篇正文（**核心**，chksm 解锁逻辑在这里） |
| `wx_archive.py` | 批量抓取并归档为 Markdown |
| `fetch_images.py` | 下载图集类文章的图（`cdn_url`） |
| `unify_archive.py` | 归档标准化 + 生成通读合集（纯标准库） |

```bash
pip install requests

python skill/scripts/wx_fetch.py    sn清单.json             # 抓取（打印每篇字数/图数）
python skill/scripts/wx_archive.py  sn清单.json out         # 归档为 Markdown
python skill/scripts/fetch_images.py sn清单.json out/images # 下图集
python skill/scripts/unify_archive.py <工作目录> <号名>      # 标准化 + 合集
```

也可作为模块用：

```python
from wx_fetch import fetch
art, raw = fetch(biz, mid, idx, sn)
print(art.title, art.publish_date, len(art.text), "字")
```

## 平台技巧精选（完整版见 SKILL.md 第 0-2 节）

- **`chksm` 值随便填，但必须有这个键** —— 有 `sn` 没 `chksm` 直接 302
- **必须用普通 Chrome UA** —— 伪装 `MicroMessenger` 微信 UA 会被拒绝（网上"必须伪装微信 UA"的说法是错的）
- **`len ≈ 31600` 且没有 `id="js_content"` = `sn` 不对** —— 服务端静默失败，HTTP 200 不报错，极易误判成功
- **`SetForegroundWindow` 从后台进程调用会静默失败** —— 症状是所有后续输入全无效，极易误判成"坐标算错"
- **`og:description` 是双层转义** —— 解序顺序错会让"正文"字数虚高（2413 字里 2000 字是 HTML 垃圾）
- **`requests` 必须显式关代理** —— `s.proxies={"http":None,"https":None}`，只写 `{}` 不够

## 边界与纪律

- **只读**：不点赞、不关注、不评论、不互动
- 不绕登录、不破解风控、不并发请求
- **区分"平台限制"和"自己的 bug"**：31756 空壳 = 自己的 sn 不对；
  没有 `sn` 来源 = 平台的墙，如实记录，不绕过
- 数据缺失如实标注 `—`，不猜、不补
- 遵守平台条款是使用者自己的责任

## 平台限制（如实记录，不绕过）

- **`sn` 不可绕过**：无 sn / 假 sn 一律返回空壳；盲扫 mid 全部无效。
  `sn` 只能从客户端点开文章时拿到。
- **列表接口要登录态**：`getmsg` 无 session 时返回 `{"errmsg":"no session"}`。
- **图集类文章内容在图里**：正文只有几十字（歌词 + 话题标签），必须下 `cdn_url`。
- **反复抢前台 + 输入注入会触发安全机制**，账号可能被登出。出现即停，交还用户手动登录。

## 目录

```
skill/            Agent Skill（SKILL.md + 归档标准化脚本）—— 主交付物
cases/            实战验证案例
docs/             发布说明
```

## License

MIT
