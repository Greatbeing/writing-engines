<p align="center">
  <img src="docs/logo.svg" width="240" alt="Caifeng">
</p>

<h1 align="center">Caifeng · 采风</h1>

<p align="center">[简体中文](README.md) · English</p>

<p align="center"><b>Collect the style. Learn the method. Find your own.</b><br>
<sub>采其风，得其法，自成一体。</sub></p>

<p align="center">Behind every style is a set of rules nobody wrote down. We collect them and build engines out of them.<br>
<a href="https://greatbeing.github.io/writing-engines/en/">Website</a> · writing-engines</p>

> In one line: **a template makes you sound like it; an engine means you don't have to.**

---

## What an engine is

A genre is, at bottom, a set of operating rules its authors never state. What writing classes
teach — "use detail", "show restraint", "sound native to the internet" — is what those rules look
like **after someone has summarized them**, not how they actually run.

This repository does the reverse: it takes a genre apart down to a grain you can execute,
then reassembles the parts into a machine that can write new pieces.

```
engine = atomic techniques × style fingerprint × red-line review
```

Each of the three parts covers one stage, and none can be dropped:

| Part | What it governs | Put another way |
|---|---|---|
| **Atomic techniques** | How the piece gets **thought up** | Cognitive moves, not sentence templates. E.g. "voice the reader's objection first, then give a clear-headed answer" |
| **Style fingerprint** | How the draft gets **checked** | Countable metrics, not "needs tension". E.g. "at least one concrete image every 200 characters" |
| **Red-line review** | What must **never** appear | Hard limits, each paired with a "change it to this" |

- Atoms without a fingerprint → a collection of model essays you can't self-check against
- A fingerprint without atoms → you can grade, but you can't write
- Red lines alone → a prompt template, and you're back where you started

## Why this isn't a prompt template

| | Prompt template | This repository |
|---|---|---|
| What it gives you | What the finished piece **looks like** | How the finished piece **gets made** |
| Can you self-check? | No, only by feel | Fingerprints are countable, red lines checkable, the checker scores |
| Does it grow? | Used once, thrown away | Every real use feeds back; the technique library and word lists keep growing |
| Coverage | One tone of voice | Every component of a genre (topic → structure → sentence → ethics) |

A template makes you sound like it; an engine means you don't have to.

A template is someone else's finished product; an engine is parts in your hands. Once the parts are
broken down to the atomic level, you can assemble things nobody has assembled before —
which is what this repository is ultimately after: not to make you write more like some author,
but to let you write the passage only you could write.

## Engines

| Engine | Genre | Distilled from | Atoms | Status |
|---|---|---|---|---|
| [`sanlian-writing`](sanlian-writing/SKILL.md) | Lived-in city observation (Sanlian Life Lab style, 三联生活实验室体) | 11 pieces (2024–2026) | 21 | Ready |
| [`zhexuan-writing`](zhexuan-writing/SKILL.md) | Official commentary (Zhejiang Propaganda style, 浙江宣传体) | 10 pieces (analysis stored, originals not) | 12 | Ready |
| [`feature-writing`](feature-writing/SKILL.md) | Profile features (*Renwu* magazine style, 《人物》杂志体) | 10 pieces (2020–2023) | 10 | Ready |
| [`gongwen-writing`](gongwen-writing/SKILL.md) | Government official documents (GB/T 9704-2012, 15 statutory types, 公文) | 9 document-type templates | 9 | Ready |
| [`sushi-writing`](sushi-writing/SKILL.md) | Su Shi-style vernacular essays (short prose and letters, 苏轼体) | 13 pieces (public domain) | 10 | Trial |
| [`luxun-writing`](luxun-writing/SKILL.md) | Lu Xun-style essay (鲁迅体杂文) | 14 pieces (public domain) | 10 | Trial |
| [`wangxiaobo-writing`](wangxiaobo-writing/SKILL.md) | Wang Xiaobo-style humorous argument (王小波体) | Analysis only (originals not stored) | 10 | Trial |
| [`zhangailing-writing`](zhangailing-writing/SKILL.md) | Eileen Chang-style prose and fictional description (张爱玲体) | Analysis only (originals not stored) | 10 | Trial |
| [`lijuan-writing`](lijuan-writing/SKILL.md) | Li Juan-style plain-sketch prose (李娟体) | Analysis only (originals not stored) | 10 | Trial |
| [`yuhua-writing`](yuhua-writing/SKILL.md) | Yu Hua-style detached narration (余华体) | Analysis only (originals not stored) | 10 | Trial |
| [`standup-writing`](standup-writing/SKILL.md) | Chinese stand-up comedy scripts (脱口秀稿) | Analysis only (originals not stored) | 10 | Trial |
| [`versailles-writing`](versailles-writing/SKILL.md) | "Versailles" humblebrag (internet genre, 凡尔赛体) | Sentence-pattern analysis (no user posts collected) | 10 | Trial |
| [`guanfang-writing`](guanfang-writing/SKILL.md) | *People's Daily* commentary (人民日报评论体) | Analysis only (originals not stored) | 10 | Trial |
| [`wangzengqi-writing`](wangzengqi-writing/SKILL.md) | Wang Zengqi-style prose (汪曾祺体) | Analysis only (originals not stored) | 10 | Trial |
| [`jinyong-writing`](jinyong-writing/SKILL.md) | Jin Yong-style wuxia narrative (金庸体) | Analysis only (originals not stored) | 10 | Trial |
| [`acheng-writing`](acheng-writing/SKILL.md) | Ah Cheng-style plain-sketch narrative (阿城体) | Analysis only (originals not stored) | 10 | Trial |
| [`mao-writing`](mao-writing/SKILL.md) | Mao Zedong-style argumentative prose (毛泽东文章体) | Analysis only (originals not stored) | 10 | Trial |

