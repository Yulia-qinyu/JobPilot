import re

from app.schemas.discovery import (
    DiscoveryHardSignal,
    DiscoveryReason,
    DiscoverySearchContext,
    DiscoverySearchDerived,
)
from app.services.discovery_tags import DiscoveryTagCatalog
from app.services.job_sources.base import ImportedJobDraft

EXPERIENCE_HARD = re.compile(
    r"(?:至少|不少于|minimum(?: of)?|at least)\s*(\d+)\+?\s*(?:年|years?)|"
    r"要求\s*(\d+)\+?\s*年|"
    r"(\d+)\+\s*(?:年|years?)|(\d+)\s*年以上",
    re.IGNORECASE,
)
DEGREE_HARD = re.compile(
    r"本科及以上|硕士及以上|博士(?:及以上)?|"
    r"bachelor(?:['’]s)?(?: degree)?(?: is)? required|"
    r"master(?:['’]s)?(?: degree)?(?: is)? required",
    re.IGNORECASE,
)
LANGUAGE_HARD = re.compile(r"CET[- ]?[46]|雅思|托福|IELTS|TOEFL", re.IGNORECASE)
AUTH_HARD = re.compile(r"工作许可|work authorization|authorized to work", re.IGNORECASE)
QUALIFICATION_MARKER = re.compile(
    r"必须|至少|不少于|需具备|任职要求|必备|mandatory|\bmust\b|\bminimum\b|"
    r"\bat least\b|candidates? must|qualifications? include|required experience|"
    r"(?:degree|license|certification) required",
    re.IGNORECASE,
)
RESPONSIBILITY_MARKER = re.compile(
    r"\byou will\b|\bresponsible for\b|\bwhat you['’]?ll do\b|\bresponsibilities\b|"
    r"\bdesign and develop\b|\bmust\s+(?:design|build|develop|deliver|manage|lead|create)\b|"
    r"工作职责|岗位职责|你将|负责(?:设计|开发|构建|推动|管理)|"
    r"必须(?:负责|设计|开发|构建|推动|完成)",
    re.IGNORECASE,
)
ROLE_EXCLUSIONS = {
    "运营": {"product_operations"},
    "解决方案": {"solution"},
    "工程": {"engineering"},
    "算法": {"algorithm"},
}
JOB_FUNCTION_PATTERNS = {
    "product_management": re.compile(r"产品经理|产品负责人|product\s+(?:manager|owner|lead)", re.IGNORECASE),
    "investment": re.compile(r"投资|投行|investment|asset management|private equity|venture capital", re.IGNORECASE),
    "data_analytics": re.compile(r"数据分析|商业分析|data analyst|analytics", re.IGNORECASE),
    "strategy_consulting": re.compile(r"战略咨询|管理咨询|strategy consultant|consulting", re.IGNORECASE),
    "algorithm_research": re.compile(r"算法|研究科学家|algorithm|research scientist", re.IGNORECASE),
    "engineering": re.compile(r"工程师|研发|developer|engineer", re.IGNORECASE),
    "marketing": re.compile(r"市场营销|品牌营销|市场经理|marketing", re.IGNORECASE),
    "risk_management": re.compile(r"风控|风险管理|risk management|risk control", re.IGNORECASE),
    "operations": re.compile(r"运营|operations?", re.IGNORECASE),
    "solution": re.compile(r"解决方案|solution", re.IGNORECASE),
    "design": re.compile(r"设计师|designer", re.IGNORECASE),
}
INDUSTRY_TERMS = {
    "banking": ("银行", "banking"),
    "financial_services": ("金融", "finance", "financial"),
    "ecommerce": ("电商", "ecommerce", "e-commerce"),
    "consumer_goods": ("消费品", "快消", "fmcg", "consumer goods"),
}
DOMAIN_TERMS = {
    "ai": ("ai", "人工智能"),
    "ai_agent": ("agent", "智能体"),
    "llm": ("大模型", "llm", "large language model"),
    "ai_platform": ("ai 平台", "ai平台", "大模型平台"),
    "multimodal": ("多模态", "multimodal"),
    "aigc": ("aigc", "生成式 ai", "内容生成"),
    "risk_control": ("风控", "risk control"),
    "primary_market": ("一级市场", "primary market"),
    "technology": ("科技", "technology"),
}


