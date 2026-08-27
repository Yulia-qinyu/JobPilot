from dataclasses import dataclass

from app.schemas.discovery import DiscoverySearchContext
from app.schemas.profile import RoleFamily


@dataclass(frozen=True)
class CandidateEvidenceItem:
    evidence_ref: str
    source_type: str
    text: str
    context: str


@dataclass(frozen=True)
class CandidateEvidenceTopic:
    topic: str
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True)
class CandidateDiscoveryContext:
    professional_years: float | None
    education_level: int | None
    graduation_year: int | None
    evidence: tuple[CandidateEvidenceItem, ...]
    evidence_topics: tuple[CandidateEvidenceTopic, ...]
    context_version: str
    limited: bool
    candidate_type: str | None = None

    @property
    def evidence_by_ref(self) -> dict[str, CandidateEvidenceItem]:
        return {item.evidence_ref: item for item in self.evidence}


@dataclass(frozen=True)
class SavedTargetRole:
    evidence_ref: str
    name: str
    priority: str
    role_family: RoleFamily


@dataclass(frozen=True)
class SavedCareerPreferences:
    target_roles: tuple[SavedTargetRole, ...]
    preferred_location: str | None
    target_companies: tuple[str, ...]


@dataclass(frozen=True)
class PersonalizedRankingInput:
    search_context: DiscoverySearchContext
    candidate_context: CandidateDiscoveryContext
    saved_preferences: SavedCareerPreferences
