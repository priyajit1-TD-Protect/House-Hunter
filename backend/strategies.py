"""
House-hunting strategy definitions.

Each strategy differs on two axes:
  1. Which freehold property types are eligible
  2. Which transit measure + threshold applies

Everything else (income/school/price/size/lifestyle scoring) is shared.
"""

# Property types eligible per strategy (matched against lowercased Realtor.ca type)
NUCLEUS_TYPES = {
    "house", "detached", "semi-detached", "semi detached",
    "townhouse", "row / townhouse", "att/row/twnhouse",
    "row/townhouse", "link",
}

BIG_FAMILY_TYPES = {
    "house", "detached",   # detached only
}

STRATEGIES = {
    "nucleus": {
        "label": "Nucleus Family",
        "eligible_types": NUCLEUS_TYPES,
        "transit_field": "transit_min_ttc",   # TTC-only to Union
        "transit_target": 40,                  # scoring gradient target (min)
        "exclude_semi": False,
        "exclude_townhouse": False,
    },
    "big_family": {
        "label": "Happy Big Family",
        "eligible_types": BIG_FAMILY_TYPES,
        "transit_field": "transit_min_go",     # incl. GO/rail door-to-door
        "transit_target": 60,                  # hard ceiling is 60 min door-to-door
        "exclude_semi": True,
        "exclude_townhouse": True,
    },
}


def is_eligible_for(prop_type: str, building_type: str, ownership: str, strategy_key: str) -> bool:
    """Return True if this listing's type qualifies for the given strategy."""
    strat = STRATEGIES[strategy_key]
    combined = f"{(prop_type or '').lower()} {(building_type or '').lower()}".strip()
    own = (ownership or "").lower()

    # Never eligible if condo/strata
    if "condo" in own or "strata" in own or "condo" in combined or "apartment" in combined:
        return False

    if strat["exclude_semi"] and ("semi" in combined):
        return False
    if strat["exclude_townhouse"] and (
        "townhouse" in combined or "row" in combined or "twnhouse" in combined or "link" in combined
    ):
        return False

    for t in strat["eligible_types"]:
        if t in combined:
            return True

    # Freehold house with a blank/generic type still counts if not excluded above
    if "freehold" in own:
        return True

    return False
