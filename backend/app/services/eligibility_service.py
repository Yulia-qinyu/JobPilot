import json
import re
from datetime import UTC, datetime

from app.db.models import Job, UserProfile
from app.schemas.analysis import JDRequirements, ResumeProfile
from app.schemas.job_decision import EligibilityResult

SOFT_LANGUAGE = re.compile(
    r"preferred|nice\s+to\s+have|a\s+plus|familiar\s+with|优先|加分|熟悉|有经验者优先",
    re.IGNORECASE,
)
EXPERIENCE = re.compile(
    r"(?:at\s+least\s+|minimum(?:\s+of)?\s+)?(\d+)\+?\s*(?:years?|yrs?)|"
    r"(?:至少|不少于)?\s*(\d+)\s*年(?:以上|及以上)?",
    re.IGNORECASE,
)
COHORT = re.compile(r"(20\d{2})\s*届|graduat(?:e|ing|ion).{0,20}(20\d{2})", re.IGNORECASE)
WORK_AUTH = re.compile(
    r"work\s+authori[sz]ation|legally\s+(?:eligible|authorized)|工作许可|合法工作|工作资格",
    re.IGNORECASE,
)
LANGUAGE = re.compile(
    r"CET[- ]?[46]|TOEFL|IELTS|雅思|托福|英语(?:六级|四级|专业八级)|日语N[1-5]", re.IGNORECASE
)
CERTIFICATION = re.compile(
    r"certification|certified|licen[cs]e|资格证|认证|执照|许可证", re.IGNORECASE
)
RELEVANT_EXPERIENCE = re.compile(r"相关|产品|AI|人工智能|大模型|数据|金融|fintech", re.IGNORECASE)
HARD_LANGUAGE = re.compile(
    r"\bmust\b|\brequired\b|\bmandatory\b|at\s+least|minimum|必须|至少|不少于|需具备",
    re.IGNORECASE,
)

DEGREE_LEVELS = {
    "associate": 1,
    "大专": 1,
    "专科": 1,
    "bachelor": 2,
    "本科": 2,
    "master": 3,
    "硕士": 3,
    "phd": 4,
    "doctor": 4,
    "博士": 4,
}


