import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";

import { jobsApi, workspaceApi } from "./api";
import FitAnalysisPanel from "./FitAnalysisPanel";
import JobNotesDrawer from "./JobNotesDrawer";
import ResumeTailoringPanel from "./ResumeTailoringPanel";
import { APPLICATION_STATUS_LABELS } from "./analysis-utils";
import { formatFullDate, JOB_STATUSES } from "./job-utils";
import type { ApplicationStatusDefinition, Job } from "./types";

type DetailTab = "overview" | "analysis" | "resume";

export function JobIdentityForm({ role, company, location, saving, onRoleChange, onCompanyChange, onLocationChange, onCancel, onSubmit }: {
  role: string;
  company: string;
  location: string;
  saving: boolean;
  onRoleChange: (value: string) => void;
  onCompanyChange: (value: string) => void;
  onLocationChange: (value: string) => void;
  onCancel: () => void;
  onSubmit: (event: FormEvent) => void;
}) {
  return <section className="job-identity-editor" aria-labelledby="job-identity-editor-title">
    <div><span className="card-kicker">岗位信息</span><h2 id="job-identity-editor-title">编辑岗位基本信息</h2><p>这些信息只更新 JobPilot 内的岗位记录。</p></div>
    <form onSubmit={onSubmit}>
      <label>岗位名称<input value={role} onChange={(event) => onRoleChange(event.target.value)} required maxLength={255} /></label>
      <label>公司<input value={company} onChange={(event) => onCompanyChange(event.target.value)} required maxLength={255} /></label>
      <label>地点<input value={location} onChange={(event) => onLocationChange(event.target.value)} maxLength={255} placeholder="未注明可留空" /></label>
      <div className="job-identity-actions"><button className="secondary-button" type="button" onClick={onCancel} disabled={saving}>取消</button><button className="primary-button" type="submit" disabled={saving || !role.trim() || !company.trim()}>{saving ? "正在保存…" : "保存岗位信息"}</button></div>
    </form>
  </section>;
}

export function JobDangerZone({ jobLabel, deleting, onDelete }: { jobLabel: string; deleting: boolean; onDelete: () => void }) {
  return <section className="job-danger-zone" aria-labelledby="job-danger-zone-title">
    <div><span className="card-kicker">Danger Zone</span><h2 id="job-danger-zone-title">删除岗位</h2><p>删除 JobPilot 内的“{jobLabel}”及相关备注；此操作仅影响 JobPilot 内的数据。</p></div>
    <button className="danger-button" type="button" disabled={deleting} onClick={onDelete}>{deleting ? "正在删除…" : "删除岗位"}</button>
  </section>;
}

