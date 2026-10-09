"""Private Concept Lexicon and Symbol Grounding system for ALC organisms.

Strict Rule: No preloaded English vocabulary dictionary.
Organisms ground symbols to internal sensory IDs (tiles, entities, actions, need drives)
through direct experience, co-occurrence, human teaching, or inter-agent communication.
If a symbol has no grounding, it is explicitly UNKNOWN.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class GroundedConcept:
    """A symbol grounded to an internal sensory or cognitive attribute."""
    symbol: str                               # Surface string token (e.g. "water", "poison", "food")
    concept_type: str                         # "tile", "entity", "action", "need", "effect"
    internal_id: Any                          # e.g. TILE_WATER (3), ENTITY_GOOD_FRUIT (13), DRINK (9)
    confidence: float = 1.0                   # Association confidence (0.0 to 1.0)
    encounter_count: int = 1                  # How many times this association was observed/reinforced
    source: str = "human_teaching"            # "human_teaching", "co_occurrence", "testimony", "self_grounded"
    description: str = ""                     # Short internal description


class ConceptLexicon:
    """An organism's private symbol-grounding lexicon.
    
    Each organism maintains their OWN independent lexicon. Alpha's lexicon
    is separate from Albedo's lexicon.
    """

    def __init__(self, owner: str = "agent"):
        self.owner = owner
        # symbol (lowercase) -> GroundedConcept
        self.symbol_to_concept: Dict[str, GroundedConcept] = {}
        # (concept_type, internal_id) -> symbol
        self.internal_to_symbol: Dict[Tuple[str, Any], str] = {}

    def ground(
        self,
        symbol: str,
        concept_type: str,
        internal_id: Any,
        confidence: float = 1.0,
        source: str = "human_teaching",
        description: str = "",
    ) -> GroundedConcept:
        """Ground a string symbol to an internal sensory ID."""
        key = symbol.strip().lower()
        if key in self.symbol_to_concept:
            # Reinforce existing grounding
            c = self.symbol_to_concept[key]
            c.encounter_count += 1
            c.confidence = min(1.0, c.confidence + 0.1)
            if description:
                c.description = description
            return c

        concept = GroundedConcept(
            symbol=key,
            concept_type=concept_type,
            internal_id=internal_id,
            confidence=confidence,
            encounter_count=1,
            source=source,
            description=description,
        )
        self.symbol_to_concept[key] = concept
        self.internal_to_symbol[(concept_type, internal_id)] = key
        return concept

    def is_known(self, symbol: str) -> bool:
        """Check if a word symbol is grounded in the organism's lexicon."""
        return symbol.strip().lower() in self.symbol_to_concept

    def get(self, symbol: str) -> Optional[GroundedConcept]:
        """Retrieve grounded concept by symbol."""
        return self.symbol_to_concept.get(symbol.strip().lower())

    def get_symbol_for(self, concept_type: str, internal_id: Any) -> Optional[str]:
        """Retrieve grounded symbol for an internal sensory ID."""
        return self.internal_to_symbol.get((concept_type, internal_id))

    def all_known_symbols(self) -> List[str]:
        """Return list of all grounded symbols."""
        return list(self.symbol_to_concept.keys())

    def to_dict(self) -> Dict[str, Any]:
        """Serialize lexicon metadata."""
        return {
            "owner": self.owner,
            "count": len(self.symbol_to_concept),
            "symbols": [
                {
                    "symbol": c.symbol,
                    "type": c.concept_type,
                    "internal_id": c.internal_id,
                    "confidence": c.confidence,
                    "encounters": c.encounter_count,
                    "source": c.source,
                    "description": c.description,
                }
                for c in self.symbol_to_concept.values()
            ],
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Restore lexicon from serialized dictionary."""
        self.owner = data.get("owner", self.owner)
        self.symbol_to_concept.clear()
        self.internal_to_symbol.clear()
        for item in data.get("symbols", []):
            sym = item["symbol"]
            c = GroundedConcept(
                symbol=sym,
                concept_type=item["type"],
                internal_id=item["internal_id"],
                confidence=item.get("confidence", 1.0),
                encounter_count=item.get("encounters", 1),
                source=item.get("source", "human_teaching"),
                description=item.get("description", ""),
            )
            self.symbol_to_concept[sym] = c
            self.internal_to_symbol[(item["type"], item["internal_id"])] = sym
