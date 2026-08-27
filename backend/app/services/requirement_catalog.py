import hashlib
from dataclasses import dataclass

from app.schemas.analysis import JDRequirements
from app.services.evidence_catalog import canonical_hash


@dataclass(frozen=True)
class ScoredRequirement:
    requirement_id: str
    text: str
    context: str
    importance_hint: str
    source_kind: str


@dataclass(frozen=True)
class RequirementCatalog:
    requirements: list[ScoredRequirement]
    structured_jd_hash: str

    @property
    def by_id(self) -> dict[str, ScoredRequirement]:
        return {item.requirement_id: item for item in self.requirements}


class RequirementCatalogBuilder:
    def build(self, requirements: JDRequirements | dict) -> RequirementCatalog:
        requirements = JDRequirements.model_validate(requirements)
        jd_hash = canonical_hash(requirements.model_dump(mode="json"))
        candidates: list[tuple[str, str, str, str]] = []
        if requirements.key_requirements:
            candidates.extend(
                (item.title, item.explanation, item.priority, "key_requirement")
                for item in requirements.key_requirements
            )
        else:
            candidates.extend(
                (item, item, "high", "required") for item in requirements.required_skills
            )
            candidates.extend(
                (item, item, "low", "preferred") for item in requirements.preferred_skills
            )

        seen: set[str] = set()
        catalog: list[ScoredRequirement] = []
        for index, (text, context, hint, source_kind) in enumerate(candidates):
            cleaned = " ".join(text.split())
            normalized = cleaned.casefold()
            if not cleaned or normalized in seen:
                continue
            seen.add(normalized)
            digest = hashlib.sha256(f"{jd_hash}:{index}:{normalized}".encode()).hexdigest()[:12]
            catalog.append(
                ScoredRequirement(
                    requirement_id=f"req_{digest}",
                    text=cleaned,
                    context=" ".join(context.split()),
                    importance_hint=hint,
                    source_kind=source_kind,
                )
            )
        return RequirementCatalog(catalog, jd_hash)
