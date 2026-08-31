import { FormEvent, useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { jobsApi, workspaceApi } from "./api";
import FitAnalysisPanel from "./FitAnalysisPanel";
import ResumeTailoringPanel from "./ResumeTailoringPanel";
import { APPLICATION_STATUS_LABELS } from "./analysis-utils";
import { formatFullDate, JOB_STATUSES } from "./job-utils";
import type { ApplicationStatusDefinition, Job } from "./types";

type DetailTab = "overview" | "analysis" | "resume";

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
  const { id } = useParams();
  const [searchParams] = useSearchParams();
  const jobId = Number(id);
  const requestedTab = searchParams.get("tab");
  const [job, setJob] = useState<Job | null>(null);
  const [tab, setTab] = useState<DetailTab>(requestedTab === "resume" || requestedTab === "analysis" ? requestedTab : "overview");
  const [applicationDate, setApplicationDate] = useState("");
  const [nextStage, setNextStage] = useState("");
  const [interviewDate, setInterviewDate] = useState("");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [statuses, setStatuses] = useState<ApplicationStatusDefinition[]>([]);

  function applyJob(value: Job) {
    setJob(value); setApplicationDate(value.application_date || ""); setNextStage(value.next_stage || ""); setInterviewDate(value.interview_date || ""); setNotes(value.notes || "");
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
    try { applyJob(await jobsApi.update(job.id, { application_date: applicationDate || null, next_stage: nextStage.trim() || null, interview_date: interviewDate || null, notes: notes.trim() || null })); setNotice("投递信息已保存。"); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "投递信息保存失败。"); }
    finally { setSaving(false); }
  }

  if (!Number.isInteger(jobId)) return <main className="workspace-shell detail-state"><div className="error">岗位地址无效。</div><Link to="/my-jobs">返回我的岗位</Link></main>;
  if (error && !job) return <main className="workspace-shell detail-state"><div className="error">{error}</div><Link to="/my-jobs">返回我的岗位</Link></main>;
  if (!job) return <main className="workspace-shell page-loading"><span className="spinner dark" />正在加载岗位详情…</main>;
  const structured = job.structured_jd;

  return <main className="workspace-shell job-detail-page">
    <Link className="back-link" to="/my-jobs">← 返回我的岗位</Link>
    <header className="job-detail-header">
      <div><span className="eyebrow">{job.company}</span><h1>{job.role}</h1><p>{[job.location, job.recruitment_type, `${formatFullDate(job.created_at)} 加入`].filter(Boolean).join(" · ")}</p></div>
      <div className="detail-header-actions">{job.match_score !== null && <div className="match-number compact"><strong>{job.match_score}%</strong><span>Match Score</span></div>}<label className="detail-status">投递状态<select value={job.application_status_id ?? ""} disabled={saving} onChange={(event) => void updateStatus(Number(event.target.value))}>{statuses.length ? statuses.map((status) => <option key={status.id} value={status.id}>{status.label}</option>) : JOB_STATUSES.map((status) => <option key={status} value="">{APPLICATION_STATUS_LABELS[status]}</option>)}</select></label></div>
    </header>
    {error && <div className="error" role="alert">{error}</div>}{notice && <div className="notice">{notice}</div>}
    <div className="detail-tabs"><button className={tab === "overview" ? "active" : ""} onClick={() => setTab("overview")}><span>01</span> 岗位要求</button><button className={tab === "analysis" ? "active" : ""} onClick={() => setTab("analysis")}><span>02</span> 匹配分析</button><button className={tab === "resume" ? "active" : ""} onClick={() => setTab("resume")}><span>03</span> 简历优化</button></div>

    {tab === "overview" && <div className="detail-layout"><div className="detail-main">
      <section className="quick-overview"><span className="card-kicker">岗位概览</span><div className="one-line-summary"><span>这个岗位主要做什么</span><h2>{structured.role_summary || "该岗位暂未生成简要概述。"}</h2></div><RequirementOverview structured={structured} /></section>
      <section className="detail-section"><h2>岗位职责</h2><TextList items={structured.responsibilities} /></section><section className="detail-section"><h2>核心要求</h2><TextList items={structured.required_skills} /></section><section className="detail-section"><h2>加分项</h2><TextList items={structured.preferred_skills} /></section><section className="detail-section original-jd"><details><summary>查看原始 JD</summary><pre>{job.original_jd}</pre></details>{job.source_url && <a href={job.source_url} target="_blank" rel="noreferrer">打开原岗位链接 ↗</a>}</section>
    </div><aside className="application-panel"><h2>投递记录</h2><p>记录申请进度、下一步和面试安排。</p><form onSubmit={saveApplication}><label>投递日期<input type="date" value={applicationDate} onChange={(event) => setApplicationDate(event.target.value)} /></label><label>下一阶段<input value={nextStage} onChange={(event) => setNextStage(event.target.value)} placeholder="例如：等待在线测评" maxLength={255} /></label><label>面试日期<input type="date" value={interviewDate} onChange={(event) => setInterviewDate(event.target.value)} /></label><label>备注<textarea rows={7} value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="记录联系人、截止时间或跟进事项…" maxLength={10000} /></label><button className="primary-link button-link" type="submit" disabled={saving}>{saving ? "正在保存…" : "保存投递信息"}</button></form></aside></div>}
    {tab === "analysis" && <FitAnalysisPanel jobId={job.id} />}
    {tab === "resume" && <ResumeTailoringPanel jobId={job.id} onGoAnalysis={() => setTab("analysis")} />}
  </main>;
}
