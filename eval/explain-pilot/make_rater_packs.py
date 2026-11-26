# -*- coding: utf-8 -*-
"""把盲评包拼成每位评分者一份纯文本（只含原稿与 X/Y，无条件信息）。"""
import json
from pathlib import Path
H = Path(__file__).resolve().parent
t = json.loads((H / 'tasks.json').read_text(encoding='utf-8'))
a = json.loads((H / 'assign.json').read_text(encoding='utf-8'))
D = {'luxun.1': '从一个具体、能拍照或录音的小东西起笔，再由它剖出大问题，而不是一句话跳到大词',
     'luxun.9': '该煽情处不煽情，只写动作、时间、数字，少用形容词与感叹',
     'versailles.10': '结尾收在一声叹气或一个疲惫情绪上，不总结、不自己点破'}
for R in ['R1', 'R2', 'R3']:
    s = []
    for it in t['items']:
        pid = it['id']
        if R not in a[pid]:
            continue
        d = H / 'blind' / R / pid
        draft = it['draft'].replace('\n\n（综合创作）', '')
        s.append(f"### 题 {pid}\n评判的目标写法：{D[it['atom']]}\n【原稿】\n{draft}\n【X】\n"
                 + (d / 'X.md').read_text(encoding='utf-8').strip()
                 + "\n【Y】\n" + (d / 'Y.md').read_text(encoding='utf-8').strip())
    (H / 'blind' / f'{R}_pack.md').write_text('\n\n'.join(s), encoding='utf-8')
    print(R, len(s))
