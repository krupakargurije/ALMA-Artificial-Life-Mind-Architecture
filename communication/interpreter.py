"""Deterministic semantic interpreter for ALC communication.

Strict Rule: No LLM, no external NLP API.
Deterministic pattern and symbol extraction to parse user queries, statements,
greetings, and teaching directives into grounded cognitive intents.
"""

from dataclasses import dataclass, field
import re
from typing import Any, Dict, List, Optional, Tuple

from communication.message import CommType, KnowledgeStatus
from communication.vocabulary import ConceptLexicon


@dataclass
class ParsedIntent:
    """Structured representation of an incoming message's intent."""
    intent_type: str                         # "greeting", "query_identity", "query_peer", "query_activity", "query_location", "query_need", "query_what_is", "query_effect", "query_learned", "query_status", "teach", "statement", "unknown"
    target_concept: Optional[str] = None     # Concept symbol queried (e.g. "water", "tree", "plant", "Alpha", "Roselia")
    claimed_effect: Optional[Dict[str, float]] = None  # Claimed need delta for teaching
    raw_text: str = ""
    is_understood: bool = True
    unrecognized_tokens: List[str] = field(default_factory=list)


class MessageInterpreter:
    """Parses natural language and symbolic inputs using an agent's private lexicon."""

    def __init__(self, lexicon: ConceptLexicon):
        self.lexicon = lexicon

    def parse(self, text: str) -> ParsedIntent:
        """Parse raw text into a semantic cognitive intent."""
        cleaned = text.strip()
        lower = cleaned.lower().rstrip("?!.,")

        # 1. Greetings: "hello", "hi", "hey", "greetings", "good morning", "good day"
        greeting_words = ["hello", "hi", "hey", "greetings", "good morning", "good afternoon", "good day", "howdy"]
        if lower in greeting_words or any(lower.startswith(w + " ") for w in greeting_words):
            return ParsedIntent(intent_type="greeting", raw_text=cleaned)

        # 2. Identity queries: "who are you", "what is your name", "tell me about yourself"
        if any(p in lower for p in ["who are you", "what is your name", "what's your name", "tell me about yourself", "who made you"]):
            return ParsedIntent(intent_type="query_identity", raw_text=cleaned)

        # 3. Peer queries: "who is albedo", "who is alpha", "do you know albedo", "where is albedo"
        if any(name in lower for name in ["albedo", "roselia"]) and any(p in lower for p in ["who is", "what is", "do you know", "where is", "tell me about", "have you seen"]):
            return ParsedIntent(intent_type="query_peer", target_concept="Albedo", raw_text=cleaned)
        if "alpha" in lower and any(p in lower for p in ["who is", "what is", "do you know", "where is", "tell me about", "have you seen"]):
            return ParsedIntent(intent_type="query_peer", target_concept="Alpha", raw_text=cleaned)

        # 4. Activity / Action queries: "what are you doing", "what are you doing right now", "what are you holding"
        if any(p in lower for p in ["what are you doing", "what are you doing right now", "what are you holding", "what are you working on"]):
            return ParsedIntent(intent_type="query_activity", raw_text=cleaned)

        # 5. Location queries: "where are you", "what is your position", "where are you right now"
        if any(p in lower for p in ["where are you", "what is your position", "where are you located", "what are your coordinates"]):
            return ParsedIntent(intent_type="query_location", raw_text=cleaned)

        # 6. Specific need state queries: "are you thirsty", "are you hungry", "are you tired", "are you hurt", "are you healthy"
        if any(p in lower for p in ["are you thirsty", "do you need water", "do you want water", "are you in need of water"]):
            return ParsedIntent(intent_type="query_need", target_concept="water", raw_text=cleaned)
        if any(p in lower for p in ["are you hungry", "do you need food", "do you want food", "do you need to eat"]):
            return ParsedIntent(intent_type="query_need", target_concept="food", raw_text=cleaned)
        if any(p in lower for p in ["are you tired", "do you have energy", "are you exhausted", "need rest", "are you sleepy"]):
            return ParsedIntent(intent_type="query_need", target_concept="energy", raw_text=cleaned)
        if any(p in lower for p in ["are you hurt", "are you injured", "are you in pain", "did you take damage"]):
            return ParsedIntent(intent_type="query_need", target_concept="health", raw_text=cleaned)
        if any(p in lower for p in ["are you healthy", "are you well", "are you okay"]):
            return ParsedIntent(intent_type="query_need", target_concept="healthy", raw_text=cleaned)

        # 7. General Status queries: "how are you", "status", "needs", "how do you feel"
        if any(p in lower for p in ["how are you", "how do you feel", "status", "how are your needs"]):
            return ParsedIntent(intent_type="query_status", raw_text=cleaned)

        # 8. Learning queries: "what did you learn", "what have you discovered", "what do you know"
        if any(p in lower for p in ["what did you learn", "what have you discovered", "what do you know", "tell me what you learned"]):
            return ParsedIntent(intent_type="query_learned", raw_text=cleaned)

        # 9. Explicit Teach syntax: "teach: <symbol> is <type>:<id>" or "this is <symbol>"
        teach_match = re.search(r"teach:\s*([a-zA-Z0-9_-]+)\s*(?:is|=|as)\s*([a-zA-Z0-9_-]+)(?::([0-9]+))?", lower)
        if teach_match:
            sym = teach_match.group(1).strip()
            ctype = teach_match.group(2).strip()
            cid = int(teach_match.group(3)) if teach_match.group(3) else 0
            return ParsedIntent(
                intent_type="teach",
                target_concept=sym,
                raw_text=cleaned,
                claimed_effect={"type": ctype, "id": cid},
            )

        if lower.startswith("this is ") or lower.startswith("here is "):
            sym = re.sub(r"^(this is|here is)\s+(a\s+|an\s+|the\s+)?", "", lower).strip().rstrip("!.")
            return ParsedIntent(intent_type="teach", target_concept=sym, raw_text=cleaned)

        # 10. Effect queries: "what does X do?", "what happens when you X?", "what makes X grow?", "what helps with X?"
        effect_patterns = [
            r"what does\s+([a-zA-Z0-9_-]+)\s+do",
            r"what happens (?:when|if) you\s+([a-zA-Z0-9_-]+)",
            r"what makes\s+(?:the\s+)?([a-zA-Z0-9_-]+)\s+grow",
            r"what helps (?:with|for)\s+([a-zA-Z0-9_-]+)",
            r"how do you (?:get|make|use)\s+([a-zA-Z0-9_-]+)",
        ]
        for pat in effect_patterns:
            m = re.search(pat, lower)
            if m:
                target = m.group(1).strip()
                is_known = self.lexicon.is_known(target)
                return ParsedIntent(
                    intent_type="query_effect",
                    target_concept=target,
                    raw_text=cleaned,
                    is_understood=is_known,
                    unrecognized_tokens=[] if is_known else [target],
                )

        # 11. Definitional queries: "what is X?", "tell me about X", "what is a X?"
        what_is_patterns = [
            r"what is\s+(?:a\s+|an\s+|the\s+)?([a-zA-Z0-9_-]+)",
            r"tell me about\s+(?:a\s+|an\s+|the\s+)?([a-zA-Z0-9_-]+)",
            r"define\s+([a-zA-Z0-9_-]+)",
            r"do you know\s+(?:what\s+)?(?:a\s+|an\s+|the\s+)?([a-zA-Z0-9_-]+)\s+is",
        ]
        for pat in what_is_patterns:
            m = re.search(pat, lower)
            if m:
                target = m.group(1).strip()
                is_known = self.lexicon.is_known(target)
                return ParsedIntent(
                    intent_type="query_what_is",
                    target_concept=target,
                    raw_text=cleaned,
                    is_understood=is_known,
                    unrecognized_tokens=[] if is_known else [target],
                )

        # 12. Single word query: e.g. "water?", "tree?", "food?"
        word_match = re.match(r"^([a-zA-Z0-9_-]+)\??$", lower)
        if word_match:
            target = word_match.group(1).strip()
            is_known = self.lexicon.is_known(target)
            return ParsedIntent(
                intent_type="query_what_is",
                target_concept=target,
                raw_text=cleaned,
                is_understood=is_known,
                unrecognized_tokens=[] if is_known else [target],
            )

        # 13. Statements / Testimony from another agent (e.g. "water reduces thirst", "poison hurts")
        statement_patterns = [
            (r"([a-zA-Z0-9_-]+)\s+(?:reduces|helps with|quenches)\s+thirst", "water", {"water": 30.0}),
            (r"([a-zA-Z0-9_-]+)\s+(?:reduces|helps with|satisfies)\s+hunger", "food", {"food": 25.0}),
            (r"([a-zA-Z0-9_-]+)\s+(?:hurts|damages|harms|poisons)", "health", {"health": -30.0}),
            (r"([a-zA-Z0-9_-]+)\s+(?:restores|heals)\s+health", "health", {"health": 20.0}),
        ]
        for pat, need, delta in statement_patterns:
            m = re.search(pat, lower)
            if m:
                subj = m.group(1).strip()
                return ParsedIntent(
                    intent_type="statement",
                    target_concept=subj,
                    claimed_effect=delta,
                    raw_text=cleaned,
                )

        # Fallback: Unrecognized input
        return ParsedIntent(
            intent_type="unknown",
            raw_text=cleaned,
            is_understood=False,
            unrecognized_tokens=[lower],
        )
