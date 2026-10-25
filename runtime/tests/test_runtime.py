"""python -m unittest discover -s runtime/tests -v   (final-mvp 에서, PYTHONPATH=runtime, jsonschema 필요)"""
import json
import os
import shutil
import types
import unittest

from cardstudio import contracts
from cardstudio.agent_runner import AgentRunner, NeedsHuman
from cardstudio.config import AGENT_DIR, MVP, Settings
from cardstudio.events import EventBus
from cardstudio.llm.anthropic_provider import AnthropicProvider
from cardstudio.llm.base import CallSpec, LLMResult, ToolSpec
from cardstudio.orchestrator import Orchestrator

GENZ = f"{MVP}/scenarios/genz-credit"


def refs(node, acc):
    if isinstance(node, dict):
        if "$ref" in node:
            acc.append(node["$ref"])
        for v in node.values():
            refs(v, acc)
    elif isinstance(node, list):
        for v in node:
            refs(v, acc)
    return acc


class SchemaTests(unittest.TestCase):
    def test_llm_output_schema_is_self_contained_and_accepts_recorded_results(self):
        from jsonschema import Draft202012Validator
        for agent, folder in AGENT_DIR.items():
            sc = contracts.llm_output_schema(agent)
            Draft202012Validator.check_schema(sc)
            bad = [r for r in refs(sc, []) if not r.startswith("#/$defs/")]
            self.assertEqual(bad, [], f"{agent}: 외부 $ref 남음")
            DISC = {"scout": "scout.stats", "gap_analyst": "gap.touchpoint", "ideator": "idea.growth", "critic": "crit.idea.risk"}
            if agent == "labeler":
                continue        # 라벨링 기록은 전역 맵이라 봉투 기록이 없다
            path = f"{MVP}/scenarios/genz-discovery/discovery/{DISC[agent]}/out.json" if agent in DISC else f"{GENZ}/{folder}/out.json"
            rec = json.load(open(path, encoding="utf-8"))
            llm_part = {k: v for k, v in rec.items() if k not in contracts.CODE_OWNED}
            errs = list(Draft202012Validator(sc).iter_errors(llm_part))
            self.assertEqual([e.message[:120] for e in errs[:3]], [], f"{agent}: 기록된 출력이 LLM 스키마를 통과하지 못함")


class FakeAnthropic:
    """messages.create 를 스크립트로 흉내. 1턴: web_search 호출, 2턴: submit_output."""

    def __init__(self, final):
        self.final, self.n = final, 0
        self.messages = self

    def create(self, **kw):
        self.n += 1
        u = types.SimpleNamespace(input_tokens=10, output_tokens=5, cache_read_input_tokens=0)
        if self.n == 1:
            blk = types.SimpleNamespace(type="tool_use", id="t1", name="web_search", input={"query": "q"})
        else:
            blk = types.SimpleNamespace(type="tool_use", id="t2", name="submit_output", input=self.final)
        return types.SimpleNamespace(content=[blk], usage=u)


class ProviderTests(unittest.TestCase):
    def test_tool_loop_collects_urls_and_returns_submit(self):
        tool = ToolSpec("web_search", "d", {"type": "object"}, lambda a: {"results": [{"url": "https://a.test/x"}]})
        spec = CallSpec(agent="trend", model="m", system="s", user="u", output_schema={"type": "object"}, tools=[tool], max_tool_calls=3)
        res = AnthropicProvider(client=FakeAnthropic({"ok": 1})).generate(spec)
        self.assertEqual(res.output, {"ok": 1})
        self.assertEqual(res.tool_calls, 1)
        self.assertEqual(res.tool_urls, ["https://a.test/x"])


