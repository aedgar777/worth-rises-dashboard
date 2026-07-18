"""Classify raw provider records as include, exclude, or review."""

import re
from dataclasses import dataclass, field

EXCLUDE_RULES: list[tuple[str, str]] = [
    (r"\bjuvenile\b", "juvenile facility"),
    (r"\byouth\b", "youth facility"),
    (r"\bjjdc\b", "juvenile detention (JJDC)"),
    (r"\bfederal\b", "federal facility"),
    (r"\bice\b", "ICE / immigration detention"),
    (r"\bimmigration\b", "immigration facility"),
    (r"\bwork\s+release\b", "work release program"),
    (r"\breentry\b", "reentry program"),
    (r"\bhalfway\b", "halfway house"),
    (r"\belectronic\s+monitor", "electronic monitoring"),
    (r"\bprobation\b", "probation program"),
    (r"\bparole\b", "parole program"),
    (r"\bcommunity\s+correction", "community corrections"),
    (r"\btransitional\b", "transitional facility"),
    (r"\btreatment\s+center\b", "treatment center"),
    (r"\bmental\s+health\b", "mental health facility"),
    (r"\bhospital\b", "hospital"),
    (r"\bprivate\b", "private facility"),
    (r"\bcontract\b", "contract facility"),
    (r"\bregional\s+jail\b", "regional jail"),
    (r"\bmulti[- ]county\b", "multi-county facility"),
]

JAIL_INCLUDE_PATTERNS = [
    (r"\bjail\b", "county jail"),
    (r"\bsheriff", "sheriff office"),
    (r"\bdetention\s+center\b", "detention center"),
    (r"\bcorrectional\s+center\b", "correctional center"),
    (r"\bcounty\s+correction", "county corrections"),
    (r"\bpublic\s+safety\b", "public safety facility"),
]

PRISON_INCLUDE_PATTERNS = [
    (r"\bdepartment\s+of\s+correction", "department of corrections"),
    (r"\bdoc\b", "DOC facility"),
    (r"\bstate\s+prison\b", "state prison"),
    (r"\bpenitentiary\b", "penitentiary"),
    (r"\bcorrectional\s+institution\b", "correctional institution"),
    (r"\bcorrectional\s+facility\b", "correctional facility"),
]


@dataclass
class Classification:
    """Outcome of applying keyword rules to one raw facility for a jurisdiction type."""

    decision: str  # include | exclude | review
    reason: str
    matched_exclude_rules: list[str] = field(default_factory=list)
    matched_include_signals: list[str] = field(default_factory=list)


def _matched_labels(text: str, rules: list[tuple[str, str]]) -> list[str]:
    """Return human labels for every regex rule that matches the facility text."""
    return [label for pattern, label in rules if re.search(pattern, text, re.IGNORECASE)]


def matched_exclude_rules(facility_name: str, facility_type: str) -> list[str]:
    """List exclusion rule labels that fired for this facility (empty if none)."""
    combined = f"{facility_name} {facility_type}".strip()
    return _matched_labels(combined, EXCLUDE_RULES)


def classify_record(
    facility_name: str,
    facility_type: str,
    jurisdiction_type: str,
) -> Classification:
    """Label a raw facility as include, exclude, or review for the target jurisdiction.

    Excluded facilities never participate in matching. Included facilities are strong
    candidates (jail names for counties, DOC/prison names for states). Review means
    the facility type looks plausible but mismatched for the jurisdiction level.
    """
    combined = f"{facility_name} {facility_type}".strip()
    exclude_rules = _matched_labels(combined, EXCLUDE_RULES)

    # Hard stop: juvenile, federal, ICE, work release, etc. never map to a jurisdiction.
    if exclude_rules:
        return Classification(
            "exclude",
            "Matched exclusion keyword",
            matched_exclude_rules=exclude_rules,
        )

    if jurisdiction_type == "state":
        include_signals = _matched_labels(combined, PRISON_INCLUDE_PATTERNS)
        if include_signals:
            return Classification(
                "include",
                "State prison / DOC facility",
                matched_include_signals=include_signals,
            )
        jail_signals = _matched_labels(combined, JAIL_INCLUDE_PATTERNS)
        # A county jail name shouldn't be the primary match for a state DOC row.
        if jail_signals:
            return Classification(
                "review",
                "Jail-like name on state jurisdiction",
                matched_include_signals=jail_signals,
            )
        return Classification("review", "Unclassified state facility")

    if jurisdiction_type == "county":
        include_signals = _matched_labels(combined, JAIL_INCLUDE_PATTERNS)
        if include_signals:
            return Classification(
                "include",
                "County jail / sheriff facility",
                matched_include_signals=include_signals,
            )
        prison_signals = _matched_labels(combined, PRISON_INCLUDE_PATTERNS)
        # A state prison name on a county row is suspicious — keep for manual review.
        if prison_signals:
            return Classification(
                "review",
                "Prison-like name on county jurisdiction",
                matched_include_signals=prison_signals,
            )
        return Classification("review", "Unclassified county facility")

    return Classification("review", "Unknown jurisdiction type")


def describe_facility_rules(
    facility_name: str,
    facility_type: str,
    jurisdiction_type: str,
    *,
    match_score: float | None = None,
    score_reason: str | None = None,
    match_confidence: float | None = None,
) -> str:
    """Build a CSV-friendly explanation of why a facility was excluded or not chosen.

    Used heavily on unmatched rows so reviewers can see which keyword rules and score
    thresholds blocked a match without opening the code.
    """
    classification = classify_record(facility_name, facility_type, jurisdiction_type)
    parts: list[str] = []

    if classification.matched_exclude_rules:
        parts.append(
            "Excluded by facility rules: "
            + "; ".join(classification.matched_exclude_rules)
        )
    else:
        parts.append(f"Classification: {classification.decision} ({classification.reason})")
        if classification.matched_include_signals:
            parts.append(
                "Matched include signals: "
                + "; ".join(classification.matched_include_signals)
            )

    if match_score is not None:
        parts.append(f"Match score {match_score:.2f}")
        if score_reason:
            parts.append(score_reason)

    if match_confidence is not None and match_confidence < 0.45:
        parts.append("Below jurisdiction match threshold (0.45)")

    return "; ".join(parts)
