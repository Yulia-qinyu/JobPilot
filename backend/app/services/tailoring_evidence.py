import re
import unicodedata
from dataclasses import dataclass

from app.schemas.resume_tailoring import ContextMetadata, DerivedEvidenceSegment


@dataclass(frozen=True)
class SegmentedEvidence:
    claim_text: str
    context_metadata: ContextMetadata
    segments: list[DerivedEvidenceSegment]


class TailoringEvidenceSegmenter:
    """Build a deterministic, Phase-6-only claim view without changing canonical facts."""

    VERSION = "tailoring-evidence-segments-v1"
    MIN_LENGTH = 160
    MIN_SENTENCES = 3
    _metadata_suffix = re.compile(
        r"(?P<title>[^。；;\n｜|]{1,80})\s*[｜|]\s*"
        r"(?P<dates>(?:19|20)\d{2}(?:\.\d{1,2})?\s*[-–—~至到]\s*"
        r"(?:19|20)\d{2}(?:\.\d{1,2})?)\s*$"
    )
    _sentence_boundary = re.compile(r"(?<=[。；;!?！？])\s*|(?<=[.!?])\s+|\n+")

    def segment(
        self,
        *,
        parent_source_id: str,
        text: str,
        experience_title: str,
        organization: str,
        date_range: str,
    ) -> SegmentedEvidence:
        cleaned = " ".join(text.split())
        metadata = ContextMetadata(
            experience_title=experience_title,
            organization=organization,
            project_name=organization if experience_title.casefold() == "project" else "",
            date_range=date_range,
        )
        match = self._metadata_suffix.search(cleaned)
        if match:
            cleaned = cleaned[: match.start()].rstrip("。；; ")
            extracted_title = match.group("title").strip()
            metadata = metadata.model_copy(
                update={
                    "experience_title": extracted_title,
                    "date_range": match.group("dates").strip(),
                }
            )

        sentences = [
            value.strip().rstrip("。；;")
            for value in self._sentence_boundary.split(cleaned)
            if value.strip().rstrip("。；;")
        ]
        should_split = len(cleaned) >= self.MIN_LENGTH or len(sentences) >= self.MIN_SENTENCES
        if not should_split or len(sentences) <= 1:
            return SegmentedEvidence(cleaned, metadata, [])
        segments = [
            DerivedEvidenceSegment(
                segment_id=f"{parent_source_id}#seg{index}",
                parent_source_id=parent_source_id,
                text=sentence,
            )
            for index, sentence in enumerate(sentences, start=1)
        ]
        return SegmentedEvidence(cleaned, metadata, segments)


class MeaningfulChangeDetector:
    VERSION = "meaningful-change-v1"
    _punctuation = re.compile(r"[^\w\u3400-\u9fff]+", re.UNICODE)

    @classmethod
    def normalize(cls, value: str) -> str:
        normalized = unicodedata.normalize("NFKC", value).casefold()
        return cls._punctuation.sub("", normalized)

    @classmethod
    def is_formatting_only(cls, original: str, tailored: str, context: ContextMetadata) -> bool:
        if cls.normalize(original) == cls.normalize(tailored):
            return True
        original_without_metadata = original
        for value in (
            context.experience_title,
            context.organization,
            context.project_name,
            context.date_range,
        ):
            if value:
                original_without_metadata = original_without_metadata.replace(value, "")
        return cls.normalize(original_without_metadata) == cls.normalize(tailored)