def toy_world():
    sc = {"scope": {"target_segment": "a", "constraints": ["투자 연계 제외"]}, "need_labels": {"x": "엑스", "y": "와이", "invest": "투자"},
          "need_tag_map": {"x": ["crowd", "white"], "y": ["other"], "invest": ["invest_reward"]},
          "trend_topic_need_map": {"topic_x": ["x"]},
          "categories": {"dining": "외식", "online": "온라인"},
          "segments": [{"id": "a", "name": "A", "complexity_tolerance": 0.5, "monthly_spend": {"dining": 20, "online": 10},
                        "need_weights": {"x": 0.8, "y": 0.8, "invest": 0.9}}]}
    cards = [{"name": f"c{i}", "tags": ["crowd", "other"]} for i in range(10)]
    tags = {"crowd": "혼잡", "white": "공백", "other": "기타", "invest_reward": "투자"}
    trend = [{"id": "T1", "topic": "topic_x", "strength": 0.8, "reliability": 0.8}]
    return sc, cards, tags, trend


class OpportunityTests(unittest.TestCase):
    def run_engine(self, ceiling=0.6):
        from cardstudio.opportunity import find_areas
        sc, cards, tags, trend = toy_world()
        return find_areas(sc=sc, db_cards=cards, allowed_tags=tags, trend=trend, consumer={"top_needs": [{"need": "x", "priority": 1}]},
                          tensions=[], ceiling_fn=lambda seg, t, d: ceiling, target_adopt=0.38)

    def test_white_mechanism_beats_crowded_one_and_excluded_need_is_absent(self):
        areas = self.run_engine()
        ids = [a["id"] for a in areas]
        best_x = next(a for a in areas if a["need"] == "x")
        self.assertIn("white", best_x["mechanisms"])           # 비어 있는 방식이 포화된 방식보다 먼저
        self.assertFalse(any(a["need"] == "invest" for a in areas))
        self.assertTrue(all(0 <= a["score"] <= 1 and "parts" in a and a["evidence_ids"] for a in areas))

    def test_low_feasibility_pulls_score_down_and_is_flagged(self):
        hi, lo = self.run_engine(0.6), self.run_engine(0.1)
        f = lambda xs: next(a for a in xs if a["mechanisms"] == ["white"])
        self.assertLess(f(lo)["score"], f(hi)["score"])
        self.assertFalse(f(lo)["feasible"])
        self.assertTrue(f(hi)["feasible"])

    def test_domain_axis_and_pairs(self):
        areas = self.run_engine()
        self.assertTrue(any(a["domain"] for a in areas))                     # 혜택 영역 축이 쓰인다
        self.assertTrue(all(len(a["mechanisms"]) <= 2 for a in areas))
        self.assertTrue(all(a["id"].endswith(a["domain"]) for a in areas if a["domain"]))

    def test_deterministic(self):
        self.assertEqual(self.run_engine(), self.run_engine())


class WhitespaceV2ValidatorTests(unittest.TestCase):
    cell = {"id": "A-a-x-white", "seg": "a", "need": "x", "mechanisms": ["white"], "domain": "online", "confidence": "medium"}

    def env(self, **over):
        pick = {"rank": 1, "seg": "a", "need": "x", "area_id": "A-a-x-white", "mechanisms": ["white"], "domain": "online", "statement": "s", "unmet_gap": "g",
                "why_now": "w", "hypotheses_to_validate": ["h"], "kill_criteria": "k", "confidence": "medium", "origin": "score"}
        pick.update(over)
        picks = [pick, dict(pick, rank=2, need="y"), dict(pick, rank=3, need="z")]
        return {"payload": {"cells_top": [self.cell]}}, {"result": {"picks": picks}}

    def test_ok(self):
        from cardstudio.validators import check_whitespace_v2
        # 1번 pick 은 문제가 없어야 한다(2·3번은 시험용으로 area_id 가 같아 별도 오류가 날 수 있다)
        self.assertEqual([e for e in check_whitespace_v2(*self.env()) if e[1].startswith("picks/1")], [])

    def test_catches_missing_fields_unknown_mechanism_and_overconfidence(self):
        from cardstudio.validators import check_whitespace_v2
        codes = lambda **o: {e[0] for e in check_whitespace_v2(*self.env(**o)) if e[1].startswith("picks/1")}
        self.assertIn("SECTION_MISSING", codes(kill_criteria=""))
        self.assertIn("ENUM_UNKNOWN", codes(mechanisms=["nope"]))
        self.assertIn("GATE_FAILED", codes(confidence="high"))
        self.assertIn("ID_UNKNOWN", codes(domain="dining"))                # 영역의 혜택 영역과 다름(WS-R14)
        self.assertIn("NUMBER_NOT_IN_INPUT", codes(statement="채택 77.7% 가능"))

    def test_diversity(self):
        from cardstudio.validators import check_whitespace_v2
        i, o = self.env()
        for p in o["result"]["picks"]:
            p["need"] = "x"
        self.assertTrue(any(e[0] == "COUNT_OUT_OF_RANGE" for e in check_whitespace_v2(i, o)))


