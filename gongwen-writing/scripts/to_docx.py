#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把纯文本公文排成符合 GB/T 9704-2012 主要要求的 .docx。

用法：
    python to_docx.py 草稿.md -o 输出.docx [--no-seal] [--cc "抄送：××。"] [--issuer "××厅办公室"] [--issue-date 2026年11月25日]

输入约定（与模板一致）：
    第1个非空行 = 标题；第2个以冒号结尾的行 = 主送机关；
    以“一、”开头 = 一级标题（黑体）；以“（一）”开头 = 二级标题（楷体）；
    以“附件：”开头 = 附件说明；末尾两行 = 署名、成文日期；
    以“（联系人”开头 = 附注。
    markdown 代码围栏会被忽略。

依赖：python-docx（pip install python-docx）。
字体需本机已安装：方正小标宋简体、仿宋_GB2312、黑体、楷体_GB2312；缺失时 Word 会替换显示，但文件中字体名仍正确。
"""
import argparse
import re
import sys

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt

XBS = "方正小标宋简体"
FS = "仿宋_GB2312"
HT = "黑体"
KT = "楷体_GB2312"
SAN = Pt(16)   # 三号
SI = Pt(14)    # 四号
ER = Pt(22)    # 二号
LINE = Pt(28.95)  # 实务做法：近似每面22行

RE_L1 = re.compile(r"^[一二三四五六七八九十]+、")
RE_L2 = re.compile(r"^（[一二三四五六七八九十]+）")
RE_DATE = re.compile(r"^\d{4}年\d{1,2}月\d{1,2}日$")


def set_font(run, name, size, bold=False):
    run.font.name = name
    run.font.size = size
    run.font.bold = bold
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for k in ("w:eastAsia", "w:ascii", "w:hAnsi"):
        rfonts.set(qn(k), name)


def para(doc, text="", font=FS, size=SAN, align=None, indent_chars=0, right_chars=0):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    pf.line_spacing = LINE
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    if indent_chars:
        pf.first_line_indent = Pt(16 * indent_chars)
    if right_chars:
        pf.right_indent = Pt(16 * right_chars)
    if align is not None:
        p.alignment = align
    if text:
        set_font(p.add_run(text), font, size)
    return p


def body_line(doc, line):
    """正文行：一级标题句黑体，二级标题句楷体，其余仿宋。标题后接正文时只把标题部分换字体。"""
    p = para(doc, indent_chars=2)
    m1, m2 = RE_L1.match(line), RE_L2.match(line)
    if m1 or m2:
        font = HT if m1 else KT
        # 标题到第一个句号为止（如“（一）及时拨付。请于……”）
        cut = line.find("。")
        head, rest = (line, "") if cut == -1 else (line[: cut + 1], line[cut + 1:])
        set_font(p.add_run(head), font, SAN)
        if rest:
            set_font(p.add_run(rest), FS, SAN)
    else:
        set_font(p.add_run(line), FS, SAN)


def add_rule(doc, thick):
    p = para(doc)
    ppr = p._p.get_or_add_pPr()
    bdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "8" if thick else "6")  # 1/8 磅：约0.35mm / 0.25mm
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "000000")
    bdr.append(bottom)
    ppr.append(bdr)
    p.paragraph_format.line_spacing = Pt(8)
    return p


def add_page_number(section):
    """页码：4号半角宋体，“— 1 —”，单页居右空一字、双页居左空一字。"""
    section.different_first_page_header_footer = False
    settings = section.part.document.settings.element
    if settings.find(qn("w:evenAndOddHeaders")) is None:
        settings.append(OxmlElement("w:evenAndOddHeaders"))
    section.footer_distance = Mm(28 - 7) if False else Mm(21)  # 近似：一字线上距版心下边缘7mm
    for footer, align in ((section.footer, WD_ALIGN_PARAGRAPH.RIGHT), (section.even_page_footer, WD_ALIGN_PARAGRAPH.LEFT)):
        p = footer.paragraphs[0]
        p.alignment = align
        if align == WD_ALIGN_PARAGRAPH.RIGHT:
            p.paragraph_format.right_indent = Pt(14)
        else:
            p.paragraph_format.left_indent = Pt(14)
        set_font(p.add_run("— "), "宋体", SI)
        r = p.add_run()
        set_font(r, "宋体", SI)
        for tag, txt in (("begin", None), (None, "PAGE"), ("end", None)):
            if tag:
                fc = OxmlElement("w:fldChar")
                fc.set(qn("w:fldCharType"), tag)
                r._r.append(fc)
            else:
                it = OxmlElement("w:instrText")
                it.set(qn("xml:space"), "preserve")
                it.text = txt
                r._r.append(it)
        set_font(p.add_run(" —"), "宋体", SI)


def parse(text):
    lines = [l.strip() for l in text.splitlines()]
    lines = [l for l in lines if l and not l.startswith("```") and not l.startswith("#") and not l.startswith(">")]
    if len(lines) < 4:
        sys.exit("内容太短，无法识别标题、主送、正文和落款")
    title = lines[0]
    i = 1
    to = ""
    if lines[1].endswith("：") or lines[1].endswith(":"):
        to, i = lines[1], 2
    note = ""
    if lines[-1].startswith("（联系人"):
        note = lines.pop()
    date, signer = "", ""
    if RE_DATE.match(lines[-1]):
        date = lines.pop()
        signer = lines.pop()
    else:
        print("警告：最后一行不是“YYYY年M月D日”格式的成文日期", file=sys.stderr)
    body, attach = [], []
    for l in lines[i:]:
        if l.startswith("附件：") or (attach and re.match(r"^\d+\.", l)):
            attach.append(l)
        else:
            body.append(l)
    return title, to, body, attach, signer, date, note


def check(title, body, attach, date):
    warns = []
    if re.search(r"[\[［]\d{4}[\]］]|\(\d{4}\)", "\n".join(body)):
        warns.append("发文字号年份应使用六角括号〔〕")
    if date and re.search(r"年0\d月|月0\d日", date):
        warns.append("成文日期月日不应编虚位（如 11月05日 → 11月5日）")
    if len(attach) == 1 and re.match(r"^附件：\s*1[\.．]", attach[0]):
        warns.append("只有一个附件时不编序号")
    for a in attach:
        if re.search(r"[。；，、]$", a):
            warns.append(f"附件名称后不加标点：{a}")
    if re.search(r"[，。；]", title.replace("《", "").replace("》", "")):
        warns.append("标题中一般不用标点")
    if title.endswith("请示") and "妥否" not in "".join(body) and "请予审批" not in "".join(body):
        warns.append("请示缺少规范结语（妥否，请批示）")
    return warns


def build(src, out, seal, cc, issuer, issue_date):
    title, to, body, attach, signer, date, note = parse(open(src, encoding="utf-8").read())
    for w in check(title, body, attach, date):
        print("格式提示：" + w, file=sys.stderr)

    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Mm(210), Mm(297)
    sec.top_margin, sec.bottom_margin = Mm(37), Mm(35)
    sec.left_margin, sec.right_margin = Mm(28), Mm(26)

    para(doc)
    para(doc, title, XBS, ER, WD_ALIGN_PARAGRAPH.CENTER).paragraph_format.line_spacing = Pt(35)
    para(doc)
    if to:
        para(doc, to)
    for l in body:
        body_line(doc, l)
    if attach:
        para(doc)
        for k, a in enumerate(attach):
            para(doc, a if k == 0 else "      " + a, indent_chars=2)
    # 署名与日期
    para(doc)
    para(doc)
    if seal:
        # 加盖印章：日期右空四字，署名以日期为准居中（近似：同样右缩进，居右对齐后再向左偏）
        ps = para(doc, signer, align=WD_ALIGN_PARAGRAPH.RIGHT, right_chars=4 + max(0, (len(date) - len(signer)) // 2))
        pd = para(doc, date, align=WD_ALIGN_PARAGRAPH.RIGHT, right_chars=4)
    else:
        # 不加盖印章：署名右空二字；日期首字比署名首字右移二字
        # 署名右空二字；日期首字比署名首字右移二字 → 日期右缩进 = len(署名) - len(日期)
        # 若日期较长（缩进<2），则日期右空二字、署名相应左移
        d_right = len(signer) - len(date)
        s_right = 2
        if d_right < 2:
            s_right = 2 + (2 - d_right)
            d_right = 2
        para(doc, signer, align=WD_ALIGN_PARAGRAPH.RIGHT, right_chars=s_right)
        para(doc, date, align=WD_ALIGN_PARAGRAPH.RIGHT, right_chars=d_right)
    if note:
        para(doc, note, indent_chars=2)

    # 版记
    if cc or issuer:
        para(doc)
        add_rule(doc, True)
        if cc:
            p = para(doc, cc if cc.endswith("。") else cc + "。", size=SI)
            p.paragraph_format.left_indent = Pt(14)
            p.paragraph_format.right_indent = Pt(14)
            add_rule(doc, False)
        if issuer:
            p = para(doc, size=SI)
            p.paragraph_format.left_indent = Pt(14)
            p.paragraph_format.right_indent = Pt(14)
            p.paragraph_format.tab_stops.add_tab_stop(Mm(156) - Pt(28), alignment=2)
            set_font(p.add_run(f"{issuer}\t{issue_date or date}印发"), FS, SI)
        add_rule(doc, True)

    add_page_number(sec)
    doc.save(out)
    print(f"已生成：{out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="公文纯文本 → GB/T 9704 版式 docx")
    ap.add_argument("src")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--no-seal", action="store_true", help="不加盖印章的版式（署名右空二字）")
    ap.add_argument("--cc", default="", help="抄送，如“抄送：××委，××局。”")
    ap.add_argument("--issuer", default="", help="印发机关，如“××厅办公室”")
    ap.add_argument("--issue-date", default="", help="印发日期，默认同成文日期")
    a = ap.parse_args()
    build(a.src, a.out, not a.no_seal, a.cc, a.issuer, a.issue_date)
