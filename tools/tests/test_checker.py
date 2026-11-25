#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
checker v0.2 的回归测试。

跑法：
    python3 tools/tests/test_checker.py

三个层次：
1. 黄金样本：一段真·人类散文（0-30 分），一段真·AI 腔（≥45 分）。
2. 文体感知：同一段文本在不同引擎下的分数关系必须符合设计意图。
   —— 这是 v0.1 完全缺失的一类断言，也是「文体感知评分」的最小证明。
3. 语料回归（可选）：若 tools/tests/fixtures/local/ 下有 21 篇原文，
   逐篇断言全部低于各自引擎门槛。原文受版权保护，不入库，见 sources/INDEX.md。

说明：本文件在无 Python 沙箱内写成，未经实际执行。合并前请先跑一次。
"""

import importlib.util
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
SCRIPT = TOOLS / "ai-flavor-checker.py"


def load_checker():
    spec = importlib.util.spec_from_file_location("aifc", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


aifc = load_checker()
PROFILES = aifc.load_profiles()["profiles"]


# ------------------------------------------------------------------ 黄金样本
HUMAN_LIKE = (
    "楼下修鞋的老周，最近把摊子挪到了地铁口。他说这边人多，一天能多修七八双。"
    "我问他冷不冷，他指指脚边一个暖水瓶，说其实这玩意儿比棉裤管用。摊子上压着块木板，"
    "用红漆写着修鞋修伞改衣，字已经掉了一半。有人拿来一只断跟的单鞋，他翻过来看看，"
    "说粘一下还能穿，别扔。"
)

AI_LIKE = (
    "在当今这个快速变化的时代，我们不难发现，效率已经成为衡量一切价值的重要维度。"
    "值得注意的是，这种转变并非偶然，而是深刻反映了社会结构的底层逻辑。因此，"
    "我们需要重新审视个体与系统之间的关系，从而在更高层面上实现对齐与赋能。"
)

# 引号访谈密集 + 不是A而是B 的活人感典型段落，用来验证「不能惩罚自家装置」
HUMAN_VOICE_DEVICES = (
    "「我一个月工资七千，房租两千八。」沪漂零零后响响说，"
    "「剩下的钱，全花在让自己看起来不像打工人上。」"
    "不是说年轻人不爱存钱，而是这个城市先把他们的钱花掉了。"
    "「你看这个杯子，」她举起来，「三十块，能让我高兴一个礼拜。」"
    "不是因为它便宜，而是因为它是我自己挑的。"
)


class TestGoldenSamples(unittest.TestCase):
    def test_human_like_scores_low(self):
        res = aifc.score_text(HUMAN_LIKE, PROFILES["generic"])
        self.assertLess(res["total"], 30, f"人类散文被判 AI 味：{res['total']}")

    def test_ai_like_scores_high(self):
        res = aifc.score_text(AI_LIKE, PROFILES["generic"])
        self.assertGreaterEqual(res["total"], 45, f"AI 腔漏检：{res['total']}")

    def test_selftest_exit_zero(self):
        self.assertEqual(aifc.selftest(), 0)


class TestEngineAwareness(unittest.TestCase):
    """同一段文本，不同引擎应当给出不同的分。v0.1 在这里必然失败。"""

    def test_quote_and_formula_not_penalised_for_human_voice(self):
        """活人感的引号访谈 + 不是A而是B，不能成为扣分项。"""
        hv = aifc.score_text(HUMAN_VOICE_DEVICES, PROFILES["human-voice-writing"])
        gen = aifc.score_text(HUMAN_VOICE_DEVICES, PROFILES["generic"])
        # 同一段话，活人感引擎的判定必须比通用引擎更宽松（或至少不更严）
        self.assertLessEqual(
            hv["total"], gen["total"] + 1e-9,
            f"活人感引擎反而更严：hv={hv['total']} generic={gen['total']}",
        )
        self.assertTrue(
            hv["passed"],
            f"自家签名装置被判不合格：{hv['total']} / 门槛 {PROFILES['human-voice-writing']['pass_below']}",
        )

    def test_formula_penalty_exempted_only_where_declared(self):
        """formula 权重：活人感/官方体为 0，特稿/通用 > 0。"""
        self.assertEqual(PROFILES["human-voice-writing"]["penalty"]["formula"], 0.0)
        self.assertEqual(PROFILES["guanfang-writing"]["penalty"]["formula"], 0.0)
        self.assertGreater(PROFILES["feature-writing"]["penalty"]["formula"], 0.0)

    def test_official_body_threshold_is_wider(self):
        """官方体自带书面腔：门槛必须比活人感宽，否则整文体被误杀。"""
        self.assertGreater(
            PROFILES["guanfang-writing"]["pass_below"],
            PROFILES["human-voice-writing"]["pass_below"],
        )

    def test_feature_writing_gets_no_colloquial_credit(self):
        """特稿禁用口语词，口语抵充必须归零。"""
        self.assertEqual(PROFILES["feature-writing"]["reward"]["colloquial"], 0.0)

    def test_long_sentence_is_length_independent(self):
        """长句惩罚只看占比，不看绝对条数——v0.1 的核心口径 bug。"""
        unit = "这是一句长度超过六十个字的句子，用来验证长句惩罚是否与文章总长度无关，它需要足够长才能被计入长句统计，因此这里继续补充字数直到超过六十。"
        short = unit * 2                      # 2 句，全是长句 → 占比 100%
        long = unit * 2 + "短句。短句。短句。短句。短句。短句。"  # 占比被摊薄
        s1 = aifc.score_text(short, PROFILES["generic"])["raw"]["long"]
        s2 = aifc.score_text(long, PROFILES["generic"])["raw"]["long"]
        self.assertGreater(s1, s2, "长句分数未随占比下降，仍是绝对计数")

    def test_short_text_not_inflated(self):
        """不足 400 字按 400 归一：短文里一个「因此」不该直接炸分。"""
        tiny = "因此，我走了。"
        res = aifc.score_text(tiny, PROFILES["generic"])
        self.assertLess(res["total"], 20, f"短文本密度虚高：{res['total']}")


class TestMechanics(unittest.TestCase):
    def test_parallel_run_ignores_coincidental_tails(self):
        """三句都以「了」结尾、长度悬殊，不算排比。

        这是 v0.1 的误报来源：只看结尾一个字。
        """
        text = ("他走了。他这件事情从头到尾都很复杂并且牵涉到很多人的利益与选择，"
                "最终结束了。他来了。")
        run = aifc.max_parallel_run(aifc.split_sentences(text))
        self.assertEqual(run, 1, f"误判排比：run={run}")

    def test_parallel_run_detects_repeated_suffix(self):
        """「春天来了／夏天来了／秋天来了」——首字不同、后缀重复，是最常见的排比。

        上一版只看「首字 + 尾字」，这一组会被整体漏掉，所以这条用例是有意义的。
        """
        text = "春天来了。夏天来了。秋天来了。"
        run = aifc.max_parallel_run(aifc.split_sentences(text))
        self.assertGreaterEqual(run, 3, f"漏检排比：run={run}")

    def test_parallel_run_detects_repeated_prefix(self):
        text = "不是因为他怕输。不是因为他懒惰。不是因为他没钱。"
        run = aifc.max_parallel_run(aifc.split_sentences(text))
        self.assertGreaterEqual(run, 3, f"漏检排比：run={run}")

    def test_parallel_run_tolerates_single_char_repetition(self):
        """单字重复不算排比（已知局限，刻意的）：宁可漏检不误报。"""
        text = "他来了。她笑了。天亮了。"
        run = aifc.max_parallel_run(aifc.split_sentences(text))
        self.assertEqual(run, 1, f"单字重复被误判为排比：run={run}")

    def test_empty_text_returns_none(self):
        self.assertIsNone(aifc.score_text("   \n\n  ", PROFILES["generic"]))

    def test_all_profiles_have_complete_weight_tables(self):
        need_p = set(aifc.CAPS)
        need_r = set(aifc.REWARD_CAPS)
        for name, p in PROFILES.items():
            with self.subTest(profile=name):
                self.assertTrue(need_p.issubset(p["penalty"]), f"{name} 缺 penalty 项")
                self.assertTrue(need_r.issubset(p["reward"]), f"{name} 缺 reward 项")
                self.assertIn("pass_below", p)
                self.assertIn("label", p)


# ------------------------------------------------------------ 可选：语料回归
LOCAL = HERE / "fixtures" / "local"


@unittest.skipUnless(LOCAL.is_dir() and any(LOCAL.glob("*.txt")),
                     "无本地语料（见 sources/INDEX.md 第四节）；跳过语料回归")
class TestCorpusRegression(unittest.TestCase):
    """最重要的一条：原文不能过不了自家的门槛。

    原文是自备的、不入库的。把 21 篇放进 tools/tests/fixtures/local/ 即可启用。
    """

    def test_human_voice_corpus_passes(self):
        engine = "human-voice-writing"
        prof = PROFILES[engine]
        for path in sorted((LOCAL).glob("三联*.txt")):
            with self.subTest(file=path.name):
                res = aifc.score_text(path.read_text(encoding="utf-8"), prof)
                self.assertLess(
                    res["total"], prof["pass_below"],
                    f"{path.name} 得分 {res['total']}，超过 {engine} 门槛",
                )

    def test_registered_engine_corpus_passes(self):
        """v0.3 登记的各引擎：fixtures/local/<engine 前缀>-<n>.txt 必须过自家门槛。

        首行是来源注释（# 来源：URL），不计入打分。
        """
        for path in sorted(LOCAL.glob("*-[0-9].txt")):
            engine = path.stem.rsplit("-", 1)[0] + "-writing"
            if engine not in PROFILES:
                continue
            prof = PROFILES[engine]
            lines = path.read_text(encoding="utf-8").splitlines()
            body = "\n".join(l for l in lines if not l.startswith("# 来源"))
            with self.subTest(file=path.name):
                res = aifc.score_text(body, prof)
                self.assertLess(
                    res["total"], prof["pass_below"],
                    f"{path.name} 得分 {res['total']}，超过 {engine} 门槛",
                )

    def test_feature_corpus_passes(self):
        engine = "feature-writing"
        prof = PROFILES[engine]
        for path in sorted((LOCAL).glob("人物*.txt")):
            with self.subTest(file=path.name):
                res = aifc.score_text(path.read_text(encoding="utf-8"), prof)
                self.assertLess(
                    res["total"], prof["pass_below"],
                    f"{path.name} 得分 {res['total']}，超过 {engine} 门槛",
                )


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False, verbosity=2).result.wasSuccessful() else 1)