class EvidenceTests(unittest.TestCase):
    def store(self):
        from cardstudio.evidence import EvidenceStore
        items = [{"id": "A1", "kind": "fact", "text": "t1", "needs": ["x"], "tags": ["white"], "domains": ["dining"], "age_scope": "20대", "confidence": "high"},
                 {"id": "A2", "kind": "fact", "text": "t2", "needs": ["x"], "tags": [], "domains": [], "age_scope": "전연령", "confidence": "low", "stale": True},
                 {"id": "A3", "kind": "constraint", "text": "rule", "needs": ["invest"], "tags": [], "domains": []},
                 {"id": "A4", "kind": "fact", "text": "t4", "needs": ["y"], "tags": [], "domains": []}]
        cards = [{"id": "c1", "name": "카드1", "issuer": "i", "type": "credit", "tags": ["white", "crowd"]}, {"id": "c2", "name": "카드2", "issuer": "i", "type": "credit", "tags": ["crowd"]}]
        return EvidenceStore(items, cards)

    def test_slice_ranks_by_label_overlap_and_is_deterministic(self):
        st = self.store()
        got = st.slice(need="x", mechanisms=["white"], domain="dining", k=5)
        self.assertEqual([e["id"] for e in got], ["ev:A1", "ev:A2"])         # y/invest 항목은 관련 없어 빠진다
        self.assertEqual(got, st.slice(need="x", mechanisms=["white"], domain="dining", k=5))
        self.assertEqual([e["id"] for e in st.slice(need="invest", kinds={"constraint"})], ["ev:A3"])

    def test_nearest_cards(self):
        self.assertEqual(self.store().nearest_cards(["white"], k=2)[0]["name"], "카드1")


class ConceptEvidenceValidatorTests(unittest.TestCase):
    def env(self, **opt):
        o = {"cvp": {"alternative": "카드1 혜택", "reason_to_believe": "ev:A1 근거"}, "evidence_ids": ["ev:A1"], "links": [], "mechanics": ["x"]}
        o.update(opt)
        return {"payload": {"evidence": [{"id": "ev:A1"}], "competitor_refs": [{"name": "카드1", "official_name": None}], "invest_rules": []}}, {"result": {"options": [o]}}

    def test_ok_and_failures(self):
        from cardstudio.validators import check_concept_v2
        self.assertEqual(check_concept_v2(*self.env()), [])
        bad_alt = self.env(cvp={"alternative": "다른 카드", "reason_to_believe": "ev:A1"})
        self.assertTrue(any("CO-R12" in e[2] for e in check_concept_v2(*bad_alt)))
        unknown = self.env(evidence_ids=["ev:ZZ"])
        self.assertTrue(any(e[0] == "ID_UNKNOWN" for e in check_concept_v2(*unknown)))
        no_rule = self.env(links=["sec"])
        self.assertTrue(any(e[0] == "GATE_FAILED" for e in check_concept_v2(*no_rule)))