def extract_explicit_hard_signals(draft: ImportedJobDraft) -> list[DiscoveryHardSignal]:
    signals: list[DiscoveryHardSignal] = []
    for requirement in draft.structured_jd.required_skills:
        source = " ".join(requirement.split())[:240]
        if not _is_qualification_statement(requirement):
            continue
        experience = EXPERIENCE_HARD.search(requirement)
        if experience:
            years = int(
                experience.group(1)
                or experience.group(2)
                or experience.group(3)
                or experience.group(4)
            )
            signals.append(
                DiscoveryHardSignal(
                    type="experience_years",
                    operator=">=",
                    value=years,
                    display=f"明确要求 {years}+ 年经验",
                    source_text=source,
                )
            )
        elif DEGREE_HARD.search(requirement):
            if re.search(r"硕士", requirement, re.IGNORECASE):
                display = "明确要求硕士及以上学历"
            elif re.search(r"博士", requirement, re.IGNORECASE):
                display = "明确要求博士学历"
            else:
                display = "明确要求本科及以上学历"
            signals.append(
                DiscoveryHardSignal(
                    type="degree",
                    operator=">=",
                    value=("master" if "硕士" in display else "doctor" if "博士" in display else "bachelor"),
                    display=display,
                    source_text=source,
                )
            )
        elif LANGUAGE_HARD.search(requirement):
            signals.append(
                DiscoveryHardSignal(
                    type="language", display="存在明确语言等级要求", source_text=source
                )
            )
        elif AUTH_HARD.search(requirement):
            signals.append(
                DiscoveryHardSignal(
                    type="authorization", display="存在明确工作许可要求", source_text=source
                )
            )
        elif QUALIFICATION_MARKER.search(requirement):
            signals.append(
                DiscoveryHardSignal(
                    type="mandatory_other", display="存在明确必备条件", source_text=source
                )
            )
    unique: dict[tuple[str, str], DiscoveryHardSignal] = {}
    for signal in signals:
        unique[(signal.type, signal.display)] = signal
    return list(unique.values())[:5]


def _is_qualification_statement(text: str) -> bool:
    """Reject responsibility prose unless it also contains an explicit qualification marker."""
    if EXPERIENCE_HARD.search(text) or DEGREE_HARD.search(text):
        return True
    if LANGUAGE_HARD.search(text) or AUTH_HARD.search(text):
        return bool(QUALIFICATION_MARKER.search(text))
    if RESPONSIBILITY_MARKER.search(text) and not QUALIFICATION_MARKER.search(text):
        return False
    return bool(QUALIFICATION_MARKER.search(text))