There are two tiers: **4 ready** (lived-in / official / feature / official documents — they pass the
contract, pass assertions, have complete output and real-world feedback) + **13 trial** (all seven
sections in place, assertions runnable, but few samples and little feedback so far).
"Ready / trial" is an internal review label, not a ceiling on ability; once the blind evaluation runs,
this tiering will be replaced by win rates.

All 17 engines share one structural contract ([`SPEC.md`](SPEC.md)), and each ships a `test-prompts.json`
with decidable assertions — an engine isn't something that "looks right", it's something that "can be checked".

## Atom library: 182 atoms (18 families + 63 unique)

Lay the atom tables of all 17 engines side by side and the overlap is higher than you'd expect: Lu Xun's
"start from a small thing", Wang Zengqi's "open idly", stand-up's "observational hook", the official
style's "scene hook" — they are the same move. Hence a cross-engine atom library
([`atoms/LIBRARY.md`](atoms/LIBRARY.md), machine-readable version
[`atoms/index.json`](atoms/index.json)):

- **182 atoms** across the engines (17 engines: lived-in 21, official 12, feature 10, official documents 9, 10 each for the rest)
- Tagged and merged into the library: **182 — 18 families, plus 63 unique** (all 17 engines covered; the 19 atoms of `feature-writing` and `gongwen-writing` are included)
- Families hold the **general definition**; engines hold the **variant differences**

In one line: **different authors = different combinations of the same atoms.** A style isn't a different
set of parts; it's the same parts in another order and density. Each engine's atom files stay as they
are, with one added line `**族**：X` (family: X); checks A1–A3 in `tools/lint_skill.py` verify that family
tags match the index — a missing line, a mismatch, or an index entry with no atom file all raise errors.
This isn't a documentation convention; it's an executable check.

## Teaching layer: from recognizing atoms to finding your own

The atom library solves "can it be taken apart", not "how does a person learn it". [`learn/`](learn/README.md)
is the first piece of the teaching layer: three learning tracks — recognize atoms (single moves), see
combinations (an author = a choice and density of atoms), find your own (diagnose your own drafts).
12 recognition exercises, 8 single-atom imitations, 4 combination exercises, and a diagnostic tool
[`tools/diagnose.py`](tools/diagnose.py). Each step has a time estimate, a deliverable, and a decidable
pass criterion; all practice material comes from the repository's `examples/`, with paths noted, and
no copyrighted originals are quoted.

## Installation

The `SKILL.md` + frontmatter format is generic; OpenClaw is used as the example below:

```bash
git clone https://github.com/Greatbeing/writing-engines.git
cp -r writing-engines/sanlian-writing \
      writing-engines/zhexuan-writing \
      writing-engines/feature-writing \
      writing-engines/gongwen-writing \
      writing-engines/sushi-writing \
      writing-engines/luxun-writing \
      writing-engines/wangxiaobo-writing \
      writing-engines/zhangailing-writing \
      writing-engines/lijuan-writing \
      writing-engines/yuhua-writing \
      writing-engines/standup-writing \
      writing-engines/guanfang-writing \
      writing-engines/wangzengqi-writing \
      writing-engines/jinyong-writing \
      writing-engines/mao-writing \
      ~/.openclaw/workspace/skills/
```