class TallyTests(unittest.TestCase):
    def checks(self, grades):
        return [{"subject_id": k, "vote": "weaken", "grade": g, "findings": ["f"], "confidence_in_vote": "medium"} for k, g in grades.items()]

    def test_any_lens_kill_drops_and_median_ranks(self):
        from cardstudio.tally import tally
        subs = [{"id": "A"}, {"id": "B"}, {"id": "C"}]
        by = {"existing": [self.checks({"A": "중", "B": "폐기", "C": "약"})], "evidence": [self.checks({"A": "중", "B": "중", "C": "약"})],
              "risk": [self.checks({"A": "약", "B": "중", "C": "약"})]}
        t = tally(subs, by, kind="gap")
        rows = {r["id"]: r for r in t["rows"]}
        self.assertTrue(rows["B"]["dropped"] and rows["B"]["killed_by"] == ["existing"])
        self.assertEqual([r["id"] for r in t["ranked"]], ["A", "C"])
        self.assertEqual(rows["A"]["tier"], "유력(중)")        # 등급 중앙값 2
        self.assertEqual(rows["C"]["tier"], "후보(약)")

    def test_ensemble_in_one_lens_needs_majority_to_kill(self):
        from cardstudio.tally import tally
        by = {"risk": [self.checks({"A": "폐기"}), self.checks({"A": "중"}), self.checks({"A": "중"})]}
        t = tally([{"id": "A"}], by, kind="gap")
        self.assertFalse(t["rows"][0]["dropped"])               # 3명 중 1명만 폐기 → 렌즈 안에서는 중앙값
        by = {"risk": [self.checks({"A": "폐기"}), self.checks({"A": "폐기"}), self.checks({"A": "중"})]}
        self.assertTrue(tally([{"id": "A"}], by, kind="gap")["rows"][0]["dropped"])

    def test_merge_needs_two_duplicate_votes_or_explicit(self):
        from cardstudio.tally import tally
        subs = [{"id": "A"}, {"id": "B"}]
        c1 = self.checks({"A": "중", "B": "중"}); c1[1]["lens_fields"] = {"duplicate_of": "A"}
        c2 = self.checks({"A": "중", "B": "중"}); c2[1]["lens_fields"] = {"duplicate_of": "A"}
        t = tally(subs, {"x": [c1], "y": [c2]}, kind="idea")
        self.assertEqual(t["rows"][1]["merged_into"], "A")
        t = tally(subs, {"x": [c1]}, kind="idea")                 # 1표만으로는 병합하지 않는다
        self.assertIsNone(t["rows"][1]["merged_into"])
        self.assertEqual(tally(subs, {"x": [c1]}, merge={"A": ["B"]}, kind="idea")["rows"][1]["merged_into"], "A")


class EnsembleTests(unittest.TestCase):
    def test_labeler_keeps_majority_labels_only(self):
        from cardstudio.ensemble import merge_results
        mk = lambda needs: {"model": "m", "result": {"labels": {"i1": {"needs": needs, "tags": [], "domains": [], "relevance": "direct"}}}}
        out = merge_results("labeler", [mk(["saving", "control"]), mk(["saving"]), mk(["control", "saving"])])
        self.assertEqual(out["result"]["labels"]["i1"]["needs"], ["control", "saving"])
        out = merge_results("labeler", [mk(["saving"]), mk(["social"]), mk(["control"])])
        self.assertEqual(out["result"]["labels"]["i1"]["needs"], [])           # 과반이 없으면 비운다

    def test_critic_ensemble_keeps_every_vote_and_variant_prefix(self):
        from cardstudio.ensemble import merge_results, variant_prefix
        mk = lambda g: {"model": "m", "result": {"checks": [{"subject_id": "A", "vote": "weaken", "grade": g, "findings": ["f"], "confidence_in_vote": "low"}]}}
        out = merge_results("critic", [mk("중"), mk("약")])
        self.assertEqual([c["grade"] for c in out["result"]["checks"]], ["중", "약"])
        self.assertEqual((variant_prefix("LN", 0), variant_prefix("LN", 1), variant_prefix("LNA", 1)), ("LNA", "LNB", "LNB"))


