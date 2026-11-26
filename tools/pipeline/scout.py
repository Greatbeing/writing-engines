#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""外部情报搜集员：抓取对标账号的新公开文章 → 拆解手法 → 喂给引擎迭代。

版权边界（与仓库一致）：
  原文只存本机 tools/tests/fixtures/local/（已 gitignore，不入库）；
  入库的只有拆解结论 drafts/pipeline/_intel/<引擎>.md（引原文 ≤30 字/处）。

来源在 SOURCES 里配：每个来源 = 搜索词 + 对应引擎。
搜索走 Bing（搜狗微信对云机返回空），只收 mp.weixin.qq.com 与来源白名单域名的文章。

用法：
  python3 tools/pipeline/scout.py              # 全部来源，每源最多 3 篇新文
  python3 tools/pipeline/scout.py --source 浙江宣传 --dry-run
"""
import argparse
import base64
import datetime as dt
import hashlib
import html
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline as P  # noqa: E402

ROOT = P.ROOT
LOCAL = ROOT / "tools" / "tests" / "fixtures" / "local"
INTEL = P.PIPE / "_intel"
SEEN = INTEL / "seen.json"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"

SOURCES = {
    "浙江宣传": {"engine": "guanfang-writing", "q": "浙江宣传 公众号", "domains": ["mp.weixin.qq.com", "zjol.com.cn"]},
    "三联生活实验室": {"engine": "sanlian-writing", "q": "三联生活实验室", "domains": ["mp.weixin.qq.com", "lifeweek.com.cn"]},
    "三联生活周刊": {"engine": "feature-writing", "q": "三联生活周刊 封面故事", "domains": ["lifeweek.com.cn", "mp.weixin.qq.com"]},
    "人民日报评论": {"engine": "guanfang-writing", "q": "人民日报评论 人民时评", "domains": ["opinion.people.com.cn", "mp.weixin.qq.com"]},
}


def get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode(r.headers.get_content_charset() or "utf-8", "ignore")


def unbing(u):
    """Bing 结果是 /ck/a?...&u=a1<base64> 跳转链接，解出真实地址。"""
    q = urllib.parse.parse_qs(urllib.parse.urlparse(u).query)
    v = (q.get("u") or [""])[0]
    if v.startswith("a1"):
        try:
            return base64.urlsafe_b64decode(v[2:] + "==").decode("utf-8", "ignore")
        except Exception:
            return u
    return u


def search(src):
    q = urllib.parse.quote(src["q"] + " " + " OR ".join(f"site:{d}" for d in src["domains"]))
    page = get(f"https://www.bing.com/search?q={q}&setlang=zh-CN&filters=ex1%3a%22ez2%22")  # 近一周
    urls = []
    for h in re.findall(r'<h2[^>]*>\s*<a[^>]+href="([^"]+)"', page):
        u = html.unescape(h)
        u = unbing(u) if "bing.com/ck/" in u else u
        if any(d in u for d in src["domains"]) and u not in urls:
            urls.append(u)
    return urls


def article(url):
    page = get(url)
    t = re.search(r'<meta property="og:title" content="([^"]+)"', page) or re.search(r"<title>(.*?)</title>", page, re.S)
    title = html.unescape(t.group(1)).strip() if t else url
    body = re.search(r'id="js_content"[^>]*>(.*?)</div>\s*<script', page, re.S)
    raw = body.group(1) if body else page
    raw = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", raw, flags=re.S)
    raw = re.sub(r"</p>|<br\s*/?>", "\n", raw)
    text = html.unescape(re.sub(r"<[^>]+>", "", raw))
    text = "\n".join(x.strip() for x in text.splitlines() if len(x.strip()) > 8)
    return title, text


def analyze(engine, name, title, text):
    out = P.llm("你是写作手法拆解师。只拆手法，不复述内容。引原文每处 ≤30 字。",
                f"""这是「{name}」的一篇新文章《{title}》。对应写作引擎「{engine}」。

引擎现有文档（节选）：
{P.W.skill_body(engine)[:1800]}

原文：
---
{text[:6000]}
---

输出 Markdown：
### 《{title}》
- 开头怎么起（引 ≤30 字）
- 结构骨架（一行）
- 2–3 个最值得学的手法，每个：名字｜原文例句（≤30字）｜为什么有效
- **引擎没写到的新手法**（没有就写「无」）——这一条是给引擎迭代用的证据
""")
    return out.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source")
    ap.add_argument("--per", type=int, default=3)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    INTEL.mkdir(parents=True, exist_ok=True)
    LOCAL.mkdir(parents=True, exist_ok=True)
    seen = json.loads(SEEN.read_text(encoding="utf-8")) if SEEN.exists() else {}
    got = 0
    for name, src in SOURCES.items():
        if a.source and a.source != name:
            continue
        try:
            urls = search(src)
        except Exception as e:
            print(f"[情报] {name} 搜索失败：{e}"); continue
        new = [u for u in urls if hashlib.md5(u.encode()).hexdigest() not in seen][: a.per]
        print(f"[情报] {name}：搜到 {len(urls)}，新 {len(new)}")
        for u in new:
            try:
                title, text = article(u)
            except Exception as e:
                print(f"  抓取失败 {u}：{e}"); continue
            if len(text) < 600:
                print(f"  正文过短，跳过 {title}"); continue
            h = hashlib.md5(u.encode()).hexdigest()
            print(f"  ✓ {title}（{len(text)} 字）")
            if a.dry_run:
                continue
            (LOCAL / f"{src['engine'].replace('-writing','')}-intel-{h[:8]}.txt").write_text(
                f"# 来源：{u}\n# 标题：{title}\n\n{text}\n", encoding="utf-8")
            note = analyze(src["engine"], name, title, text)
            f = INTEL / f"{src['engine']}.md"
            head = f.read_text(encoding="utf-8") if f.exists() else f"# 外部情报 · {src['engine']}\n\n"
            f.write_text(head + f"\n<!-- {dt.date.today()} {name} {u} -->\n{note}\n", encoding="utf-8")
            seen[h] = {"url": u, "title": title, "source": name, "date": dt.date.today().isoformat()}
            got += 1
    if not a.dry_run:
        SEEN.write_text(json.dumps(seen, ensure_ascii=False, indent=1), encoding="utf-8")
        if got:
            P.commit(f"intel: 新增 {got} 篇外部文章拆解")
    print(f"[情报] 本次拆解 {got} 篇")


if __name__ == "__main__":
    main()