def derive_search_relevance(
    context: DiscoverySearchContext,
    draft: ImportedJobDraft,
    role_family: str,
    hard_signals: list[DiscoveryHardSignal],
    *,
    company_group: str | None = None,
    tags: DiscoveryTagCatalog | None = None,
) -> DiscoverySearchDerived:
    tag_catalog = tags or DiscoveryTagCatalog()
    constraints = context.explicit_constraints
    searchable = f"{draft.role} {draft.original_jd}".casefold()
    title = draft.role.casefold()
    location_text = (draft.location or "").casefold()
    score = 0
    reasons: list[DiscoveryReason] = []
    matched: list[str] = []
    unresolved: list[str] = []
    excluded: list[str] = []

    def match(code: str, label: str, value: int) -> None:
        nonlocal score
        score += value
        matched.append(label)
        reasons.append(DiscoveryReason(kind="matched", code=code, label=label))

    if constraints.companies and draft.company in constraints.companies:
        match("company", draft.company, 3)
    if constraints.company_groups and company_group in constraints.company_groups:
        match("company_group", "受支持的目标公司类型", 2)
    role_compatibility = _role_compatibility(
        constraints.role_families, role_family, draft.role
    )
    function_compatibility = _job_function_compatibility(
        constraints.job_functions, draft.role, role_family
    )
    if constraints.role_families and role_family in constraints.role_families:
        match("role_family", _role_label(role_family), 6)
    elif role_compatibility not in {"mismatch", "unknown_weak"} and any(
        term.casefold() in searchable for term in constraints.role_terms
    ):
        match("role_term", "岗位关键词", 3)
    if constraints.job_functions and function_compatibility == "exact":
        match("job_function", _function_label(constraints.job_functions[0]), 5)
    if constraints.locations and any(
        value.casefold() in location_text for value in constraints.locations
    ):
        labels = [value for value in constraints.locations if value.casefold() in location_text]
        match("location", " / ".join(labels), 3)
    if constraints.recruitment_types and draft.recruitment_type in constraints.recruitment_types:
        label = "校招" if draft.recruitment_type == "campus" else "社招"
        match("recruitment_type", label, 2)
    for term in context.include_terms:
        if term.casefold() in searchable:
            match("include_term", term, 1)
    for tag_id in context.selected_tag_ids:
        tag = tag_catalog.get(tag_id)
        if tag and any(term.casefold() in searchable for term in tag.query_terms):
            match(f"tag:{tag_id}", tag.label, 2)
    for industry in constraints.industries:
        if _contains_any(searchable, INDUSTRY_TERMS.get(industry, (industry,))):
            match(f"industry:{industry}", _concept_label(industry), 2)
    for domain in constraints.domains:
        if _contains_any(searchable, DOMAIN_TERMS.get(domain, (domain,))):
            match(f"domain:{domain}", _concept_label(domain), 2)

    exclusion_families = {
        family
        for term in context.exclusions
        for keyword, families in ROLE_EXCLUSIONS.items()
        if keyword in term
        for family in families
    }
    if role_family in exclusion_families:
        excluded.append(_role_label(role_family))
    for term in context.exclusions:
        terms = [part for part in re.split(r"[/、\s]+", term) if part]
        if any(part.casefold() in title for part in terms):
            excluded.append(term)
    if "高级/资深" in context.exclusions and re.search(
        r"高级|资深|senior|staff|principal|director", title, re.IGNORECASE
    ):
        excluded.append("高级/资深岗位")
    excluded = list(dict.fromkeys(excluded))
    for value in excluded:
        reasons.append(DiscoveryReason(kind="excluded", code="explicit_exclusion", label=value))
    for signal in hard_signals:
        reasons.append(DiscoveryReason(kind="warning", code=signal.type, label=signal.display))
    if not hard_signals:
        unresolved.append("年限要求未明确")
        reasons.append(
            DiscoveryReason(kind="unknown", code="hard_requirements", label="年限要求未明确")
        )

    if role_compatibility in {"mismatch", "unknown_weak"}:
        reasons.append(
            DiscoveryReason(
                kind="warning",
                code="role_family_mismatch",
                label="岗位类型与本次目标方向不一致",
            )
        )
    if function_compatibility == "mismatch":
        reasons.append(
            DiscoveryReason(
                kind="warning",
                code="job_function_mismatch",
                label="岗位职能与本次目标方向不一致",
            )
        )

    if (
        excluded
        or role_compatibility in {"mismatch", "unknown_weak"}
        or function_compatibility == "mismatch"
    ):
        band = "Low"
    elif score >= 6:
        band = "High"
    elif score >= 2:
        band = "Medium"
    else:
        band = "Low"
    if role_compatibility == "adjacent" and band == "High":
        band = "Medium"
    return DiscoverySearchDerived(
        relevance_band=band,
        matched_constraints=matched,
        unresolved_constraints=unresolved,
        excluded_matches=excluded,
        reasons=[item.label for item in reasons],
        reason_items=reasons,
        excluded_by_current_search=bool(excluded),
    )


