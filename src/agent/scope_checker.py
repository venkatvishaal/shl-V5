"""
ScopeChecker
------------
Determines whether a user message is within the agent's allowed scope
(SHL assessment recommendations) and returns an appropriate refusal
message when it is not.

Returns None from check() if the message is in scope.
Returns a category string (e.g. "prompt_injection") if out of scope.
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


class ScopeChecker:
    """Boundary enforcement for the SHL recommender agent."""

    # ── Patterns that are ALWAYS allowed ───────────────────────────────
    _ALWAYS_IN_SCOPE = [
        r"^(hi|hello|hey|thanks|thank you|ok|okay|got it|sounds good|perfect|great|sure|yes|no|please)[\s!\.]*$",
        r"^(yes|no|maybe|okay|ok)[,\.]?\s*(i\s+)?",   # short affirmations
    ]

    # ── Out-of-scope pattern categories ────────────────────────────────
    _OUT_OF_SCOPE: dict = {
        "prompt_injection": [r"ignore\b.*\b(previous|prior|all|your)\b.*\binstructions?",
    r"ignore\b.*\brules?",
    r"ignore\b.*\bsystem prompt",
    r"forget\b.*\binstructions?",
    r"forget\b.*\bsystem prompt",
    r"you are now",
    r"new (persona|identity|role|instructions?)",
    r"bypass\b.*",
    r"jailbreak",
    r"act as\b.*",
    r"pretend (to be|you are|you're)",
    r"disregard\b.*",
    r"override\b.*",
            
        ],
        "legal_compliance": [
            r"(is|are) (this|these|the) (test|assessment|practice) legal",
            r"discriminat(e|ion|ory)",
            r"comply with (gdpr|ccpa|eeoc|ada|hipaa)",
            r"(legal|liability) (risk|issue|advice|concern)",
            r"lawsuit",
            r"wrongful (termination|dismissal)",
        ],
        "hiring_strategy": [
            r"how (should|do) i (structure|run|conduct) (the |an? )?interview",
            r"best practice(s)? for (hiring|interviewing|recruiting)",
            r"hiring strategy",
            r"interview technique",
            r"how to (hire|fire|dismiss|lay off)",
            r"onboarding (process|plan|strategy)",
            r"compensation (structure|bench|plan)",
            r"salary (band|benchmark|negotiation)",
        ],
        "competitor_vendor": [
            r"(assessments?|tests?) from (hogan|sova|criteria|talent\+|cut[-\s]?e|mettl|hackerrank|codility|talentq)",
            r"alternative(s)? to shl",
            r"(non-?shl|outside shl|other vendor)",
            r"compare shl (to|with|vs\.?) (hogan|sova|criteria|mettl)",
        ],
        "general_knowledge": [
            r"^(what is|explain|define|tell me about) (artificial intelligence|machine learning|python|java|sql)$",
            r"write (me )?(a |an )?(code|script|program|essay|poem|story)",
            r"(book|movie|song|recipe) recommendation",
            r"weather (in|at|for)",
            r"stock (price|market|tip)",
            r"translate (this|to|from)",
        ],
    }

    # ── Messages ────────────────────────────────────────────────────────

    _REFUSAL_MESSAGES = {
        "prompt_injection": (
            "I'm focused on helping you find the right SHL assessments and can't "
            "respond to that type of request. How can I help with assessment selection?"
        ),
        "legal_compliance": (
            "Legal compliance questions are outside my scope — I'd recommend consulting "
            "your legal team or an HR compliance specialist. I'm here to help you choose "
            "the right SHL assessments for your role. What role are you hiring for?"
        ),
        "hiring_strategy": (
            "Interview and hiring strategy advice is beyond what I can help with, but I "
            "can recommend the right SHL assessments to support your selection process. "
            "What role are you assessing candidates for?"
        ),
        "competitor_vendor": (
            "I specialise in SHL assessments only and can't compare or recommend "
            "assessments from other providers. Is there an SHL assessment I can help "
            "you with instead?"
        ),
        "general_knowledge": (
            "That's outside my area — I'm here specifically to help you select SHL "
            "assessments for your hiring needs. What role or skill would you like to "
            "assess?"
        ),
        "off_topic": (
            "I specialize in recommending SHL assessments for hiring. For other topics, "
            "I'd suggest consulting the relevant specialist. How can I help with "
            "assessment selection today?"
        ),
    }

    # ── Public API ──────────────────────────────────────────────────────

    def check(self, message: str) -> Optional[str]:
        """
        Check whether the message is in scope.

        Returns:
            None  — message is in scope, proceed normally
            str   — out-of-scope category name; caller should refuse
        """
        msg_lower = message.lower().strip()

        # Short harmless messages — always in scope
        for pattern in self._ALWAYS_IN_SCOPE:
            if re.search(pattern, msg_lower):
                logger.debug("ScopeChecker: harmless short message — in scope")
                return None

        # Check each out-of-scope category
        for category, patterns in self._OUT_OF_SCOPE.items():
            for pattern in patterns:
                if re.search(pattern, msg_lower):
                    logger.warning(f"ScopeChecker: out-of-scope [{category}] — '{message[:60]}'")
                    return category

        return None  # in scope

    def is_in_scope(self, message: str) -> bool:
        """Convenience boolean wrapper around check()."""
        return self.check(message) is None

    def get_refusal_message(self, category: Optional[str] = None) -> str:
        """Return an appropriate refusal message for the given category."""
        if category and category in self._REFUSAL_MESSAGES:
            return self._REFUSAL_MESSAGES[category]
        return self._REFUSAL_MESSAGES["off_topic"]