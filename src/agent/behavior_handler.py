"""
BehaviorHandler (Phase 5 update)
---------------------------------
Replaces the Phase 4 version.  The core algorithm is identical; the only
change is that all prompt strings are now imported from src/llm/prompts.py
(Phase 5 deliverable) instead of being defined inline.

This keeps behavior_handler.py focused on *logic* (search, ranking, parsing)
while prompts.py owns all LLM language.

What changed vs Phase 4
~~~~~~~~~~~~~~~~~~~~~~~~
* Imports CLARIFY_SYSTEM, CLARIFY_PROMPT, RECOMMEND_SYSTEM, RECOMMEND_PROMPT,
  REFINE_SYSTEM, REFINE_PROMPT, COMPARE_SYSTEM, COMPARE_PROMPT,
  JD_RECOMMEND_SYSTEM, JD_RECOMMEND_PROMPT from src.llm.prompts.
* Uses prompts.format_catalog_section(), format_requirements_summary(),
  format_context_summary(), format_assessments_verbose() for formatting —
  removes duplicated formatting helpers from this file.
* LLMClient is imported from src.llm.client (lazy, same as before).
* Added jd_recommend() method so ConversationManager can call it for the
  JD fast-path with the richer JD-specific prompt.
* _build_fallback_recommendations() unchanged.
* _score_candidate() and _search_and_rank() unchanged.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Dict, List, Optional, Tuple

from src.retrieval.catalog import CatalogManager
from src.config import settings
from src.agent.constants import _SKILL_KEYWORDS
from src.llm.prompts import (
    CLARIFY_SYSTEM,
    CLARIFY_PROMPT,
    RECOMMEND_SYSTEM,
    RECOMMEND_PROMPT,
    REFINE_SYSTEM,
    REFINE_PROMPT,
    COMPARE_SYSTEM,
    COMPARE_PROMPT,
    JD_RECOMMEND_SYSTEM,
    JD_RECOMMEND_PROMPT,
    format_catalog_section,
    format_requirements_summary,
    format_context_summary,
    format_assessments_verbose,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Deterministic relevance scorer
# ---------------------------------------------------------------------------

# General-purpose assessment types that apply broadly across roles.
# These get a base relevance score even without specific skill matches.
_GENERAL_ASSESSMENT_KEYWORDS = {
    "personality": 2.0,
    "opq": 2.0,
    "verbal": 1.8,
    "numerical": 1.8,
    "reasoning": 1.5,
    "situational judgment": 1.8,
    "communication": 1.2,
    "cognitive": 1.5,
    "simulation": 1.5,
}
# Test types that are generally applicable across roles.
# Note: Verbal and Numerical assessments have test_type="A" (Ability & Aptitude)
# in the SHL catalog schema, not "V" or "N".
_GENERAL_TEST_TYPES = {"P", "A", "SI"}

_CATEGORY_SIGNALS = {
    "personality": (
        {"personality", "opq"},                          # detection keywords
        {"personality", "leadership", "leader", "manager", "executive",
         "cto", "c-suite", "sales", "graduate", "stakeholder",
         "director", "head"},                            # intent triggers
        5.0, 1.0,
    ),
    "verbal": (
        {"verbal"},
        {"verbal", "communication", "stakeholder", "client",
         "customer", "negotiation", "persuasion", "graduate",
         "leadership", "manager", "executive", "cto", "board",
         "c-suite", "cognitive", "cognitive ability"},
        5.0, 1.0,
    ),
    "numerical": (
        {"numerical"},
        {"numerical", "analytical", "analytics", "cognitive",
         "cognitive ability",
         "finance", "banking", "data", "graduate", "logical",
         "decision-making", "decision making", "sales"},
        5.0, 1.0,
    ),
    "simulation": (
        {"simulation"},
        {"customer", "service", "contact center", "client",
         "situational", "simulation"},
        5.0, 0.0,
    ),
    "reasoning": (
        {"reasoning", "cognitive"},
        {"reasoning", "logical", "cognitive", "analytical",
         "problem solving", "critical thinking"},
        4.0, 0.5,
    ),
}

_TEST_INDICATORS = {"questionnaire", "verify", "test", "assessment",
                    "simulation", "interactive"}

_REPORT_INDICATORS = {"report", "guide", "profile", "summary",
                      "feedback"}

_PROGRAMMING_LANGS = {
    "java", "python", "c#", "c++", "javascript", "typescript",
    ".net", "ruby", "php", "scala", "kotlin", "swift", "go",
    "sql", "html", "css", "angular", "react", "node",
}


def _type_codes(assessment: Dict) -> set[str]:
    return {
        code.strip().upper()
        for code in str(assessment.get("test_type", "")).split(",")
        if code.strip()
    }


def _has_type(assessment: Dict, code: str) -> bool:
    return code.strip().upper() in _type_codes(assessment)


def _score_candidate(assessment: Dict, requirements: Dict) -> float:
    """
    Score an assessment against structured requirements.
    No LLM involved — fast and deterministic.
    Higher score = more relevant.
    """
    score = 0.0
    skills        = [s.lower() for s in requirements.get("skills", [])]
    seniority     = (requirements.get("seniority") or "").lower()
    duration_limit = requirements.get("duration_limit")
    role          = (requirements.get("role") or "").lower()

    # Build searchable text blob for this assessment
    text = " ".join([
        assessment.get("name", ""),
        assessment.get("description", ""),
        " ".join(assessment.get("dimensions", [])),
        " ".join(assessment.get("use_cases", [])),
    ]).lower()

    name_lower = assessment.get("name", "").lower()
    intent_text = " ".join([role, seniority, " ".join(skills)]).lower()

    # ── Skill / keyword match (with partial matching) ────────────────
    for skill in skills:
        if skill in text:
            score += 4.0
        elif len(skill.split()) > 1:
            # For multi-word skills, require at least 2 of 3 words to match
            words = [w for w in skill.split() if len(w) > 3]
            if len(words) >= 2 and sum(1 for w in words if w in text) >= 2:
                score += 0.8

    # ── General applicability bonus ──────────────────────────────────
    # Assessments like personality, verbal, numerical reasoning are broadly
    # useful across almost any role.  Give them a meaningful base score.
    test_types = _type_codes(assessment)
    test_type = assessment.get("test_type", "")
    if test_types & _GENERAL_TEST_TYPES:
        score += 1.5

    for keyword, bonus in _GENERAL_ASSESSMENT_KEYWORDS.items():
        if keyword in name_lower or keyword in text:
            score += bonus
            break  # only apply the highest matching general bonus

    # ── Category-based contextual relevance ────────────────────────────
    # Instead of hardcoding specific assessment names, detect the
    # assessment's *category* from its name/description and boost when
    # the user's intent aligns with that category.  This generalises
    # across all catalog items of the same type.
    #
    # Name-match premium: if the category keyword appears in the
    # assessment *name*, it's a primary/canonical assessment for that
    # category and gets a larger boost than description-only matches.

    for _cat_name, (detect_kws, triggers, high_boost, base_boost) in _CATEGORY_SIGNALS.items():
        # Check if this assessment belongs to this category
        in_name = any(kw in name_lower for kw in detect_kws)
        in_text = any(kw in text for kw in detect_kws)
        if in_name or in_text:
            # Name-match premium: canonical assessments score higher
            multiplier = 1.5 if in_name else 1.0
            if any(kw in intent_text for kw in triggers):
                score += high_boost * multiplier
            elif base_boost:
                score += base_boost * multiplier

    # ── Required-types boost ─────────────────────────────────────────
    # If the user explicitly requests/requires a specific test type
    required_types = requirements.get("required_types", [])
    for rtype in required_types:
        if _has_type(assessment, rtype):
            score += 5.0

    # ── Assessment-type signal ───────────────────────────────────────
    # Favor items that ARE actual tests/questionnaires over derivative
    # reports, guides, and profiles.  The former are what the user is
    # hiring for; the latter are output artefacts.
    if any(kw in name_lower for kw in _TEST_INDICATORS):
        score += 3.0
    if any(kw in name_lower for kw in _REPORT_INDICATORS):
        score -= 3.0

    # ── Programming-language assessment matching ─────────────────────
    # Generalised: if the assessment name contains a known programming
    # language AND that language appears in the user's intent, boost it.
    for lang in _PROGRAMMING_LANGS:
        # Match whole words to avoid java matching javascript
        if re.search(r'\b' + re.escape(lang) + r'\b', name_lower) and re.search(r'\b' + re.escape(lang) + r'\b', intent_text):
            score += 5.0
            break

    # ── Duration-aware boost ─────────────────────────────────────────
    # When user specifies a duration cap, assessments that fit within it
    # and belong to broadly useful categories get a relevance nudge.
    if duration_limit:
        dur = assessment.get("duration_minutes")
        if dur and dur <= duration_limit:
            if test_types & _GENERAL_TEST_TYPES:
                score += 3.0

    # ── Role-based contextual boosts ─────────────────────────────────
    if role:
        # Personality & Cognitive assessments are especially valuable for leadership roles
        if any(kw in role for kw in ("manager", "leader", "executive", "director", "cto", "head")):
            if _has_type(assessment, "P"):
                score += 2.0
            if _has_type(assessment, "A"):
                score += 2.0
            if "personality" in text or "opq" in name_lower:
                score += 1.0

        # Technical roles benefit from technical knowledge + numerical tests
        if any(kw in role for kw in ("developer", "engineer", "architect", "programmer", "scientist")):
            if _has_type(assessment, "K"):
                score += 1.5
            if _has_type(assessment, "A") and "numerical" in name_lower:
                score += 1.5

        # Customer service roles benefit from situational judgment + verbal
        if "customer" in role or "service" in role:
            if _has_type(assessment, "SI") or _has_type(assessment, "B") or _has_type(assessment, "A"):
                score += 1.5
            if "simulation" in text:
                score += 1.5

        # Sales roles benefit from personality (persuasion) and verbal
        if "sales" in role:
            if _has_type(assessment, "P") or _has_type(assessment, "A"):
                score += 1.0

    # ── Cognitive ability base boost for professional roles ─────────
    if seniority in ("mid", "senior", "executive"):
        if _has_type(assessment, "A"):
            score += 1.5

    # ── Seniority match ──────────────────────────────────────────────
    if seniority:
        target_levels = [lv.lower() for lv in assessment.get("target_levels", [])]
        level_synonyms = {
            "entry": {"entry", "graduate", "junior", "intern", "entry-level"},
            "mid": {"mid", "intermediate", "experienced", "associate", "mid-professional", "professional individual contributor"},
            "senior": {"senior", "lead", "principal", "staff", "supervisor"},
            "executive": {"executive", "director", "vp", "c-level", "c-suite", "cto", "ceo", "coo", "head of", "manager"},
        }
        syns = level_synonyms.get(seniority, {seniority})
        if any(any(s in tl for s in syns) for tl in target_levels):
            score += 2.0

    # ── Duration cap penalty ─────────────────────────────────────────
    dur = assessment.get("duration_minutes")
    if duration_limit and dur and dur > duration_limit:
        score -= 3.0

    # ── Role text match ──────────────────────────────────────────────
    if role and role in text:
        score += 1.0

    # ── Metadata completeness bonus ──────────────────────────────────
    if assessment.get("dimensions"):
        score += 0.3
    if assessment.get("use_cases"):
        score += 0.2

    return score


# ---------------------------------------------------------------------------
# BehaviorHandler
# ---------------------------------------------------------------------------

class BehaviorHandler:
    """
    Implements four conversation behaviors:
        clarify   — ask 1-2 targeted questions
        recommend — rank + explain 1-10 catalog assessments
        refine    — update recommendations given a new constraint
        compare   — answer differences between named assessments
        jd_recommend — fast-path for job-description input

    Every behavior returns (reply: str, recommendations: List[Dict], end: bool).
    """

    def __init__(self, catalog: CatalogManager):
        self.catalog = catalog
        self._llm: Optional[object] = None  # lazy-loaded LLMClient

    # ── Behaviors ───────────────────────────────────────────────────────

    async def clarify(
        self, user_message: str, context: Dict
    ) -> Tuple[str, List[Dict], bool]:
        """Ask targeted clarifying questions."""
        logger.debug("BehaviorHandler.clarify()")

        prompt = CLARIFY_PROMPT.format(
            context_summary=format_context_summary(context),
            user_message=user_message,
        )

        try:
            reply = await self._call_llm(prompt, CLARIFY_SYSTEM)
        except Exception as exc:
            logger.warning(f"clarify(): LLM failed ({exc!r}), using fallback")
            reply = self._fallback_clarify(context)

        return reply.strip(), [], False

    async def recommend(
        self, user_message: str, context: Dict
    ) -> Tuple[str, List[Dict], bool]:
        """Search, rank, and explain 1-10 recommendations."""
        logger.debug("BehaviorHandler.recommend()")

        requirements = self._build_requirements(context)
        candidates   = self._search_and_rank(requirements, max_results=15)

        if not candidates:
            return (
                "I couldn't find assessments matching those requirements in the catalog. "
                "Could you share more about the role or skills you want to assess?",
                [],
                False,
            )

        max_recs = min(len(candidates), 10)
        prompt = RECOMMEND_PROMPT.format(
            catalog_section=format_catalog_section(candidates),
            requirements_summary=format_requirements_summary(requirements, user_message),
            max_recs=max_recs,
        )

        try:
            raw = await self._call_llm(prompt, RECOMMEND_SYSTEM)
        except Exception as exc:
            logger.warning(f"recommend(): LLM failed ({exc!r}), using fallback")
            reply, recs = self._build_fallback_recommendations(candidates)
            return reply, recs, True

        reply, recs = self._parse_recommend_response(raw, candidates)
        return reply, recs, True

    async def refine(
        self, user_message: str, context: Dict
    ) -> Tuple[str, List[Dict], bool]:
        """Update recommendations based on a new constraint."""
        logger.debug("BehaviorHandler.refine()")

        ctx = context.copy()
        ctx.setdefault("constraints", []).append(user_message)

        requirements = self._build_requirements(ctx)
        candidates   = self._search_and_rank(requirements, max_results=15)

        if not candidates:
            return (
                "After applying your constraint I couldn't find matching assessments. "
                "Could you tell me more about what you're looking for?",
                [],
                False,
            )

        max_recs = min(len(candidates), 10)
        prompt = REFINE_PROMPT.format(
            catalog_section=format_catalog_section(candidates),
            requirements_summary=format_requirements_summary(requirements),
            new_constraint=user_message,
            max_recs=max_recs,
        )

        try:
            raw = await self._call_llm(prompt, REFINE_SYSTEM)
        except Exception as exc:
            logger.warning(f"refine(): LLM failed ({exc!r}), using fallback")
            reply, recs = self._build_fallback_recommendations(candidates)
            return reply, recs, True

        reply, recs = self._parse_recommend_response(raw, candidates)
        return reply, recs, True

    async def compare(
        self, user_message: str, context: Dict
    ) -> Tuple[str, List[Dict], bool]:
        """Compare two or more named assessments."""
        logger.debug("BehaviorHandler.compare()")

        targets = self._extract_comparison_targets(user_message)
        assessment_data = [
            a for name in targets
            if (a := self.catalog.get_assessment(name)) is not None
        ]

        # Broader fallback if named targets not found
        if len(assessment_data) < 2:
            assessment_data = self.catalog.search_by_keyword(user_message)[:3]

        if len(assessment_data) < 2:
            return (
                "I couldn't identify two or more assessments to compare. "
                "Please name them directly — for example, "
                "\"Compare OPQ32r and the Numerical Reasoning test\".",
                [],
                False,
            )

        prompt = COMPARE_PROMPT.format(
            assessment_details=format_assessments_verbose(assessment_data),
            user_message=user_message,
        )

        try:
            reply = await self._call_llm(prompt, COMPARE_SYSTEM)
        except Exception as exc:
            logger.warning(f"compare(): LLM failed ({exc!r}), using fallback")
            reply = (
                "I'm unable to generate a comparison right now, but here are the "
                "key facts about each assessment:\n\n"
                + format_assessments_verbose(assessment_data)
            )

        return reply.strip(), [], False

    async def jd_recommend(
        self, jd_text: str, context: Dict
    ) -> Tuple[str, List[Dict], bool]:
        """
        Fast-path for a pasted job description.
        Uses the richer JD_RECOMMEND_PROMPT that references the JD text directly.
        """
        logger.debug("BehaviorHandler.jd_recommend()")

        requirements = self._build_requirements(context)
        candidates   = self._search_and_rank(requirements, max_results=15)

        # If context yields nothing, fall back to full catalog (JD parsing covers it)
        if not candidates:
            candidates = self.catalog.list_all()[:15]

        max_recs = min(len(candidates), 7)  # JD fast-path: cap at 7

        prompt = JD_RECOMMEND_PROMPT.format(
            catalog_section=format_catalog_section(candidates),
            jd_text=jd_text[:2000],  # safety cap
            requirements_summary=format_requirements_summary(requirements),
        )

        try:
            raw = await self._call_llm(prompt, JD_RECOMMEND_SYSTEM)
        except Exception as exc:
            logger.warning(f"jd_recommend(): LLM failed ({exc!r}), using fallback")
            reply, recs = self._build_fallback_recommendations(candidates)
            return reply, recs, True

        reply, recs = self._parse_recommend_response(raw, candidates)
        return reply, recs, True

    # ── LLM integration ─────────────────────────────────────────────────

    async def _call_llm(self, user_prompt: str, system_prompt: str) -> str:
        """Call an optional LLM under a strict deadline."""
        if self._llm is None and not settings.use_llm:
            raise RuntimeError("LLM wording disabled; using grounded fallback")
        llm = self._get_llm()
        return await asyncio.wait_for(
            llm.generate(user_prompt, system_prompt=system_prompt),
            timeout=settings.llm_timeout_seconds,
        )

    def _get_llm(self):
        if self._llm is None:
            from src.llm.client import LLMClient
            self._llm = LLMClient()
        return self._llm

    # ── Catalog search & ranking ────────────────────────────────────────

    # Test types that are universally applicable across nearly every role.
    # We guarantee at least one assessment per type in the candidate pool.
    # Note: Verbal and Numerical assessments both map to test_type="A" (Ability
    # & Aptitude), so we inject up to 2 "A" assessments to cover both.
    _UNIVERSAL_TYPES = {"P", "A", "SI"}

    def _search_and_rank(
        self, requirements: Dict, max_results: int = 10
    ) -> List[Dict]:
        """
        Score every catalog entry against requirements; return top max_results.
        Assessments with score ≤ 0 are omitted unless everything scores ≤ 0.
        Universal type assessments are always guaranteed a spot.
        """
        all_assessments = self.catalog.list_all()
        skills = requirements.get("skills", [])
        excluded_types = set(requirements.get("excluded_types", []))
        duration_limit = requirements.get("duration_limit")
        all_assessments = [
            item for item in all_assessments
            if not (_type_codes(item) & set(excluded_types))
            and not (
                duration_limit
                and item.get("duration_minutes") is not None
                and item["duration_minutes"] > duration_limit
            )
        ]

        # Keyword pre-filter when skills are known
        if skills:
            allowed_urls = {item.get("url", "") for item in all_assessments}
            seen: set = set()
            keyword_hits: List[Dict] = []
            for skill in skills:
                for a in self.catalog.search_by_keyword(skill):
                    url = a.get("url", "")
                    if url in allowed_urls and url not in seen:
                        seen.add(url)
                        keyword_hits.append(a)
            # Append the rest so nothing is missed in scoring
            for a in all_assessments:
                url = a.get("url", "")
                if url not in seen:
                    seen.add(url)
                    keyword_hits.append(a)
            candidates = keyword_hits
        else:
            candidates = all_assessments

        scored = sorted(
            ((a, _score_candidate(a, requirements)) for a in candidates),
            key=lambda x: x[1],
            reverse=True,
        )

        positive = [(a, s) for a, s in scored if s > 0]
        if positive:
            results = [a for a, _ in positive[:max_results]]
        else:
            results = [a for a, _ in scored[:max_results]]

        # Required assessment types are hard intent, not a soft diversity hint.
        for required_type in requirements.get("required_types", []):
            if any(_has_type(item, required_type) for item in results):
                continue
            for item, _ in scored:
                if _has_type(item, required_type):
                    results.insert(0, item)
                    break

        # Always inject universal assessments.  For "A" type (Ability &
        # Aptitude), inject up to 2 to cover both Verbal and Numerical.
        result_urls = {a.get("url", "") for a in results}
        result_type_counts: Dict[str, int] = {}
        for a in results:
            t = a.get("test_type", "")
            result_type_counts[t] = result_type_counts.get(t, 0) + 1

        for utype in self._UNIVERSAL_TYPES:
            max_count = 2 if utype == "A" else 1
            current_count = result_type_counts.get(utype, 0)
            if current_count >= max_count or len(results) >= max_results + 4:
                continue
            # Find the highest-scored assessment of this type not already in results
            for a, _ in scored:
                if _has_type(a, utype) and a.get("url", "") not in result_urls:
                    results.append(a)
                    result_urls.add(a.get("url", ""))
                    result_type_counts[utype] = result_type_counts.get(utype, 0) + 1
                    if result_type_counts[utype] >= max_count:
                        break

        return results

    # ── Requirements extraction ─────────────────────────────────────────

    def _build_requirements(self, context: Dict) -> Dict:
        """Flatten context into a requirements dict for scoring and prompts."""
        reqs: Dict = {
            "role":           context.get("role"),
            "seniority":      context.get("seniority"),
            "skills":         list(context.get("skills") or []),
            "industry":       context.get("industry"),
            "duration_limit": context.get("duration_limit"),
            "required_types": list(context.get("required_types") or []),
            "excluded_types": list(context.get("excluded_types") or []),
        }
        for constraint in context.get("constraints", []):
            self._parse_constraint_into(constraint, reqs)
        return reqs

    @staticmethod
    def _parse_constraint_into(constraint_text: str, reqs: Dict) -> None:
        """Extract duration caps and additional skills from free-text constraint."""
        lower = constraint_text.lower()

        dur_match = re.search(r"(\d+)\s*(?:min(?:utes?)?|hrs?|hours?)", lower)
        if dur_match:
            raw = int(dur_match.group(1))
            if "hr" in dur_match.group(0) or "hour" in dur_match.group(0):
                raw *= 60
            reqs["duration_limit"] = raw

        type_words = {
            "personality": "P",
            "knowledge": "K",
            "cognitive": "A",
            "ability": "A",
            "situational": "SI",
        }
        for word, code in type_words.items():
            if word in lower:
                near_exclusion = re.search(
                    rf"(?:remove|exclude|without|no)\b[^.;,]{{0,30}}\b{word}\b",
                    lower,
                )
                key = "excluded_types" if near_exclusion else "required_types"
                if code not in reqs.setdefault(key, []):
                    reqs[key].append(code)

        for kw in _SKILL_KEYWORDS:
            if kw in lower and kw not in reqs["skills"]:
                reqs["skills"].append(kw)

    # ── Response parsing ────────────────────────────────────────────────

    def _parse_recommend_response(
        self, raw: str, candidates: List[Dict]
    ) -> Tuple[str, List[Dict]]:
        """
        Split LLM output into (human_reply, validated_recommendation_list).

        Expected format:
            <natural language reply>
            RECOMMENDATIONS_JSON:
            [{"name": "...", "url": "...", "test_type": "..."}]

        Falls back to top candidates directly from catalog if JSON is absent
        or malformed — never invents recommendations.
        """
        recs: List[Dict] = []
        reply_text = raw.strip()

        marker = "RECOMMENDATIONS_JSON:"
        if marker in raw:
            parts = raw.split(marker, 1)
            reply_text = parts[0].strip()
            json_raw   = parts[1].strip()

            # Strip optional markdown fences
            json_raw = re.sub(r"^```(?:json)?", "", json_raw).strip()
            json_raw = re.sub(r"```$",          "", json_raw).strip()

            try:
                parsed = json.loads(json_raw)
                if isinstance(parsed, list):
                    for item in parsed:
                        catalog_item = (
                            self.catalog.get_by_url(item.get("url", ""))
                            if isinstance(item, dict) else None
                        )
                        if catalog_item:
                            recs.append({
                                "name": catalog_item["name"],
                                "url": catalog_item["url"],
                                "test_type": catalog_item["test_type"],
                            })
            except json.JSONDecodeError as exc:
                logger.warning(f"RECOMMENDATIONS_JSON parse failed: {exc}")

        # Catalog fallback — guarantees no hallucination.
        # Use the diverse fallback method instead of raw top-5 to ensure
        # broad test-type coverage even when the LLM JSON is malformed.
        if not recs and candidates:
            logger.info("No valid JSON recs from LLM — using diverse catalog candidates")
            fallback_reply, recs = self._build_fallback_recommendations(candidates)
            if not reply_text.strip():
                reply_text = fallback_reply

        if not reply_text.strip():
            reply_text = (
                "Here are the SHL assessments that best match the information "
                "provided, grounded in the catalog."
            )

        return reply_text, recs[:10]

    # ── Fallbacks ───────────────────────────────────────────────────────

    @staticmethod
    def _fallback_clarify(context: Dict) -> str:
        missing = []
        if not context.get("role"):
            missing.append("the role you're hiring for")
        if not context.get("seniority"):
            missing.append("the seniority level (entry / mid / senior / executive)")
        if not missing:
            missing.append("any specific skills or competencies you'd like assessed")
        questions = " and ".join(missing[:2])
        return f"To recommend the best SHL assessments, could you tell me {questions}?"

    def _build_fallback_recommendations(
        self, candidates: List[Dict]
    ) -> Tuple[str, List[Dict]]:
        """Use the deterministic relevance order with diversity guarantees."""
        # Separate by type for diversity injection
        type_order = {"K": 0, "A": 1, "P": 2, "SI": 3, "S": 4, "E": 5, "C": 6, "D": 7}
        
        seen = set()
        recs = []
        diversity = []  # P, SI, S types for guaranteed inclusion
        
        for item in candidates:
            url = item.get("url", "")
            if url in seen:
                continue
            seen.add(url)
            
            t = (item.get("test_type") or "U")[0]  # first type code
            
            # Keep only the required schema fields
            clean_item = {
                "name": item.get("name", ""),
                "url": url,
                "test_type": item.get("test_type", "U"),
            }
            
            if t in ("P", "SI", "S"):
                diversity.append(clean_item)
            elif len(recs) < 10:
                recs.append(clean_item)
        
        # Fill remaining slots with diversity types first
        for item in diversity:
            if len(recs) >= 10:
                break
            recs.append(item)
        
        recs = recs[:10]
        
        lines = [
            "Based on your requirements, here are the most relevant SHL assessments:"
        ]
        for i, r in enumerate(recs, 1):
            lines.append(f"{i}. {r['name']} [{r.get('test_type', 'U')}]")
        return "\n".join(lines), recs

    # ── Comparison target extraction ────────────────────────────────────

    def _extract_comparison_targets(self, user_message: str) -> List[str]:
        """Return all assessment names mentioned in the user message."""
        msg_lower = user_message.lower()
        exact = [
            a["name"]
            for a in self.catalog.list_all()
            if a["name"].lower() in msg_lower
        ]
        aliases = {
            "opq32r": "Occupational Personality Questionnaire OPQ32r",
            "opq": "Occupational Personality Questionnaire OPQ32r",
            "verbal reasoning": "Verify - Verbal Ability - Next Generation",
            "verbal ability": "Verify - Verbal Ability - Next Generation",
            "numerical reasoning": "SHL Verify Interactive - Numerical Reasoning",
        }
        for alias, name in aliases.items():
            if alias in msg_lower and name not in exact and self.catalog.verify_name(name):
                exact.append(name)
        return exact