class EligibilityService:
    VERSION = "eligibility-rules-v1"

    def evaluate(self, profile: UserProfile, job: Job) -> EligibilityResult:
        if profile.resume is None:
            return EligibilityResult(status="Unknown", reasons=["缺少主简历，暂无法判断投递门槛。"])
        try:
            candidate = ResumeProfile.model_validate(profile.resume.structured_profile)
            jd = JDRequirements.model_validate(job.structured_jd)
        except (TypeError, ValueError):
            return EligibilityResult(
                status="Unknown", reasons=["候选人档案或岗位要求格式不足以可靠判断。"]
            )

        requirements = self._requirements(jd)
        if not requirements and not jd.responsibilities:
            return EligibilityResult(status="Unknown", reasons=["岗位缺少可判断的职责与要求。"])

        reasons: list[str] = []
        blocking: list[str] = []
        unknown: list[str] = []
        candidate_text = json.dumps(candidate.model_dump(mode="json"), ensure_ascii=False)
        years = self._professional_years(candidate)
        degree = self._highest_degree(candidate)
        graduation_year = (
            profile.graduation_year
            if profile.candidate_type in {"graduate", "both"}
            else None
        )

        for requirement in requirements:
            if SOFT_LANGUAGE.search(requirement):
                continue
            if not self._is_explicit_hard(requirement):
                continue
            cohort = COHORT.search(requirement)
            if cohort:
                required_year = int(cohort.group(1) or cohort.group(2))
                if graduation_year is None:
                    unknown.append(requirement)
                elif graduation_year != required_year:
                    blocking.append(requirement)
                else:
                    reasons.append(f"求职档案已确认毕业届别为 {required_year}。")
                    required_degree = self._required_degree(requirement)
                    if required_degree is not None:
                        if degree is None:
                            unknown.append(requirement)
                        elif degree < required_degree:
                            blocking.append(requirement)
                        else:
                            reasons.append("已记录的最高学历不低于岗位明确门槛。")
                continue

            required_degree = self._required_degree(requirement)
            if required_degree is not None:
                if degree is None:
                    unknown.append(requirement)
                elif degree < required_degree:
                    blocking.append(requirement)
                else:
                    reasons.append("已记录的最高学历不低于岗位明确门槛。")
                continue

            experience = EXPERIENCE.search(requirement)
            if experience:
                required_years = int(experience.group(1) or experience.group(2))
                if years is None:
                    unknown.append(requirement)
                elif years < required_years:
                    blocking.append(requirement)
                elif RELEVANT_EXPERIENCE.search(requirement):
                    unknown.append(requirement)
                else:
                    reasons.append(f"可解析工作经历约 {years:g} 年，不低于最低年限。")
                continue

            if WORK_AUTH.search(requirement):
                if self._candidate_mentions(requirement, candidate_text):
                    reasons.append("候选人档案包含相应工作资格信息。")
                else:
                    unknown.append(requirement)
                continue
            if LANGUAGE.search(requirement) or CERTIFICATION.search(requirement):
                if self._candidate_mentions(requirement, candidate_text):
                    reasons.append("候选人档案包含相应语言或资格信息。")
                else:
                    unknown.append(requirement)

        if blocking:
            return EligibilityResult(
                status="Ineligible",
                reasons=[*reasons, "存在候选人事实与明确投递门槛的冲突。"],
                blocking_requirements=self._deduplicate(blocking),
                unknown_requirements=self._deduplicate(unknown),
            )
        if unknown:
            return EligibilityResult(
                status="PossiblyEligible",
                reasons=[*reasons, "未发现明确冲突，但仍有硬性条件需要确认。"],
                unknown_requirements=self._deduplicate(unknown),
            )
        return EligibilityResult(
            status="Eligible",
            reasons=[*reasons, "未发现与候选人已知事实冲突的明确投递门槛。"],
        )

    @staticmethod
    def _requirements(jd: JDRequirements) -> list[str]:
        values = [*jd.required_skills]
        values.extend(item.title for item in jd.key_requirements if item.priority != "low")
        values.extend(item.explanation for item in jd.key_requirements if item.priority != "low")
        return EligibilityService._deduplicate(values)

    @staticmethod
    def _is_explicit_hard(requirement: str) -> bool:
        if HARD_LANGUAGE.search(requirement):
            return True
        if COHORT.search(requirement) or WORK_AUTH.search(requirement):
            return True
        if LANGUAGE.search(requirement) or CERTIFICATION.search(requirement):
            return True
        if re.search(
            r"本科及以上|硕士及以上|博士及以上|bachelor(?:'s)?\s+or\s+higher",
            requirement,
            re.IGNORECASE,
        ):
            return True
        return bool(
            re.search(
                r"\d+\+\s*(?:years?|yrs?)|\d+\s*年(?:以上|及以上)",
                requirement,
                re.IGNORECASE,
            )
        )

    @staticmethod
    def _professional_years(candidate: ResumeProfile) -> float | None:
        intervals: list[tuple[int, int]] = []
        current_year = datetime.now(UTC).year
        for item in candidate.work_experience:
            period = item.period or ""
            years = [int(value) for value in re.findall(r"(?:19|20)\d{2}", period)]
            if not years:
                return None
            start = years[0]
            end = (
                years[-1]
                if len(years) > 1
                else current_year
                if re.search(r"present|current|至今|现在", period, re.IGNORECASE)
                else years[0]
            )
            if end < start or end - start > 50:
                return None
            intervals.append((start, end))
        if not intervals:
            return None
        intervals.sort()
        merged: list[list[int]] = []
        for start, end in intervals:
            if not merged or start > merged[-1][1]:
                merged.append([start, end])
            else:
                merged[-1][1] = max(merged[-1][1], end)
        return float(sum(end - start for start, end in merged))

    @staticmethod
    def _highest_degree(candidate: ResumeProfile) -> int | None:
        levels = []
        for item in candidate.education:
            text = f"{item.degree or ''} {item.field or ''}".casefold()
            levels.extend(level for marker, level in DEGREE_LEVELS.items() if marker in text)
        return max(levels) if levels else None

    @staticmethod
    def _required_degree(requirement: str) -> int | None:
        text = requirement.casefold()
        matches = [level for marker, level in DEGREE_LEVELS.items() if marker in text]
        return min(matches) if matches else None

    @staticmethod
    def _graduation_year(candidate: ResumeProfile) -> int | None:
        years: list[int] = []
        for item in candidate.education:
            period_years = re.findall(r"(?:19|20)\d{2}", item.period or "")
            if period_years:
                years.append(int(period_years[-1]))
        return max(years) if years else None

    @staticmethod
    def _candidate_mentions(requirement: str, candidate_text: str) -> bool:
        tokens = re.findall(
            r"CET[- ]?[46]|TOEFL|IELTS|雅思|托福|工作许可|work authorization",
            requirement,
            re.IGNORECASE,
        )
        return bool(tokens) and all(
            token.casefold() in candidate_text.casefold() for token in tokens
        )

    @staticmethod
    def _deduplicate(values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            cleaned = " ".join(value.split())
            key = cleaned.casefold()
            if cleaned and key not in seen:
                seen.add(key)
                result.append(cleaned)
        return result
