import re
from dataclasses import dataclass

from app.schemas.fit_analysis import EvidenceSourceRead, MatchConfidence, RequirementMatchStatus

SIMPLE_COHORT = re.compile(
    r"^\s*(?:20\d{2}\s*届(?:毕业生)?|(?:class\s+of|graduat(?:ing|ion))\s*20\d{2})\s*$",
    re.IGNORECASE,
)
SIMPLE_CAMPUS = re.compile(
    r"^\s*(?:应届(?:毕业生)?|校招(?:候选人)?|new\s+grad(?:uate)?|campus)\s*$",
    re.IGNORECASE,
)
YEAR = re.compile(r"(20\d{2})")
DEGREE_LEVELS = {"本科": 2, "bachelor": 2, "硕士": 3, "master": 3, "博士": 4, "phd": 4}


@dataclass(frozen=True)
class CandidateRequirementNormalization:
    match_status: RequirementMatchStatus
    reason: str
    confidence: MatchConfidence
    evidence_sources: list[EvidenceSourceRead]


class CandidateRequirementEvidenceNormalizer:
    """Deterministically grounds narrow recruitment-identity requirements.

    It intentionally handles only simple cohort/campus requirements and the common
    cohort + degree compound. Broader requirements remain the semantic matcher's job.
    """

    def normalize(
        self,
        requirement_text: str,
        requirement_context: str,
        current_status: RequirementMatchStatus,
        current_reason: str,
        current_confidence: MatchConfidence,
        cited: list[EvidenceSourceRead],
        evidence_by_id: dict[str, EvidenceSourceRead],
    ) -> CandidateRequirementNormalization | None:
        combined = f"{requirement_text} {requirement_context}".strip()
        required_year = self._year_from_text(combined)
        has_cohort_language = bool(
            required_year
            and re.search(
                r"届|毕业(?:生|届别)?|class\s+of|graduat(?:e|ing|ion)",
                combined,
                re.IGNORECASE,
            )
        )
        is_simple_cohort = SIMPLE_COHORT.fullmatch(requirement_text)
        is_simple_campus = SIMPLE_CAMPUS.fullmatch(requirement_text)
        required_degree = self._required_degree(combined) if has_cohort_language else None
        if not (has_cohort_language or is_simple_cohort or is_simple_campus):
            return None

        type_source = evidence_by_id.get("manual_confirmed:profile:candidate_type")
        year_source = evidence_by_id.get("manual_confirmed:profile:graduation_year")
        candidate_type = self._candidate_type(type_source)
        candidate_year = self._year(year_source)

        if is_simple_campus:
            if candidate_type in {"graduate", "both"}:
                return CandidateRequirementNormalization(
                    "Strong",
                    "求职档案已由用户确认当前求职身份包含应届 / 校招。",
                    "High",
                    self._merge(cited, [type_source]),
                )
            if candidate_type == "experienced":
                return CandidateRequirementNormalization(
                    "Missing", "求职档案当前确认的求职身份为社招。", "High", []
                )
            return CandidateRequirementNormalization(
                "Missing", "求职档案尚未确认应届 / 校招身份。", "Low", []
            )

        if required_year is None:
            return None
        cohort_supported = (
            candidate_type in {"graduate", "both"} and candidate_year == required_year
        )
        cohort_conflict = candidate_year is not None and candidate_year != required_year

        if required_degree is None:
            if cohort_supported:
                return CandidateRequirementNormalization(
                    "Strong",
                    f"求职档案已由用户确认毕业届别为 {required_year} 届。",
                    "High",
                    self._merge(cited, [type_source, year_source]),
                )
            if cohort_conflict:
                return CandidateRequirementNormalization(
                    "Missing",
                    f"求职档案确认的毕业届别为 {candidate_year} 届，与岗位要求的 {required_year} 届不同。",
                    "High",
                    [],
                )
            return CandidateRequirementNormalization(
                "Missing", "求职档案尚未确认该毕业届别。", "Low", []
            )

        degree_source = self._degree_source(evidence_by_id.values(), required_degree)
        degree_supported = degree_source is not None
        supported_sources: list[EvidenceSourceRead | None] = []
        if cohort_supported:
            supported_sources.extend([type_source, year_source])
        if degree_supported:
            supported_sources.append(degree_source)

        if cohort_supported and degree_supported:
            return CandidateRequirementNormalization(
                "Strong",
                f"求职档案确认毕业届别为 {required_year} 届，且主简历教育经历支持{self._degree_label(required_degree)}及以上学历。",
                "High",
                self._merge(cited, supported_sources),
            )
        if cohort_supported:
            return CandidateRequirementNormalization(
                "Partial",
                f"求职档案确认毕业届别为 {required_year} 届；当前证据尚未确认{self._degree_label(required_degree)}及以上学历。",
                "High",
                self._merge([], supported_sources),
            )
        if degree_supported:
            reason = (
                f"主简历教育经历支持{self._degree_label(required_degree)}及以上学历，但求职档案确认的毕业届别为 {candidate_year} 届，"
                f"与岗位要求的 {required_year} 届不同。"
                if cohort_conflict
                else f"主简历教育经历支持{self._degree_label(required_degree)}及以上学历，但求职档案尚未确认 {required_year} 届。"
            )
            return CandidateRequirementNormalization(
                "Partial", reason, "High" if cohort_conflict else "Medium", [degree_source]
            )
        if cohort_conflict:
            return CandidateRequirementNormalization(
                "Missing",
                f"求职档案确认的毕业届别为 {candidate_year} 届，与岗位要求的 {required_year} 届不同；学历证据也不足。",
                "High",
                [],
            )
        return CandidateRequirementNormalization(
            "Missing", "求职档案尚未确认该毕业届别，且当前学历证据不足。", "Low", []
        )

    @staticmethod
    def _candidate_type(source: EvidenceSourceRead | None) -> str | None:
        if source is None:
            return None
        if "校招与社招都可以" in source.text:
            return "both"
        if "应届" in source.text or "校招" in source.text:
            return "graduate"
        if "社招" in source.text:
            return "experienced"
        return None

    @staticmethod
    def _year(source: EvidenceSourceRead | None) -> int | None:
        return CandidateRequirementEvidenceNormalizer._year_from_text(source.text) if source else None

    @staticmethod
    def _year_from_text(text: str) -> int | None:
        match = YEAR.search(text)
        return int(match.group(1)) if match else None

    @staticmethod
    def _required_degree(text: str) -> int | None:
        normalized = text.casefold()
        levels = [level for marker, level in DEGREE_LEVELS.items() if marker in normalized]
        return min(levels) if levels else None

    @staticmethod
    def _degree_label(level: int) -> str:
        return {2: "本科", 3: "硕士", 4: "博士"}[level]

    @staticmethod
    def _degree_source(
        sources, required_level: int
    ) -> EvidenceSourceRead | None:
        candidates: list[tuple[int, EvidenceSourceRead]] = []
        for source in sources:
            if source.context != "教育经历":
                continue
            text = source.text.casefold()
            levels = [level for marker, level in DEGREE_LEVELS.items() if marker in text]
            if levels and max(levels) >= required_level:
                candidates.append((max(levels), source))
        return max(candidates, key=lambda item: item[0])[1] if candidates else None

    @staticmethod
    def _merge(
        existing: list[EvidenceSourceRead], additions: list[EvidenceSourceRead | None]
    ) -> list[EvidenceSourceRead]:
        result: list[EvidenceSourceRead] = []
        seen: set[str] = set()
        for source in [*existing, *additions]:
            if source is None:
                continue
            key = f"{source.source_type}:{source.source_id}"
            if key not in seen:
                seen.add(key)
                result.append(source)
        return result