function TextList({ items, empty = "该 JD 中未明确说明。" }: { items: string[]; empty?: string }) {
  return items.length ? <ul className="detail-list">{items.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ul> : <p className="muted">{empty}</p>;
}

function RequirementOverview({ structured }: { structured: Job["structured_jd"] }) {
  if (structured.requirement_taxonomy_version !== "v2") {
    return <div className="quick-columns"><div><h3>关键要求</h3>{structured.key_requirements.length ? <ol>{structured.key_requirements.map((item, index) => <li key={`${item.title}-${index}`}><span className={`priority priority-${item.priority}`}>{index + 1}</span><div><strong>{item.title}</strong><p>{item.explanation}</p></div></li>)}</ol> : <p className="muted">该 JD 中未提取到明确重点要求。</p>}</div><div><h3>相关知识与领域</h3><div className="topic-tags">{structured.knowledge_topics.map((topic) => <span key={topic}>{topic}</span>)}{!structured.knowledge_topics.length && <p className="muted">该 JD 中未提取到明确知识主题。</p>}</div></div></div>;
  }
  const groups = [
    { type: "eligibility", title: "岗位资格", note: "单独核验，不计入 Match Score" },
    { type: "matchable", title: "履历匹配要求", note: "由已验证职业证据评估" },
    { type: "knowledge", title: "岗位知识要求", note: "作为面试准备主题" },
  ] as const;
  return <div className="quick-columns taxonomy-quick-columns">{groups.map((group) => {
    const items = structured.requirements.filter((item) => item.requirement_type === group.type);
    if (!items.length) return null;
    return <div key={group.type}><h3>{group.title}</h3><p className="taxonomy-group-note">{group.note}</p><ul className="detail-list">{items.map((item) => <li key={item.requirement_id}>{item.normalized_requirement}</li>)}</ul></div>;
  })}</div>;
}

export default function JobDetailPage() {
  const navigate = useNavigate();
  const { id } = useParams();
  const [searchParams] = useSearchParams();
  const jobId = Number(id);
  const requestedTab = searchParams.get("tab");
  const [job, setJob] = useState<Job | null>(null);
  const [tab, setTab] = useState<DetailTab>(requestedTab === "resume" || requestedTab === "analysis" ? requestedTab : "overview");
  const [applicationDate, setApplicationDate] = useState("");
  const [nextStage, setNextStage] = useState("");
  const [interviewDate, setInterviewDate] = useState("");
  const [deadlineAt, setDeadlineAt] = useState("");
  const [identityRole, setIdentityRole] = useState("");
  const [identityCompany, setIdentityCompany] = useState("");
  const [identityLocation, setIdentityLocation] = useState("");
  const [identityEditing, setIdentityEditing] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [notesOpen, setNotesOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [statuses, setStatuses] = useState<ApplicationStatusDefinition[]>([]);

  function applyJob(value: Job) {
    setJob(value); setApplicationDate(value.application_date || ""); setNextStage(value.next_stage || ""); setInterviewDate(value.interview_date || ""); setDeadlineAt(value.deadline_at ? value.deadline_at.slice(0, 16) : ""); setIdentityRole(value.role); setIdentityCompany(value.company); setIdentityLocation(value.location || "");
  }
  useEffect(() => { if (Number.isInteger(jobId)) jobsApi.get(jobId).then(applyJob).catch((cause: Error) => setError(cause.message)); }, [jobId]);
  useEffect(() => { workspaceApi.statuses().then(setStatuses).catch(() => undefined); }, []);

  async function updateStatus(statusId: number) {
    if (!job) return;
    setSaving(true); setError(""); setNotice("");
    try { applyJob(await jobsApi.update(job.id, { application_status_id: statusId })); setNotice("岗位状态已更新。"); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "状态更新失败。"); }
    finally { setSaving(false); }
  }
  async function saveApplication(event: FormEvent) {
    event.preventDefault(); if (!job) return;
    setSaving(true); setError(""); setNotice("");
    try { applyJob(await jobsApi.update(job.id, { application_date: applicationDate || null, next_stage: nextStage.trim() || null, deadline_at: deadlineAt || null, interview_date: interviewDate || null })); setNotice("投递信息已保存。"); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "投递信息保存失败。"); }
    finally { setSaving(false); }
  }
  async function saveIdentity(event: FormEvent) {
    event.preventDefault(); if (!job || !identityRole.trim() || !identityCompany.trim()) return;
    setSaving(true); setError(""); setNotice("");
    try { applyJob(await jobsApi.update(job.id, { role: identityRole.trim(), company: identityCompany.trim(), location: identityLocation.trim() || null })); setIdentityEditing(false); setNotice("岗位信息已保存。"); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "岗位信息保存失败。"); }
    finally { setSaving(false); }
  }
  function cancelIdentityEdit() {
    if (!job) return;
    setIdentityRole(job.role); setIdentityCompany(job.company); setIdentityLocation(job.location || ""); setIdentityEditing(false);
  }
  async function deleteJob() {
    if (!job) return;
    const confirmed = window.confirm(`确认删除“${job.role}”？\n\n这会删除 JobPilot 内的岗位及相关备注，且无法撤销。`);
    if (!confirmed) return;
    setDeleting(true); setError(""); setNotice("");
    try { await jobsApi.delete(job.id); navigate("/my-jobs", { replace: true }); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "岗位删除失败。"); setDeleting(false); }
  }

  if (!Number.isInteger(jobId)) return <main className="workspace-shell detail-state"><div className="error">岗位地址无效。</div><Link to="/my-jobs">返回我的岗位</Link></main>;
  if (error && !job) return <main className="workspace-shell detail-state"><div className="error">{error}</div><Link to="/my-jobs">返回我的岗位</Link></main>;
  if (!job) return <main className="workspace-shell page-loading"><span className="spinner dark" />正在加载岗位详情…</main>;
  const structured = job.structured_jd;

  return <main className="workspace-shell job-detail-page">
    <Link className="back-link" to="/my-jobs">← 返回我的岗位</Link>
    <header className="job-detail-header">
      <div><span className="eyebrow">{job.company}</span><h1>{job.role}</h1><p>{[job.location, job.recruitment_type, `${formatFullDate(job.created_at)} 加入`].filter(Boolean).join(" · ")}</p></div>
      <div className="detail-header-actions">{job.match_score !== null && <div className="match-number compact"><strong>{job.match_score}%</strong><span>Match Score</span></div>}<button className="secondary-button" type="button" onClick={() => setIdentityEditing(true)}>编辑岗位信息</button></div>
    </header>
    {error && <div className="error" role="alert">{error}</div>}{notice && <div className="notice">{notice}</div>}
    {identityEditing && <JobIdentityForm role={identityRole} company={identityCompany} location={identityLocation} saving={saving} onRoleChange={setIdentityRole} onCompanyChange={setIdentityCompany} onLocationChange={setIdentityLocation} onCancel={cancelIdentityEdit} onSubmit={saveIdentity} />}
    <div className="detail-tabs"><button className={tab === "overview" ? "active" : ""} onClick={() => setTab("overview")}><span>01</span> 岗位要求</button><button className={tab === "analysis" ? "active" : ""} onClick={() => setTab("analysis")}><span>02</span> 匹配分析</button><button className={tab === "resume" ? "active" : ""} onClick={() => setTab("resume")}><span>03</span> 简历优化</button></div>

    {tab === "overview" && <div className="detail-layout"><div className="detail-main">
      <section className="quick-overview"><span className="card-kicker">岗位概览</span><div className="one-line-summary"><span>这个岗位主要做什么</span><h2>{structured.role_summary || "该岗位暂未生成简要概述。"}</h2></div><RequirementOverview structured={structured} /></section>
      <section className="detail-section"><h2>岗位职责</h2><TextList items={structured.responsibilities} /></section><section className="detail-section"><h2>核心要求</h2><TextList items={structured.required_skills} /></section><section className="detail-section"><h2>加分项</h2><TextList items={structured.preferred_skills} /></section><section className="detail-section original-jd"><details><summary>查看原始 JD</summary><pre>{job.original_jd}</pre></details>{job.source_url && <a href={job.source_url} target="_blank" rel="noreferrer">打开原岗位链接 ↗</a>}</section>
    </div><aside className="application-panel"><h2>投递记录</h2><p>结构化记录当前阶段、关键日期与下一步。</p><form onSubmit={saveApplication}><label>当前状态<select value={job.application_status_id ?? ""} disabled={saving} onChange={(event) => void updateStatus(Number(event.target.value))}>{statuses.length ? statuses.map((status) => <option key={status.id} value={status.id}>{status.label}</option>) : JOB_STATUSES.map((status) => <option key={status} value="">{APPLICATION_STATUS_LABELS[status]}</option>)}</select></label><label>投递日期<input type="date" value={applicationDate} onChange={(event) => setApplicationDate(event.target.value)} /></label><label>下一阶段<input value={nextStage} onChange={(event) => setNextStage(event.target.value)} placeholder="例如：等待在线测评" maxLength={255} /></label><label>Deadline<input type="datetime-local" value={deadlineAt} onChange={(event) => setDeadlineAt(event.target.value)} /></label><label>面试日期<input type="date" value={interviewDate} onChange={(event) => setInterviewDate(event.target.value)} /></label><button className="primary-link button-link" type="submit" disabled={saving}>{saving ? "正在保存…" : "保存投递信息"}</button></form><div className="application-notes-entry"><div><strong>备注</strong><p>记录 HR 沟通、下一步与重要上下文。</p></div><button className="secondary-button" type="button" onClick={() => setNotesOpen(true)}>查看全部备注</button></div></aside></div>}
    {tab === "analysis" && <FitAnalysisPanel jobId={job.id} />}
    {tab === "resume" && <ResumeTailoringPanel jobId={job.id} onGoAnalysis={() => setTab("analysis")} />}
    <JobDangerZone jobLabel={`${job.company} · ${job.role}`} deleting={deleting} onDelete={() => void deleteJob()} />
    {notesOpen && <JobNotesDrawer jobId={job.id} jobLabel={`${job.company} · ${job.role}`} onClose={() => setNotesOpen(false)} />}
  </main>;
}