class DiscoveryValidatorTests(unittest.TestCase):
    def test_gap_analyst_rules(self):
        from cardstudio.validators import check_discovery
        cand = lambda **o: dict({"id": "X1", "genz_basis": [{"fact_id": "ev:F1"}], "existing_check": {"db_cards_compared": ["a", "b", "c"], "verdict": "none"},
                                 "mechanism_tags": ["t1"], "need_key": "saving"}, **o)
        pl = {"evidence": [{"id": "ev:F1"}], "competitor_cards": [{"name": n} for n in "abc"], "allowed_tags": {"t1": "x"}, "need_labels": {"saving": "s"},
              "n_candidates": {"min": 1, "max": 3}}
        ok = lambda c: check_discovery("12-gap-analyst", {"payload": pl}, {"result": {"candidates": [c]}})
        self.assertEqual(ok(cand()), [])
        self.assertTrue(any(e[0] == "ID_UNKNOWN" for e in ok(cand(genz_basis=[{"fact_id": "F9"}]))))                    # GA-R2
        self.assertTrue(any(e[0] == "COUNT_OUT_OF_RANGE" for e in ok(cand(existing_check={"db_cards_compared": ["a"], "verdict": "none"}))))   # GA-R3
        self.assertTrue(any(e[0] == "ENUM_UNKNOWN" for e in ok(cand(mechanism_tags=["zz"]))))                           # GA-R4

    def test_critic_requires_all_subjects_and_consistent_votes(self):
        from cardstudio.validators import check_discovery
        pl = {"lens": {"id": "evidence"}, "subject_kind": "gap_candidate", "subjects": [{"id": "A"}, {"id": "B"}]}
        chk = lambda sid, vote, grade: {"subject_id": sid, "vote": vote, "grade": grade, "findings": ["f"], "confidence_in_vote": "low"}
        run = lambda checks: check_discovery("14-critic", {"payload": pl}, {"result": {"checks": checks}})
        self.assertEqual(run([chk("A", "weaken", "약"), chk("B", "refute", "폐기")]), [])
        self.assertTrue(any("CR-R1" in e[2] for e in run([chk("A", "weaken", "약")])))                                 # 누락
        self.assertTrue(any("CR-R2" in e[2] for e in run([chk("A", "refute", "중"), chk("B", "weaken", "약")])))       # refute 인데 중
        self.assertTrue(any("CR-R2" in e[2] for e in run([chk("A", "confirm", "폐기"), chk("B", "weaken", "약")])))

    def test_scout_rules(self):
        from cardstudio.validators import check_discovery
        env = {"sources": [{"id": "S1", "url": "https://a.test/", "tier": "B"}],
               "result": {"facts": [{"id": "AAF1", "source_id": "S1"}, {"id": "AAF2", "source_id": "S9"}], "trend_items": [{"id": "T1", "fact_ids": ["AAF1", "AAF7"]}], "cases": []}}
        errs = check_discovery("11-scout", {"payload": {"known_source_urls": ["https://a.test/"]}}, env)
        codes = [(e[0], e[1]) for e in errs]
        self.assertIn(("SOURCE_URL_UNKNOWN", "facts/AAF2"), codes)              # SC-R1
        self.assertIn(("ID_UNKNOWN", "trend_items/T1"), codes)                  # SC-R5
        self.assertIn(("SOURCE_URL_UNKNOWN", "sources/S1"), codes)              # SC-R8


class DiscoveryReplayTests(unittest.TestCase):
    def test_full_pipeline_replays_recorded_run(self):
        from cardstudio.discovery import Discovery
        shutil.rmtree(f"{MVP}/runs/_unit_disc", ignore_errors=True)
        d = Discovery(Settings(provider="replay", human_mode="auto"), "_unit_disc", f"{MVP}/scenarios/genz-discovery/discovery.json")
        try:
            res = d.execute()
            self.assertEqual(len(res["finalists"]), 8)
            ranked = json.load(open(f"{d.dir}/discovery_pack/ideas_ranked.json"))
            self.assertEqual(len(ranked["ranking"]), 26)                        # 32개 - 병합 6
            cands = json.load(open(f"{d.dir}/discovery_pack/whitespace_candidates.json"))["candidates"]
            self.assertEqual(sum(1 for c in cands if c.get("dropped")), 11)
            self.assertTrue(os.path.exists(f"{d.dir}/discovery_pack/evidence_index.json"))
        finally:
            shutil.rmtree(d.dir, ignore_errors=True)


