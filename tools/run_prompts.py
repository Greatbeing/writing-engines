#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按 test-prompts.json 的 assertions 自动核对引擎产出。

    python3 tools/run_prompts.py jinyong-writing            # 核对 examples/ 下按题号匹配的稿子
    python3 tools/run_prompts.py --all

支持断言：checker_max / min_chars / length_max / no_regex / any_regex / count_min / count_max；
manual 只列出不判定。字数口径统一用 checker 的 chars（去 markdown 标记、去空白后的字符数，
含标点），与 ai-flavor-checker 报告的「规模」一致。
退出码：0 全过，1 有失败，2 参数错。
"""
import importlib.util,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('aifc',ROOT/'tools'/'ai-flavor-checker.py');aifc=importlib.util.module_from_spec(spec);spec.loader.exec_module(aifc)
CFG=aifc.load_profiles()

def check(a,text,res):
    t=a['type'];v=a.get('value');m=res['measured']
    if t=='checker_max': return res['total']<=v,f"{res['total']} ≤ {v}"
    if t=='min_chars': return m['chars']>=v,f"{m['chars']} ≥ {v}"
    if t=='length_max': return m['chars']<=v,f"{m['chars']} ≤ {v}"
    if t=='no_regex':
        h=re.findall(v,text);return not h,('无命中' if not h else '命中 '+'、'.join(sorted(set(h))[:5]))
    if t=='any_regex': return bool(re.search(v,text)),'有命中' if re.search(v,text) else '无命中'
    if t in('count_min','count_max'):
        pat=a.get('pattern',v);n=len(re.findall(pat,text));lim=a.get('min',a.get('max',a.get('n',v if isinstance(v,int) else 0)))
        return (n>=lim if t=='count_min' else n<=lim),f"{n} vs {lim}"
    return None,a.get('note','')

def run(engine):
    d=ROOT/engine;tp=d/'test-prompts.json'
    if not tp.exists(): print(f'== {engine}: 无 test-prompts.json');return 0
    j=json.loads(tp.read_text(encoding='utf-8'))
    if isinstance(j,list): j={'prompts':j}
    prof=CFG['profiles'].get(engine,CFG['profiles']['generic'])
    fails=0
    for pr in j.get('prompts',[]):
        pid=pr['id'];cand=sorted((d/'examples').glob(f'{pid}*.md')) if (d/'examples').exists() else []
        if not cand: print(f'== {engine}/{pid}: 无产出，跳过');continue
        text=cand[0].read_text(encoding='utf-8');res=aifc.score_text(text,prof)
        print(f'== {engine}/{pid}  {cand[0].name}')
        for a in pr.get('assertions',[]):
            ok,msg=check(a,text,res);mark={True:'PASS',False:'FAIL',None:'MANUAL'}[ok]
            fails+=ok is False;print(f'   [{mark}] {a["type"]}: {msg}')
    return fails

def main(argv=None):
    a=sys.argv[1:] if argv is None else argv
    if not a: print(__doc__);return 2
    engines=[p.parent.name for p in sorted(ROOT.glob('*-writing/test-prompts.json'))] if a[0]=='--all' else a
    f=sum(run(e) for e in engines);print(f'\n失败断言 {f} 条');return 1 if f else 0
if __name__=='__main__': sys.exit(main())