Claude Code or any other host that supports `SKILL.md`: put the engine directories in the matching
skills path. Each directory is self-contained with no code dependencies — copy it in and it works.

## Usage

One-line request in, one piece out. Each engine carries its own trigger phrases and "not applicable" routing:

| Engine | Requests that mean "use this" | Requests that mean "don't use this" |
|---|---|---|
| Lived-in | WeChat articles / city observation / avoiding an AI tone / internet-native copy | Features needing named interviews, government commentary |
| Official | Commentary / political essays / mainstream themes / viral pieces inside the system | Casual essays, conversational observation pieces |
| Feature | Profile features / in-depth reporting / group portraits | Only second-hand accounts, no scene, no interviews |
| Official documents | Notices / reports / requests for instructions / letters / meeting minutes, or conversion to national-standard docx | Party-paper commentary, new-media commentary |
| *People's Daily* commentary | Editorials / commentator articles / *People's* commentary, "raising the stance" of a piece | Official documents, essays, features, impersonating a *People's Daily* byline |
| Lu Xun-style | Essays / short commentary / social criticism, sharpening a lukewarm opinion piece | Official commentary, relaxed essays, pastiche of Republican-era prose |

The other 9 engines each carry trigger phrases and "not applicable" routing in the `description` of their
`SKILL.md` (3–4 trigger branches, one not-applicable route). These rows aren't the full list — just the
most common cases to start with.

All 17 engines also work **in reverse**: give one an existing piece and it breaks it down along its atom
chain and runs a red-line check, telling you which moves the piece uses, where it slips, and how to fix it.

## Building an engine

This is the real point of the repository: **engines aren't collected; they're built.**

```
sample (10+ representative pieces) → dissect (enumerate atomic techniques) → compress (style fingerprint + red lines)
→ field-test (verify on real pieces) → feed back (write feedback into the technique library)
```

Step three, "compress", used to have no defined output, so the first three engines grew three different
structures. Now it has one: [`SPEC.md`](SPEC.md) specifies the seven-section structure, size limits
(counted in characters, not bytes), and how the description, red lines and fingerprint are each written.
`tools/lint_skill.py` makes it executable.

To contribute a new engine, it must clear four entry criteria ([`CONTRIBUTING.md`](CONTRIBUTING.md)):

1. A corpus of ≥ 10 pieces from the same source, traceable, **no full texts stored** (see [`sources/INDEX.md`](sources/INDEX.md))
2. ≥ 8 atomic techniques, each cross-validated on ≥ 2 pieces
3. Pass the `eval` blind evaluation: a significant win rate over the bare model, and distinguishable from other engines
4. Pass `python3 tools/lint_skill.py <engine> --strict`

Criterion 3 is the only one you can't pass on writing skill. If an engine falls short, fix the engine;
don't lower the bar — **one engine that can't pass blind evaluation dilutes the credibility of the whole library.**

## Tools

| Tool | What it does |
|---|---|
| [`tools/ai-flavor-checker.py`](tools/ai-flavor-checker.py) | AI-tone scoring (v0.2, scored **per engine**, usable as a gate) |
| [`tools/lint_skill.py`](tools/lint_skill.py) | Checks engines against `SPEC.md` (eleven checks E1–E11 + A1–A3 atom family tags; `--strict` is the entry bar) |
| [`tools/run_prompts.py`](tools/run_prompts.py) | Checks `examples/` output against the assertions in each engine's `test-prompts.json`; `--all` runs the whole library |
| [`tools/tests/test_checker.py`](tools/tests/test_checker.py) | Regression tests for the checker (18 assertions) |
| [`tools/build_articles.py`](tools/build_articles.py) | Builds engine `examples/*.md` into website article pages under `docs/articles/` |
| [`tools/build_compare.py`](tools/build_compare.py) | Builds the four versions in `demo/<id>/` into side-by-side pages under `docs/compare/` |
| [`tools/maint/`](tools/maint/README.md) | Daily maintenance: site consistency build, six health checks, weekly report (scheduled on two cloud machines) |
| [`tools/agents/`](tools/agents/README.md) | Usage guide and unified entry point for four agents (DSH/Claude/codex/opencode) |
| [`tools/daily/`](tools/daily/README.md) | Daily automated writing pipeline (draft + independent review) |