class DiscoveryEnsembleTests(unittest.TestCase):
    def test_critic_ensemble_doubles_votes_but_keeps_ranking(self):
        from cardstudio.discovery import Discovery
        from cardstudio.llm.replay_provider import ReplayProvider
        rd = f"{MVP}/scenarios/genz-discovery"

        class Two(Discovery):
            def variants(self, agent):
                if agent != "critic":
                    return super().variants(agent)
                return [{"suffix": "@a", "provider": ReplayProvider(rd), "model": "m-a", "k": 0}, {"suffix": "@b", "provider": ReplayProvider(rd), "model": "m-b", "k": 1}]
        shutil.rmtree(f"{MVP}/runs/_unit_ens", ignore_errors=True)
        d = Two(Settings(provider="replay", human_mode="auto"), "_unit_ens", f"{rd}/discovery.json")
        try:
            res = d.execute()
            self.assertEqual(len(res["finalists"]), 8)
            self.assertEqual(res["usage"]["calls"], 32 + 6)             # 기본 32회 중 critic 6회가 모델 2개씩이 되어 6회 추가
            ranked = json.load(open(f"{d.dir}/discovery_pack/ideas_ranked.json"))["ranking"]
            self.assertEqual(len(ranked), 26)                          # 같은 판정 2벌이어도 순위는 그대로
        finally:
            shutil.rmtree(d.dir, ignore_errors=True)


class TavilyTests(unittest.TestCase):
    def test_maps_results_and_never_invents_dates(self):
        from cardstudio.tools import TavilySearch
        seen = {}

        def http(payload):
            seen.update(payload)
            return {"results": [{"title": "t", "url": "https://www.example.co.kr/a", "content": "c", "score": 0.9},
                                {"title": "n", "url": "https://news.test/b", "content": "d", "published_date": "2026-09-01"}, {"title": "x"}]}
        out = TavilySearch(http=http).search("GenZ 카드", 50)
        self.assertEqual(seen["max_results"], 10)
        self.assertEqual([r["publisher"] for r in out], ["example.co.kr", "news.test"])
        self.assertIsNone(out[0]["published"])
        self.assertEqual(out[1]["published"], "2026-09-01")


class OpenAIProviderTests(unittest.TestCase):
    def test_tool_loop_then_submit(self):
        from cardstudio.llm.openai_provider import OpenAIProvider
        S = types.SimpleNamespace

        def call(i, name, args):
            return S(id=i, function=S(name=name, arguments=json.dumps(args)))

        class Chat:
            n = 0

            def create(self, **kw):
                Chat.n += 1
                calls = [call("c1", "web_search", {"query": "q"})] if Chat.n == 1 else [call("c2", "submit_output", {"ok": 2})]
                msg = S(tool_calls=calls, model_dump=lambda exclude_none=True: {"role": "assistant", "tool_calls": []})
                return S(choices=[S(message=msg)], usage=S(prompt_tokens=7, completion_tokens=3, prompt_tokens_details=None))
        client = S(chat=S(completions=Chat()))
        tool = ToolSpec("web_search", "d", {"type": "object"}, lambda a: {"results": [{"url": "https://o.test/1"}]})
        spec = CallSpec(agent="trend", model="m", system="s", user="u", output_schema={"type": "object"}, tools=[tool], max_tool_calls=3)
        res = OpenAIProvider(client=client).generate(spec)
        self.assertEqual((res.output, res.tool_calls, res.tool_urls, res.input_tokens), ({"ok": 2}, 1, ["https://o.test/1"], 14))


