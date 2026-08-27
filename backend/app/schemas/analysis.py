from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class Education(BaseModel):
    institution: str
    degree: str | None = None
    field: str | None = None
    period: str | None = None


class WorkExperience(BaseModel):
    company: str
    title: str
    period: str | None = None
    highlights: list[str] = Field(default_factory=list)


class Project(BaseModel):
    name: str
    description: str
    skills: list[str] = Field(default_factory=list)


class ResumeProfile(BaseModel):
    education: list[Education] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    work_experience: list[WorkExperience] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    ai_experience: list[str] = Field(default_factory=list)
    product_experience: list[str] = Field(default_factory=list)
    technical_experience: list[str] = Field(default_factory=list)
    domain_experience: list[str] = Field(default_factory=list)


class KeyRequirement(BaseModel):
    title: str
    explanation: str
    category: str | None = None
    priority: Literal["high", "medium", "low"] = "medium"


class JDRequirements(BaseModel):
    role: str | None = None
    company: str | None = None
    location: str | None = None
    recruitment_type: str | None = None
    published_date: date | None = None
    role_summary: str | None = None
    key_requirements: list[KeyRequirement] = Field(default_factory=list)
    knowledge_topics: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    ai_requirements: list[str] = Field(default_factory=list)
    product_requirements: list[str] = Field(default_factory=list)
    technical_requirements: list[str] = Field(default_factory=list)
    domain_requirements: list[str] = Field(default_factory=list)


class JDKeyRequirementOutput(BaseModel):
    """Low-complexity wire schema used only for Claude structured output."""

    title: str
    explanation: str
    category: str
    priority: Literal["high", "medium", "low"]


class JDRequirementsOutput(BaseModel):
    """All fields are required to avoid nullable/default grammar branches."""

    role: str
    company: str
    location: str
    recruitment_type: str
    published_date: str
    role_summary: str
    key_requirements: list[JDKeyRequirementOutput]
    knowledge_topics: list[str]
    responsibilities: list[str]
    required_skills: list[str]
    preferred_skills: list[str]
    ai_requirements: list[str]
    product_requirements: list[str]
    technical_requirements: list[str]
    domain_requirements: list[str]


class EvidenceItem(BaseModel):
    requirement: str
    resume_evidence: str
    assessment: Literal["strong", "partial", "missing"]


class MatchAnalysis(BaseModel):
    match_score: int = Field(ge=0, le=100)
    recommendation: Literal["Strong Apply", "Apply", "Stretch", "Skip"]
    top_strengths: list[str] = Field(default_factory=list)
    key_gaps: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    suggested_preparation: list[str] = Field(default_factory=list)


class AnalysisResponse(BaseModel):
    resume_profile: ResumeProfile
    jd_requirements: JDRequirements
    match_analysis: MatchAnalysis