```bash
python3 tools/ai-flavor-checker.py --engine sanlian-writing article.md
python3 tools/lint_skill.py --all
python3 tools/run_prompts.py --all
python3 tools/tests/test_checker.py
```

The key point: **the same device carries different weight in different genres.** "Heavy use of quoted
interview speech" is a signature device in the lived-in style (a plus) and noise in a feature; "not A but B"
is an atom in the lived-in and official styles but should be restrained in a feature. v0.1 used one global
word list and penalized both — the evaluator was working against its own engines.
Details in [`tools/README.md`](tools/README.md).

## Evaluation

[`eval/`](eval/README.md) is a blind-evaluation pipeline that is already in place:

```
10 prompts × 4 versions (bare model + 3 engines) = 40 pieces
× 2 raters per prompt, ranking blind (they only see file names like t01/A.md)
→ win rate / distinguishability / inter-rater agreement
```

The procedure, prompts, shared material pack, leak blocking, aggregation scripts and criteria are all written.
**The first round hasn't run yet**; [`eval/RESULTS.md`](eval/RESULTS.md) is all `TBD` —
so there is no number yet for "how much better is it with an engine than without".

To be clear about scope: the first round ranks only 3 mature engines (lived-in / official / feature);
the other 14 engines **have never been evaluated**. So current evaluation evidence covers 3/17 engines,
and all 182 atoms in the library (18 families, plus 63 unique) were written to a checkable spec, not selected by win rate.

The criteria were fixed in advance, including a self-falsification condition:

> If the outputs of these three engines can't be told apart in the first round (H2 fails), then the claim
> "an operating system for genres" should be downgraded to "one general writing engine with three emphases".

Set the falsification condition first, then look at the data. Otherwise any data can be explained away.

## Roadmap

Ordered by "every step leaves something to show", not by "what we'd like to do".

Done:

- [x] 17 engines (lived-in 21 atoms / official 12 / feature 10 / official documents 9 / 10 each for the rest)
- [x] Engine contract `SPEC.md` + compliance checker (E1–E11 + A1–A3)
- [x] Cross-engine atom library `atoms/`: 182 atoms (18 families + 63 unique), family tags guarded by lint
- [x] checker v0.2 (per-engine scoring) + regression tests (18 assertions)
- [x] Full checker calibration (21 originals as negative samples: "the original must clear its own engine's bar")
- [x] Toolchain: `lint_skill` / `run_prompts` / `build_articles` / `build_compare` / `check_quotes`
- [x] Same-prompt, four-style demo (5 prompts × 4 versions, `docs/compare/`) — a showcase, not an evaluation

Not done:

- [ ] **First round of `eval` blind evaluation** ← the only thing currently in progress (3 engines, not 17)
- [ ] Extend blind evaluation to 17 engines (including cross-family comparison: how the same atom family behaves in different genres)
- [x] First piece of the teaching layer: [`learn/`](learn/README.md) — three learning tracks, 12 recognition exercises, 8 imitations,
      4 combination exercises, diagnostic tool `tools/diagnose.py` (exercise evaluation and iteration data still to come)
- [ ] Source verification: quotations in the engines for in-copyright authors — Jin Yong, Yu Hua, Li Juan, Eileen Chang, Wang Xiaobo,
      Wang Zengqi, Mao's Selected Works and others — are all "not verified word for word"; `tools/check_quotes.py` can only catch fabrication within the material, not against the originals

## License and corpus

- **All original content** (SKILL.md, references/, the atoms/ library, SPEC, eval, tools code): **MIT** —
  see [`LICENSE`](LICENSE). Use it freely, commercially included; just keep the attribution and license notice.
  Scope and third-party material are explained in [`NOTICE.md`](NOTICE.md).
- **Third-party articles**: no full texts are included, only bibliographic metadata and technique mappings; each
  example is ≤ 50 characters and cites its source. Copyright belongs to the original authors and first publishers and is
  **outside the scope of this repository's license**. See [`sources/INDEX.md`](sources/INDEX.md)

The cost of MIT, stated plainly: **others can take these engines and build courses or competing products.** That is a
deliberate choice — let it get used first, then pull ahead on evidence, data and quality of delivery, not on license terms.

---

*Techniques are original; distillation material comes from public reporting and is quoted only for commentary and teaching.*