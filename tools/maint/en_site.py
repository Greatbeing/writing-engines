#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""英文站（Greatbeing/caifeng-en）生成与推送，由 maintain.py --mode build 调用，也可单独跑。

步骤：目录不存在则 clone → pull → build_en_site.py --out <目录> → 有改动才 commit + push。
凭据：与 writing-engines 相同——沿用本仓库 origin 的协议/凭据形式（ssh 或 https + credential
helper / 内嵌 token），只把仓库名换成 caifeng-en；不另配凭据。

    python3 tools/maint/en_site.py                 # 构建并推送
    python3 tools/maint/en_site.py --dry-run       # 构建、比对，不 commit/push
    python3 tools/maint/en_site.py --dir /tmp/x    # 指定工作目录（默认 ../caifeng-en，或 $CAIFENG_EN_DIR）
"""
import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(os.environ.get("WRITING_HOME", Path(__file__).resolve().parents[2])).resolve()
DEFAULT_URL = "https://github.com/Greatbeing/caifeng-en.git"
IDENT = ["-c", "user.name=Greatbeing", "-c", "user.email=todobeing@gmail.com"]


def run(cmd, cwd, timeout=600):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)


def clone_url():
    """按 writing-engines 的 origin 类推：同协议、同凭据形式，仓库名换成 caifeng-en。"""
    r = run(["git", "remote", "get-url", "origin"], ROOT)
    u = (r.stdout or "").strip()
    if r.returncode == 0 and re.search(r"writing-engines(\.git)?/?$", u):
        return re.sub(r"writing-engines(\.git)?/?$", "caifeng-en.git", u)
    return DEFAULT_URL


def parse_missing(out):
    """build_en_site.py 输出里的『built en <类>: ... missing translations: N』→ {类: N}。"""
    miss = {}
    for kind, n in re.findall(r"built en ([\w-]+):[^\n]*?missing translations:\s*(\d+)", out or ""):
        miss[kind] = int(n)
    return miss


def en_site(dry_run=False, workdir=None):
    """返回 dict(ok, changed, pushed, missing, log)。不抛异常。"""
    res = {"ok": False, "changed": False, "pushed": False, "missing": {}, "log": []}
    log = res["log"]
    d = Path(workdir or os.environ.get("CAIFENG_EN_DIR") or ROOT.parent / "caifeng-en").resolve()
    try:
        if not (d / ".git").exists():
            url = clone_url()
            r = run(["git", "clone", url, str(d)], ROOT.parent if d.parent.exists() else None)
            if r.returncode != 0:
                log.append(f"en site: clone 失败：{(r.stderr or '')[-300:]}")
                return res
            log.append(f"en site: 已 clone 到 {d}")
        r = run(["git", "pull", "--rebase", "--autostash", "origin", "main"], d)
        if r.returncode != 0:
            log.append(f"en site: pull 失败：{(r.stderr or '')[-300:]}")
            return res
        b = run([sys.executable, str(ROOT / "tools/build_en_site.py"), "--out", str(d)], ROOT, 900)
        res["missing"] = parse_missing(b.stdout)
        if b.returncode != 0:
            log.append(f"en site: 构建失败：{(b.stderr or '')[-300:]}")
            return res
        dirty = run(["git", "status", "--porcelain"], d).stdout.strip()
        if not dirty:
            print("en site: no changes")
            log.append("en site: no changes")
            res["ok"] = True
            return res
        res["changed"] = True
        n = len(dirty.splitlines())
        if dry_run:
            log.append(f"en site: dry-run，检测到 {n} 个文件有改动，未提交")
            res["ok"] = True
            return res
        src = run(["git", "rev-parse", "--short", "HEAD"], ROOT).stdout.strip() or "unknown"
        run(["git", "add", "-A"], d)
        c = run(["git", *IDENT, "commit", "-m", f"build: regenerate from writing-engines@{src} ({n} files)"], d)
        if c.returncode != 0:
            log.append(f"en site: commit 失败：{(c.stderr or c.stdout or '')[-300:]}")
            return res
        for i in range(1, 6):
            p = run(["git", "push", "origin", "HEAD:main"], d)
            if p.returncode == 0:
                res["pushed"] = res["ok"] = True
                log.append(f"en site: 已提交 {n} 个文件并推送（源 {src}）")
                return res
            run(["git", "pull", "--rebase", "--autostash", "origin", "main"], d)
            time.sleep(8 * i)
        log.append(f"en site: push 失败：{(p.stderr or '')[-300:]}")
        return res
    except Exception as exc:  # noqa: BLE001 —— 失败不让整个维护挂掉
        log.append(f"en site: 出错：{type(exc).__name__}: {exc}")
        return res


def missing_detail(missing):
    if not missing:
        return "未解析到缺译数"
    return "缺译 " + "、".join(f"{k} {v}" for k, v in missing.items())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--dir")
    a = ap.parse_args()
    r = en_site(a.dry_run, a.dir)
    for line in r["log"]:
        print(line)
    print(f"en site: {missing_detail(r['missing'])}")
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