PRODUCT_FAMILIES = {
    "ai_product",
    "fintech_product",
    "data_product",
    "strategy_product",
    "platform_product",
    "growth_product",
    "general_product",
}
NON_PRODUCT_FAMILIES = {"engineering", "algorithm", "design"}
PRODUCT_TITLE = re.compile(r"产品经理|产品负责人|product\s+(?:manager|owner|lead)", re.IGNORECASE)


def _role_compatibility(requested: list[str], actual: str, title: str) -> str:
    if not requested:
        return "unspecified"
    if actual in requested:
        return "exact"
    requested_product = any(value in PRODUCT_FAMILIES for value in requested)
    requested_non_product = any(value in NON_PRODUCT_FAMILIES for value in requested)
    if requested_product:
        if actual in NON_PRODUCT_FAMILIES or actual in {"product_operations", "solution"}:
            return "mismatch"
        if actual == "unknown":
            return "adjacent" if PRODUCT_TITLE.search(title) else "unknown_weak"
        if actual in PRODUCT_FAMILIES:
            return "adjacent"
    if requested_non_product:
        if actual in PRODUCT_FAMILIES or actual in {"product_operations", "solution"}:
            return "mismatch"
        if actual == "unknown":
            return "unknown_weak"
        if actual in NON_PRODUCT_FAMILIES:
            return "adjacent"
    return "mismatch"


def _role_label(role_family: str) -> str:
    return {
        "ai_product": "AI Product",
        "fintech_product": "FinTech Product",
        "data_product": "Data Product",
        "strategy_product": "Strategy Product",
        "platform_product": "Platform Product",
        "growth_product": "Growth Product",
        "general_product": "Product",
        "product_operations": "Product Operations",
        "solution": "解决方案",
        "engineering": "Engineering",
        "algorithm": "Algorithm",
        "design": "Design",
    }.get(role_family, role_family)


def _job_function_compatibility(
    requested: list[str], title: str, role_family: str
) -> str:
    if not requested:
        return "unspecified"
    actual = {
        name for name, pattern in JOB_FUNCTION_PATTERNS.items() if pattern.search(title)
    }
    if role_family in PRODUCT_FAMILIES:
        actual.add("product_management")
    elif role_family == "engineering":
        actual.add("engineering")
    elif role_family == "algorithm":
        actual.add("algorithm_research")
    elif role_family == "product_operations":
        actual.add("operations")
    elif role_family == "solution":
        actual.add("solution")
    elif role_family == "design":
        actual.add("design")
    if not actual:
        return "unknown"
    return "exact" if set(requested) & actual else "mismatch"


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(
        bool(re.search(r"\bai\b", text, re.IGNORECASE))
        if term.casefold() == "ai"
        else term.casefold() in text
        for term in terms
    )


def _function_label(value: str) -> str:
    return {
        "ai": "AI",
        "product_management": "产品",
        "investment": "投资",
        "data_analytics": "数据分析",
        "strategy_consulting": "战略咨询",
        "algorithm_research": "算法 / 研究",
        "engineering": "工程",
        "marketing": "市场营销",
        "risk_management": "风险管理",
        "operations": "运营",
        "solution": "解决方案",
        "design": "设计",
    }.get(value, value)


def _concept_label(value: str) -> str:
    return {
        "banking": "银行",
        "financial_services": "金融",
        "ecommerce": "电商",
        "consumer_goods": "消费品",
        "ai_agent": "AI Agent",
        "llm": "大模型",
        "ai_platform": "AI 平台",
        "multimodal": "多模态",
        "aigc": "AIGC",
        "risk_control": "风控",
        "primary_market": "一级市场",
        "technology": "科技",
    }.get(value, value)