class RunnerTests(unittest.TestCase):
    def test_live_path_fills_code_fields_and_blocks_unknown_url(self):
        rec = json.load(open(f"{GENZ}/03-competitor/out.json", encoding="utf-8"))
        llm_part = {k: v for k, v in rec.items() if k not in contracts.CODE_OWNED}
        llm_part["sources"] = [dict(s, url="https://not-in-tool-results.test/") for s in llm_part["sources"]] or llm_part["sources"]

        class Prov:
            calls = 0

            def generate(self, spec):
                Prov.calls += 1
                return LLMResult(output=llm_part, tool_urls=["https://other.test/"], model="m-live")

        s = Settings(provider="anthropic")
        run_dir = f"{MVP}/runs/_unit_runner"
        shutil.rmtree(run_dir, ignore_errors=True)
        env_in = json.load(open(f"{GENZ}/03-competitor/in.json", encoding="utf-8"))
        runner = AgentRunner(s, Prov(), EventBus(), run_dir)
        try:
            if any(x.get("url") for x in llm_part["sources"]):
                with self.assertRaises(NeedsHuman):
                    runner.call("03-competitor", "competitor", env_in)
                self.assertEqual(Prov.calls, 1 + s.limits.agent_retry)   # 재시도 상한 지킴
        finally:
            shutil.rmtree(run_dir, ignore_errors=True)


class E2ETests(unittest.TestCase):
    def run_e2e(self, scenario, rid, over=None):
        from cardstudio.hitl import HumanGate
        s = Settings(scenario=scenario, provider="replay", human_mode="auto")
        shutil.rmtree(f"{MVP}/runs/{rid}", ignore_errors=True)
        o = Orchestrator(s, rid, "GenZ 특화 신용카드 만들어줘", human=HumanGate("auto", None, over or {}))
        o.human.bus = o.run.bus
        try:
            return o.execute(), o
        finally:
            pass

    def test_base_branch_reproduces_recorded_run(self):
        res, o = self.run_e2e("genz-credit", "_unit_base")
        try:
            self.assertEqual(res["twin_adopt"], 0.412)
            self.assertEqual(res["counters"]["concept_rework"], 1)       # 가드레일 fix 로 1회
            self.assertTrue(os.path.exists(f"{o.run.dir}/final/기획서.md"))
        finally:
            shutil.rmtree(o.run.dir, ignore_errors=True)

    def test_h2_alt_branch(self):
        res, o = self.run_e2e("genz-credit-alt", "_unit_alt", {"H2": {"id": 1, "choice": 1}})
        try:
            self.assertEqual(res["pick"]["need"], "simple")
            self.assertEqual(res["twin_adopt"], 0.382)
            self.assertEqual(res["counters"]["concept_rework"], 1)       # 상한(가드레일 1회) 후 fix 가 남은 채 진행
        finally:
            shutil.rmtree(o.run.dir, ignore_errors=True)

    def test_v2_main_path_replays(self):
        res, o = self.run_e2e("genz-credit-v2-alt", "_unit_v2a", {"H2": {"id": 1, "choice": 0}})
        try:
            self.assertEqual(res["twin_adopt"], 0.43)
            self.assertEqual(res["counters"]["concept_rework"], 1)       # 가드레일 문구 fix 로 1회
        finally:
            shutil.rmtree(o.run.dir, ignore_errors=True)

    def test_v2_graduation_branch_replays(self):
        res, o = self.run_e2e("genz-credit-v2", "_unit_v2", {"H2": {"id": 1, "choice": 2}})
        try:
            self.assertEqual(res["twin_adopt"], 0.438)
            self.assertTrue(os.path.exists(f"{o.run.dir}/final/기획서.md"))
        finally:
            shutil.rmtree(o.run.dir, ignore_errors=True)

    def test_every_call_input_passes_schema(self):
        # 입력 검증은 runner.call 안에서 매 호출 앞에 강제되므로, 완주했다면 10개 에이전트 입력이 모두 통과한 것
        res, o = self.run_e2e("genz-credit", "_unit_in")
        try:
            self.assertEqual(self.runner_calls(o), 15)
        finally:
            shutil.rmtree(o.run.dir, ignore_errors=True)

    @staticmethod
    def runner_calls(o):
        return o.runner.usage_total["calls"]


if __name__ == "__main__":
    unittest.main()
