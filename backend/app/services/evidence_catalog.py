import hashlib
import json
from dataclasses import dataclass

from app.db.models import UserProfile
from app.schemas.analysis import ResumeProfile
from app.schemas.fit_analysis import EvidenceSourceRead


def canonical_hash(value: object) -> str:
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class EvidenceCatalog:
    sources: list[EvidenceSourceRead]
    resume_hash: str
    experience_bank_hash: str

    @property
    def by_catalog_id(self) -> dict[str, EvidenceSourceRead]:
        return {EvidenceCatalogBuilder.catalog_id(source): source for source in self.sources}


class EvidenceCatalogBuilder:
    """Maps Phase 1 storage semantics to explicit Phase 3 provenance."""

    @staticmethod
    def catalog_id(source: EvidenceSourceRead) -> str:
        return f"{source.source_type}:{source.source_id}"

    def build(self, profile: UserProfile) -> EvidenceCatalog:
        if profile.resume is None:
            raise ValueError("A Master Resume is required before running Fit Analysis.")

        structured = ResumeProfile.model_validate(profile.resume.structured_profile)
        sources: list[EvidenceSourceRead] = []
        for experience in profile.experiences:
            context = " · ".join(
                item
                for item in (experience.organization, experience.title, experience.date_range)
                if item
            )
            for fact in experience.facts:
                provenance = self._eligible_provenance(fact.source_type, fact.confirmed)
                if provenance is None:
                    continue
                sources.append(
                    EvidenceSourceRead(
                        source_type=provenance,
                        source_id=str(fact.id),
                        text=fact.text.strip(),
                        context=context,
                    )
                )

        # Database-backed facts take precedence over duplicate parser summary entries.
        sources.extend(self._resume_profile_sources(profile.resume.id, structured))

        sources = self._deduplicate(sources)
        resume_hash = canonical_hash(structured.model_dump(mode="json"))
        experience_hash = canonical_hash(
            [
                {
                    "catalog_id": self.catalog_id(source),
                    "text": source.text,
                    "context": source.context,
                }
                for source in sources
                if source.source_id.isdigit()
            ]
        )
        return EvidenceCatalog(sources, resume_hash, experience_hash)

    @staticmethod
    def _eligible_provenance(source_type: str, confirmed: bool) -> str | None:
        if source_type == "resume":
            return "resume_extracted"
        if source_type == "manual" and confirmed:
            return "manual_confirmed"
        # manual_unconfirmed, unknown, and future AI-derived facts are deliberately excluded.
        return None

    def _resume_profile_sources(
        self, resume_id: int, profile: ResumeProfile
    ) -> list[EvidenceSourceRead]:
        sources: list[EvidenceSourceRead] = []

        def add(path: str, text: str, context: str = "主简历") -> None:
            cleaned = " ".join(text.split())
            if cleaned:
                sources.append(
                    EvidenceSourceRead(
                        source_type="resume_extracted",
                        source_id=f"resume:{resume_id}:{path}",
                        text=cleaned,
                        context=context,
                    )
                )

        for index, item in enumerate(profile.education):
            add(
                f"education:{index}",
                " · ".join(
                    value
                    for value in (item.institution, item.degree, item.field, item.period)
                    if value
                ),
                "教育经历",
            )
        for field_name in (
            "skills",
            "ai_experience",
            "product_experience",
            "technical_experience",
            "domain_experience",
        ):
            for index, value in enumerate(getattr(profile, field_name)):
                add(f"{field_name}:{index}", value)
        for index, item in enumerate(profile.work_experience):
            add(
                f"work_experience:{index}",
                " · ".join(value for value in (item.company, item.title, item.period) if value),
                "工作经历",
            )
        for index, item in enumerate(profile.projects):
            add(
                f"projects:{index}",
                item.name,
                "项目经历",
            )
            for skill_index, skill in enumerate(item.skills):
                add(f"projects:{index}:skills:{skill_index}", skill, f"项目：{item.name}")
        return sources

    @staticmethod
    def _deduplicate(sources: list[EvidenceSourceRead]) -> list[EvidenceSourceRead]:
        seen: set[str] = set()
        result: list[EvidenceSourceRead] = []
        for source in sources:
            key = " ".join(source.text.casefold().split())
            if not source.text or key in seen:
                continue
            seen.add(key)
            result.append(source)
        return result
