#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
引擎合规检查器 —— 把 SPEC.md 变成可执行的门槛。

用法：
    python3 tools/lint_skill.py --all
    python3 tools/lint_skill.py human-voice-writing
    python3 tools/lint_skill.py some-new-engine --strict

检查项（对齐 SPEC.md 与 CONTRIBUTING.md 的准入线）：
  E1 frontmatter 合法：--- 包裹，含 name / description
  E2 name 与目录名一致
  E3 description 长度 ≤ 450 字（建议 ≤ 300）；这是常驻上下文的「指针」，
     写长了每一轮都在付钱
  E4 必需小节齐全（按关键词匹配 ## 标题）
  E5 SKILL.md 体积 ≤ 4400 字符（建议 ≤ 4000）；超了说明该做渐进披露
  E6 至少 1 个指向 references/ 的指针（渐进披露的证据）
  E7 SKILL.md 内不得有「版本记录」小节（版本属于 CHANGELOG.md）
  E8 仓库内不得有 .backup/ 目录或 *N.txt 式的语料全文
  E9 不得存在 sources/local/ 下的 .txt（版权边界）
  E10 examples/ 至少 1 个 > 1KB 的完整产出（片段不算示例，见 SPEC §1）

退出码：0 全通过 / 1 有错误 / 2 参数错误
说明：本文件在无 Python 沙箱内写成，未经实际执行。
"""

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 体积按**字符数**计，不按字节数。
# 早先版本按字节设了 8192，结果三个引擎全判不合规——中文一个字符 3 字节，
# 8192 B 只够 2700 汉字，那是逼作者砍内容，不是逼他做渐进披露。
# 实测：下沉原子表之后三份引擎在 3654–4012 字符（约 3300–3600 tokens），
# 与一份信息密度相当的高质量 skill 同量级。所以门槛定在 4400。
MAX_SKILL_CHARS = 4400
WARN_SKILL_CHARS = 4000
MAX_DESC_CHARS = 450
WARN_DESC_CHARS = 300

# 小节名 → 可接受的标题关键词（任一命中即算有）
REQUIRED_SECTIONS = [
    ("能力边界", ["能力边界", "能做什么", "边界条件"]),
    ("核心认知", ["核心认知"]),
    ("原子",     ["原子"]),
    ("组合规则", ["组合规则", "组合"]),
    ("风格指纹", ["风格指纹", "指纹"]),
    ("红线",     ["红线"]),
    ("工作流",   ["工作流", "写作流程", "流程"]),
]

RE_FENCE = re.compile(r"^---\s*$", re.M)
RE_H2 = re.compile(r"^##\s+(.+?)\s*$", re.M)
RE_KV = re.compile(r"^(name|description)\s*:\s*(.*)$", re.M)


class Issue:
    def __init__(self, code, level, msg):
        self.code, self.level, self.msg = code, level, msg

    def __str__(self):
        mark = "ERROR" if self.level == "error" else "warn "
        return f"  [{mark}] {self.code}  {self.msg}"


def parse_frontmatter(text):
    """返回 (fields, body, err)。支持 description: | 块标量。"""
    if not text.startswith("---"):
        return {}, text, "文件未以 --- 开头，缺少 frontmatter"
    parts = RE_FENCE.split(text, maxsplit=2)
    if len(parts) < 3:
        return {}, text, "frontmatter 未闭合（缺少第二个 ---）"
    fm, body = parts[1], parts[2]

    fields = {}
    lines = fm.splitlines()
    i = 0
    while i < len(lines):
        m = RE_KV.match(lines[i].strip())
        if m:
            key, val = m.group(1), m.group(2).strip()
            if val in ("|", ">", "|-", ">-"):
                block = []
                i += 1
                while i < len(lines) and (lines[i].startswith(" ") or not lines[i].strip()):
                    block.append(lines[i].strip())
                    i += 1
                fields[key] = "\n".join(block).strip()
                continue
            fields[key] = val
        i += 1
    return fields, body, None


def lint_engine(engine_dir, strict=False):
    issues = []
    skill = engine_dir / "SKILL.md"

    if not skill.exists():
        return [Issue("E1", "error", f"{engine_dir.name}: 缺 SKILL.md")]

    raw = skill.read_bytes()
    size = len(raw)
    text = raw.decode("utf-8", errors="replace")
    chars = len(text)

    # E5 体积（按字符，见文件头的说明）
    if chars > MAX_SKILL_CHARS:
        issues.append(Issue("E5", "error",
                            f"SKILL.md {chars} 字符 > {MAX_SKILL_CHARS}，需下沉到 references/"))
    elif chars > WARN_SKILL_CHARS:
        issues.append(Issue("E5", "warn",
                            f"SKILL.md {chars} 字符 > 建议值 {WARN_SKILL_CHARS}"))

    fields, body, err = parse_frontmatter(text)
    if err:
        issues.append(Issue("E1", "error", err))
        fields, body = {}, text

    # E1 字段
    for key in ("name", "description"):
        if not fields.get(key):
            issues.append(Issue("E1", "error", f"frontmatter 缺 {key}"))

    # E2 name 一致性
    name = fields.get("name", "")
    if name and name != engine_dir.name:
        issues.append(Issue("E2", "error",
                            f"name「{name}」≠ 目录名「{engine_dir.name}」"))

    # E3 description 长度
    desc = fields.get("description", "")
    if desc:
        n = len(desc.replace("\n", " "))
        if n > MAX_DESC_CHARS:
            issues.append(Issue("E3", "error",
                                f"description {n} 字 > {MAX_DESC_CHARS}，指针太长"))
        elif n > WARN_DESC_CHARS:
            issues.append(Issue("E3", "warn",
                                f"description {n} 字 > 建议值 {WARN_DESC_CHARS}"))

    # E4 必需小节
    headings = RE_H2.findall(body)
    for label, keys in REQUIRED_SECTIONS:
        if not any(any(k in h for k in keys) for h in headings):
            issues.append(Issue("E4", "error", f"缺小节：{label}（## 标题需含关键词 {keys[0]}）"))

    # E6 渐进披露指针
    if "references/" not in body:
        issues.append(Issue("E6", "error", "SKILL.md 没有任何 references/ 指针，等于全内联"))

    # E7 版本记录
    if any("版本记录" in h or "更新记录" in h for h in headings):
        issues.append(Issue("E7", "error", "SKILL.md 含「版本记录」小节，应移到 CHANGELOG.md"))

    # E8 备份与语料
    if (engine_dir / ".backup").exists():
        issues.append(Issue("E8", "error", f"{engine_dir.name}/.backup/ 不应入库"))
    for txt in engine_dir.rglob("*.txt"):
        if txt.stat().st_size > 5000:
            issues.append(Issue("E8", "error",
                                f"疑似语料全文：{txt.relative_to(ROOT)} "
                                f"（{txt.stat().st_size}B）— 见 sources/INDEX.md"))

    # E9 sources/local
    for local in engine_dir.rglob("sources/local"):
        if local.is_dir() and any(local.iterdir()):
            issues.append(Issue("E9", "error",
                                f"{local.relative_to(ROOT)}/ 非空，语料全文不得入库"))

    # E10 examples/
    # 一个引擎没有完整产出示例，等于「只给了方法没给标准」——写出来的人无法自比。
    ex_dir = engine_dir / "examples"
    solid = [p for p in ex_dir.glob("*") if p.is_file() and p.stat().st_size > 1024] \
        if ex_dir.is_dir() else []
    if not solid:
        issues.append(Issue("E10", "warn",
                            "examples/ 没有 > 1KB 的完整产出（片段不算示例）"))

    if strict:
        issues = [i for i in issues if True]  # warn 也计入失败，见下方汇总
    return issues


def repo_level_lint():
    issues = []
    for need in ("LICENSE", "README.md", "SPEC.md", "CHANGELOG.md", ".gitignore"):
        if not (ROOT / need).exists():
            issues.append(Issue("R1", "warn", f"仓库根缺 {need}"))
    # 语料全文
    for txt in ROOT.rglob("*.txt"):
        if ".git" in txt.parts:
            continue
        if txt.stat().st_size > 5000:
            issues.append(Issue("R2", "error",
                                f"疑似语料全文：{txt.relative_to(ROOT)} "
                                f"（{txt.stat().st_size}B）"))
    for backup in ROOT.rglob(".backup"):
        if ".git" not in backup.parts:
            issues.append(Issue("R3", "error",
                                f"备份目录不应入库：{backup.relative_to(ROOT)}"))
    return issues


def main(argv=None):
    ap = argparse.ArgumentParser(description="引擎合规检查（SPEC.md 的执行版）")
    ap.add_argument("engines", nargs="*", help="引擎目录名")
    ap.add_argument("--all", action="store_true", help="检查所有含 SKILL.md 的目录")
    ap.add_argument("--strict", action="store_true", help="warn 也算失败")
    ap.add_argument("--repo", action="store_true", help="只跑仓库级检查")
    args = ap.parse_args(argv)

    if args.all:
        targets = [p.parent for p in sorted(ROOT.glob("*/SKILL.md"))]
    elif args.repo:
        targets = []
    elif args.engines:
        targets = [ROOT / e for e in args.engines]
    else:
        ap.print_help()
        return 2

    all_issues = []
    if not args.engines or args.repo:
        all_issues += repo_level_lint()
    for d in targets:
        if not d.is_dir():
            all_issues.append(Issue("E0", "error", f"目录不存在：{d}"))
            continue
        found = lint_engine(d, args.strict)
        if found:
            print(f"{d.name}:")
            for i in found:
                print(i)
        else:
            print(f"{d.name}: 通过")
        all_issues += found

    errors = [i for i in all_issues if i.level == "error"]
    warns = [i for i in all_issues if i.level == "warn"]
    print(f"\n{len(targets)} 个引擎｜错误 {len(errors)}｜警告 {len(warns)}")
    if errors:
        return 1
    if args.strict and warns:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
