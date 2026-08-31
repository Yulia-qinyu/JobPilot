import hashlib
import unicodedata
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
        jd_hash = self.structured_jd_hash(requirements)
        if requirements.requirement_taxonomy_version == "v2":
            # V2 keeps ONE canonical requirement identity end to end: the
            # reqv2_* id stored on StructuredRequirement flows unchanged into the
            # matcher input/output, RequirementMatch, and score_basis.
            seen_ids: set[str] = set()
            v2_catalog: list[ScoredRequirement] = []
            for item in requirements.requirements:
                if item.requirement_type != "matchable":
                    continue
                cleaned = " ".join(item.normalized_requirement.split())
                if not cleaned or item.requirement_id in seen_ids:
                    continue
                seen_ids.add(item.requirement_id)
                v2_catalog.append(
                    ScoredRequirement(
                        requirement_id=item.requirement_id,
                        text=cleaned,
                        context=" ".join(item.source_text.split()),
                        importance_hint=self._importance_hint(item.importance),
                        source_kind="v2_matchable",
                    )
                )
            return RequirementCatalog(v2_catalog, jd_hash)

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

    @staticmethod
    def _importance_hint(importance: str) -> str:
        return {"Critical": "high", "Important": "medium", "Preferred": "low"}[importance]

    @staticmethod
    def structured_jd_hash(requirements: JDRequirements | dict) -> str:
        requirements = JDRequirements.model_validate(requirements)
        if requirements.requirement_taxonomy_version == "legacy-v1":
            # Preserve the exact pre-V2 hash payload so additive schema defaults do not
            # invalidate every historical analysis.
            legacy_fields = (
                "role",
                "company",
                "location",
                "recruitment_type",
                "published_date",
                "role_summary",
                "key_requirements",
                "knowledge_topics",
                "responsibilities",
                "required_skills",
                "preferred_skills",
                "ai_requirements",
                "product_requirements",
                "technical_requirements",
                "domain_requirements",
            )
            payload = requirements.model_dump(mode="json", include=set(legacy_fields))
            return canonical_hash(payload)
        canonical_requirements = sorted(
            (
                item.model_dump(mode="json")
                for item in requirements.requirements
            ),
            key=lambda item: item["requirement_id"],
        )
        return canonical_hash(
            {
                "requirement_taxonomy_version": "v2",
                "requirements": canonical_requirements,
            }
        )

    @staticmethod
    def stable_requirement_id(
        *,
        source_text: str,
        normalized_requirement: str,
        requirement_type: str,
        source_section: str,
        duplicate_ordinal: int = 0,
    ) -> str:
        values = (
            RequirementCatalogBuilder._stable_text(source_text),
            RequirementCatalogBuilder._stable_text(normalized_requirement),
            requirement_type,
            source_section,
            str(duplicate_ordinal),
        )
        digest = hashlib.sha256("\x1f".join(values).encode("utf-8")).hexdigest()[:16]
        return f"reqv2_{digest}"

    @staticmethod
    def _stable_text(value: str) -> str:
        return " ".join(unicodedata.normalize("NFKC", value).casefold().split())
