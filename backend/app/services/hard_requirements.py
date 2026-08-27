import re

from app.schemas.fit_analysis import HardRequirementCategory
from app.services.requirement_catalog import ScoredRequirement

SOFT_LANGUAGE = re.compile(
    r"\b(preferred|nice\s+to\s+have|a\s+plus|familiar\s+with)\b|优先|熟悉|加分",
    re.IGNORECASE,
)
MANDATORY_LANGUAGE = re.compile(
    r"\b(must|required|mandatory|minimum\s+of|at\s+least)\b|必须|硬性|至少|不少于|需具备",
    re.IGNORECASE,
)
EXPERIENCE_THRESHOLD = re.compile(
    r"\b(?:at\s+least\s+|minimum(?:\s+of)?\s+)?\d+\+?\s*(?:years?|yrs?)\b|"
    r"\d+\s*年(?:以上|及以上)|至少\s*\d+\s*年|不少于\s*\d+\s*年",
    re.IGNORECASE,
)
ELIGIBILITY_LANGUAGE = re.compile(
    r"work\s+authori[sz]ation|work\s+eligibility|legally\s+(?:eligible|authorized)|"
    r"citizenship|security\s+clearance|graduat(?:e|ing|ion)\s+(?:class|date)|"
    r"工作许可|合法工作|工作资格|公民身份|安全许可|20\d{2}\s*届|毕业届别",
    re.IGNORECASE,
)
QUALIFICATION_LANGUAGE = re.compile(
    r"\b(certification|certified|licen[cs]e|degree|bachelor|master'?s|ph\.?d\.?)\b|"
    r"资格证|认证|执照|许可证|学历|本科|硕士|博士",
    re.IGNORECASE,
)


def validate_hard_requirement(
    requirement: ScoredRequirement,
    requested_hard: bool,
) -> tuple[bool, HardRequirementCategory]:
    """Conservatively accepts hard classifications supported by explicit JD wording."""
    if not requested_hard:
        return False, "none"

    text = f"{requirement.text} {requirement.context}".strip()
    has_soft_language = bool(SOFT_LANGUAGE.search(text))
    has_mandatory_language = bool(MANDATORY_LANGUAGE.search(text))

    if ELIGIBILITY_LANGUAGE.search(text) and (has_mandatory_language or not has_soft_language):
        return True, "eligibility"
    if EXPERIENCE_THRESHOLD.search(text) and not has_soft_language:
        return True, "experience"
    if QUALIFICATION_LANGUAGE.search(text) and (
        has_mandatory_language or (requirement.source_kind == "required" and not has_soft_language)
    ):
        return True, "qualification"
    if has_mandatory_language and not has_soft_language:
        return True, "other"
    return False, "none"
