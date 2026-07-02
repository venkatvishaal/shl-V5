"""
ConversationManager (Phase 5 update)
--------------------------------------
Minimal diff from Phase 4.  Only the JD fast-path is updated:
  - calls behavior_handler.jd_recommend() instead of behavior_handler.recommend()
  so the richer JD_RECOMMEND_PROMPT is used for job description inputs.

All other logic (context extraction, phase routing, hallucination guard)
is identical to Phase 4 — no regression possible.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Dict, List, Optional, Tuple

from src.api.schemas import ConversationPhase, Message
from src.retrieval.catalog import CatalogManager
from src.agent.behavior_handler import BehaviorHandler
from src.agent.scope_checker import ScopeChecker

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Keyword banks (unchanged from Phase 4)
# ---------------------------------------------------------------------------

def _empty_context() -> Dict:
    return {
        "turn_count": 0,
        "role": None,
        "seniority": None,
        "skills": [],
        "industry": None,
        "team_size": None,
        "duration_limit": None,
        "constraints": [],
        "required_types": [],
        "excluded_types": [],
        "previous_recommendations": [],
        "is_jd_input": False,
    }


_SENIORITY_MAP = {
    "entry":     ["entry", "graduate", "junior", "fresher", "intern", "entry-level"],
    "mid":       ["mid", "intermediate", "experienced", "associate", "mid-level"],
    "senior":    ["senior", "lead", "principal", "staff", "sr.", "sr "],
    "executive": ["executive", "director", "vp", "c-level", "c-suite",
                  "cto", "ceo", "coo", "head of"],
}
from src.agent.constants import _SKILL_KEYWORDS

_JD_SIGNALS = [
    "job description", "job posting", "job ad", "position description",
    "responsibilities:", "requirements:", "qualifications:", "about the role",
    "we are looking for", "we seek", "hiring for", "about this role",
    "key responsibilities", "must have", "nice to have", "minimum qualifications",
]

_COMPARISON_WORDS = [
    "difference", "compare", "versus", "vs", "vs.", "better", "which is",
    "what's the difference", "how do they differ",
]

_REFINEMENT_WORDS = [
    "actually", "change", "add", "remove", "instead", "also",
    "more focused", "narrow", "broaden", "shorter", "longer",
    "not that", "exclude", "without", "only", "prefer", "i'd prefer", 
    "switch to", "let's go with", "instead of", "swap",
]


class ConversationManager:
    """Full multi-turn conversation manager."""

    def __init__(self, catalog: CatalogManager):
        self.catalog          = catalog
        self.behavior_handler = BehaviorHandler(catalog)
        self.scope_checker    = ScopeChecker()

    # ── Public API ──────────────────────────────────────────────────────

    async def process(
        self, messages: List[Message]
    ) -> Tuple[str, List[Dict], bool]:
        """
        Entry point.  Returns (reply, recommendations, end_of_conversation).
        """
        logger.info(f"ConversationManager.process() — {len(messages)} messages")

        last_user_msg = self._get_last_user_message(messages)
        if not last_user_msg:
            return "I didn't catch that — could you rephrase?", [], False

        # Scope guard
        refusal = self.scope_checker.check(last_user_msg)
        if refusal:
            logger.warning(f"Out-of-scope: {refusal}")
            return self.scope_checker.get_refusal_message(refusal), [], False

        context = self._extract_context(messages)

        # ── JD fast-path ────────────────────────────────────────────────
        if len(messages) == 1 and self._is_job_description(last_user_msg):
            logger.info("JD detected — routing to jd_recommend")
            context = self._extract_context_from_jd(last_user_msg, context)
            context["is_jd_input"] = True
            # Phase 5: use jd_recommend() so the JD prompt is used
            reply, recs, done = await self.behavior_handler.jd_recommend(
                last_user_msg, context
            )
            recs = self._validate_recommendations(recs)
            return reply, recs, done

        # ── Phase routing ────────────────────────────────────────────────
        phase = self._determine_phase(messages, context)
        logger.debug(f"Phase: {phase}")

        if phase == ConversationPhase.REFUSING:
            return self.scope_checker.get_refusal_message("off_topic"), [], False

        if phase == ConversationPhase.CLARIFYING:
            reply, recs, done = await self.behavior_handler.clarify(
                last_user_msg, context
            )

        elif phase == ConversationPhase.RECOMMENDING:
            reply, recs, done = await self.behavior_handler.recommend(
                last_user_msg, context
            )
            recs = self._validate_recommendations(recs)

        elif phase == ConversationPhase.REFINING:
            reply, recs, done = await self.behavior_handler.refine(
                last_user_msg, context
            )
            recs = self._validate_recommendations(recs)

        elif phase == ConversationPhase.COMPARING:
            reply, recs, done = await self.behavior_handler.compare(
                last_user_msg, context
            )

        else:
            reply = (
                "I'm here to help you find the right SHL assessments. "
                "Could you tell me more about the role you're hiring for?"
            )
            recs, done = [], False

        return reply, recs, done

    # ── Phase determination ─────────────────────────────────────────────

    def _determine_phase(
        self, messages: List[Message], context: Dict
    ) -> ConversationPhase:
        last_msg    = self._get_last_user_message(messages).lower()
        turn_count  = len(messages)

        # 1. Comparison phase (only trigger if it's comparison of assessments)
        if any(w in last_msg for w in _COMPARISON_WORDS):
            test_indicators = {"verbal", "numerical", "logical", "opq", "personality", "test",
                               "reasoning", "ability", "questionnaire", "assessment", "sjt",
                               "simulation", "versus", "vs"}
            has_test_word = any(ind in last_msg for ind in test_indicators)
            has_catalog_name = any(a["name"].lower() in last_msg for a in self.catalog.list_all())
            if has_test_word or has_catalog_name:
                # Avoid out-of-scope comparison false positives (like compare salaries)
                if not any(w in last_msg for w in ["salary", "salaries", "pay", "compensation", "job", "career"]):
                    return ConversationPhase.COMPARING

        # 2. Refinement phase
        if len(messages) > 1:
            refinement_match = False
            for w in _REFINEMENT_WORDS:
                if w in last_msg:
                    # Ignore common conversation phrases with 'change' (e.g. change career, change of career)
                    if w == "change":
                        false_positives = ["change career", "change job", "change my career", "change my job",
                                           "change fields", "change in career", "change of career", "change my mind"]
                        if not any(fp in last_msg for fp in false_positives):
                            refinement_match = True
                    else:
                        refinement_match = True
            if refinement_match:
                return ConversationPhase.REFINING

        role_known      = bool(context.get("role") or context.get("skills"))
        seniority_known = bool(context.get("seniority"))
        turns_sufficient = turn_count >= 4

        if role_known and (seniority_known or turns_sufficient):
            return ConversationPhase.RECOMMENDING

        if turn_count >= 7:
            return ConversationPhase.RECOMMENDING

        return ConversationPhase.CLARIFYING

    # ── Context extraction ──────────────────────────────────────────────

    @staticmethod
    def _word_match(keyword: str, text: str) -> bool:
        """Helper to match seniority keywords with word boundaries to avoid lead -> leadership issues."""
        if keyword.endswith('.'):
            pattern = r'\b' + re.escape(keyword)
        else:
            pattern = r'\b' + re.escape(keyword) + r'\b'
        return bool(re.search(pattern, text))

    def _extract_context(self, messages: List[Message]) -> Dict:
        ctx = _empty_context()
        ctx["turn_count"] = len(messages)

        full_user_text = " ".join(
            m.content for m in messages if m.role == "user"
        ).lower()

        # Word boundary match for seniority
        for level, keywords in _SENIORITY_MAP.items():
            if any(self._word_match(kw, full_user_text) for kw in keywords):
                ctx["seniority"] = level
                break

        matched_skills = [kw for kw in _SKILL_KEYWORDS if kw in full_user_text]
        ctx["skills"] = list(dict.fromkeys(matched_skills))

        # Extended role matching regex
        role_match = re.search(
            r"(?:hire|hiring|assess|for a|for an|role of|position of|looking for a|looking for an|we need a|we need an|recruiting for a|recruiting for an)\s+"
            r"([a-z0-9][a-z0-9\s&/\-]+?)(?:\s+who|\s+with|\s+to|\.|,|\n|$)",
            full_user_text,
        )
        if role_match:
            ctx["role"] = role_match.group(1).strip()

        # Try to extract or override seniority from the role string itself
        role_lower = (ctx.get("role") or "").lower()
        if role_lower:
            for level, keywords in _SENIORITY_MAP.items():
                if any(self._word_match(kw, role_lower) for kw in keywords):
                    ctx["seniority"] = level
                    break

        dur_match = re.search(r"(\d+)\s*(?:min(?:utes?)?|hrs?|hours?)", full_user_text)
        if dur_match:
            raw = int(dur_match.group(1))
            if "hr" in dur_match.group(0) or "hour" in dur_match.group(0):
                raw *= 60
            ctx["duration_limit"] = raw

        industries = [
            "banking", "finance", "healthcare", "retail", "technology",
            "engineering", "sales", "marketing", "logistics", "education",
            "manufacturing", "consulting", "telecom",
        ]
        for ind in industries:
            if ind in full_user_text:
                ctx["industry"] = ind
                break

        for msg in messages:
            if msg.role == "user":
                if any(w in msg.content.lower() for w in _REFINEMENT_WORDS):
                    ctx["constraints"].append(msg.content)

        latest = self._get_last_user_message(messages).lower()
        type_words = {
            "personality": "P", "knowledge": "K", "cognitive": "A",
            "ability": "A", "situational": "SI",
        }
        for word, code in type_words.items():
            if word in latest:
                near_exclusion = re.search(
                    rf"(?:remove|exclude|without|no)\b[^.;,]{{0,30}}\b{word}\b",
                    latest,
                )
                target = "excluded_types" if near_exclusion else "required_types"
                ctx[target].append(code)

        ctx["previous_recommendations"] = self._harvest_prior_recs(messages)
        return ctx

    def _extract_context_from_jd(self, jd_text: str, ctx: Dict) -> Dict:
        lower = jd_text.lower()

        title_match = re.search(
            r"(?:job title|position|role)[:\s\-]+([A-Za-z0-9][A-Za-z0-9\s&/\-]+?)(?:\n|,|;|$|\.|\()",
            jd_text,
            re.IGNORECASE,
        )
        if not title_match:
            title_match = re.search(
                r"(?:looking for a|seeking a|hiring a) ([A-Za-z0-9][A-Za-z0-9\s&/\-]+?)(?:\n|,|;|$|\.|\()",
                jd_text,
                re.IGNORECASE,
            )
            
        if title_match and not ctx.get("role"):
            ctx["role"] = title_match.group(1).strip()

        # Extract/override seniority from JD (preferring role title first)
        role_lower = (ctx.get("role") or "").lower()
        title_seniority_found = False
        if role_lower:
            for level, keywords in _SENIORITY_MAP.items():
                if any(self._word_match(kw, role_lower) for kw in keywords):
                    ctx["seniority"] = level
                    title_seniority_found = True
                    break

        if not title_seniority_found:
            for level, keywords in _SENIORITY_MAP.items():
                if any(self._word_match(kw, lower) for kw in keywords):
                    ctx["seniority"] = level
                    break

        matched = [kw for kw in _SKILL_KEYWORDS if kw in lower]
        ctx["skills"] = list(dict.fromkeys(ctx["skills"] + matched))
        return ctx

    def _harvest_prior_recs(self, messages: List[Message]) -> List[Dict]:
        recs: List[Dict] = []
        for msg in messages:
            if msg.role == "assistant":
                json_blobs = re.findall(r"\[\s*\{.*?\}\s*\]", msg.content, re.DOTALL)
                for blob in json_blobs:
                    try:
                        parsed = json.loads(blob)
                        if isinstance(parsed, list) and parsed and "url" in parsed[0]:
                            recs.extend(parsed)
                    except json.JSONDecodeError:
                        pass
        return recs

    # ── Helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _get_last_user_message(messages: List[Message]) -> str:
        for msg in reversed(messages):
            if msg.role == "user":
                return msg.content
        return ""

    @staticmethod
    def _is_job_description(text: str) -> bool:
        lower = text.lower()
        
        strong_signals = {
            "job description", "job posting", "position description", 
            "responsibilities:", "requirements:", "qualifications:", 
            "key responsibilities"
        }
        weak_signals = {
            "job ad", "about the role", "we are looking for", "we seek", 
            "hiring for", "about this role", "must have", "nice to have", 
            "minimum qualifications"
        }

        # Any strong signal triggers JD detection immediately (e.g. paste of a responsibilities section)
        if any(sig in lower for sig in strong_signals):
            return True
            
        # Weak signals require a reasonable word length to avoid false positives
        has_weak = any(sig in lower for sig in weak_signals)
        word_count = len(text.split())
        if has_weak and word_count >= 40:
            return True
            
        if word_count >= 150:
            return True
            
        return False

    def _validate_recommendations(self, recs: List[Dict]) -> List[Dict]:
        validated = []
        for rec in recs:
            url = rec.get("url", "")
            catalog_item = self.catalog.get_by_url(url)
            if catalog_item:
                validated.append({
                    "name": catalog_item["name"],
                    "url": catalog_item["url"],
                    "test_type": catalog_item["test_type"],
                })
            else:
                logger.warning(
                    f"Dropping hallucinated recommendation: "
                    f"{rec.get('name')} / {url}"
                )
        return validated
