import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { fitAnalysisApi, jobsApi } from "./api";
import {
  REQUIREMENT_IMPORTANCE_LABELS,
  REQUIREMENT_MATCH_LABELS,
} from "./analysis-utils";
import type { FitAnalysisPreview, JobPreview, RequirementImportance } from "./types";

const IMPORTANCE_ORDER: RequirementImportance[] = ["Critical", "Important", "Preferred"];

function isUrl(value: string) {
  return /^https?:\/\//i.test(value.trim());
}

function RequirementGroups({ analysis }: { analysis: FitAnalysisPreview }) {
  return <div className="requirement-groups">{IMPORTANCE_ORDER.map((importance) => {
    const items = analysis.requirement_matches.filter((item) => item.importance === importance);
    if (!items.length) return null;
    return <section key={importance}>
      <h3>{REQUIREMENT_IMPORTANCE_LABELS[importance]}</h3>
      <ul>{items.map((item) => <li key={item.requirement_id}>{item.requirement_text}{item.is_hard_requirement && <span className="hard-badge">硬性要求</span>}</li>)}</ul>
    </section>;
  })}</div>;
}

function AnalysisResults({
  preview,
  analysis,
  onReset,
}: {
  preview: JobPreview;
  analysis: FitAnalysisPreview;
  onReset: () => void;
}) {
  const navigate = useNavigate();
  const [adding, setAdding] = useState(false);
  const [persistedId, setPersistedId] = useState<number | null>(null);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  async function addToMyJobs() {
    if (!preview.company || !preview.role) {
      setError("未能确认公司或岗位名称，请先使用手动添加岗位补充信息。");
      return;
    }
    setAdding(true); setError(""); setNotice("");
    try {
      const job = await jobsApi.create({ ...preview, company: preview.company, role: preview.role, preview_artifact_token: analysis.artifact_token || undefined });
      setPersistedId(job.id);
      try {
        if (job.analysis_promoted) {
          setNotice("已加入我的岗位，并复用本次匹配分析。");
          return;
        }
        await fitAnalysisApi.run(job.id);
        setNotice("已加入我的岗位，并保存本次匹配分析。");
      } catch {
        setNotice("已加入我的岗位；匹配分析暂未保存，可在岗位详情中重新分析。");
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "加入我的岗位失败。");
    } finally { setAdding(false); }
  }

  return <main className="workspace-shell analyze-result-page">
    <Link className="back-link" to="/analyze" onClick={(event) => { event.preventDefault(); onReset(); }}>← 分析其他岗位</Link>
    <header className="analysis-result-header">
      <div><span className="eyebrow">{preview.company || "公司待确认"}</span><h1>{preview.role || "岗位名称待确认"}</h1><p>{[preview.location, preview.recruitment_type].filter(Boolean).join(" · ") || "地点与招聘类型未注明"}</p></div>
      <div className="analysis-result-actions">
        <div className="match-number"><strong>{analysis.match_score}%</strong><span>Match Score</span></div>
        {persistedId
          ? <button className="primary-link button-link" onClick={() => navigate(`/jobs/${persistedId}`)}>已加入 · 查看岗位</button>
          : <button className="primary-link button-link" disabled={adding} onClick={() => void addToMyJobs()}>{adding ? "正在加入…" : "加入我的岗位"}</button>}
      </div>
    </header>
    {notice && <div className="notice" role="status">{notice}</div>}
    {error && <div className="error" role="alert">{error}</div>}

    <nav className="analysis-mini-nav"><a href="#requirements">01 岗位要求</a><a href="#match">02 匹配分析</a><a href="#resume">03 简历优化</a></nav>

    <section id="requirements" className="analysis-module">
      <div className="module-number">01</div><div className="module-heading"><span>Job Understanding</span><h2>岗位要求</h2><p>{preview.structured_jd.role_summary || "已将完整 JD 整理为可快速阅读的岗位要求。"}</p></div>
      <RequirementGroups analysis={analysis} />
    </section>

    <section id="match" className="analysis-module">
      <div className="module-number">02</div><div className="module-heading"><span>Evidence-grounded Match</span><h2>匹配分析</h2><p>{analysis.summary}</p></div>
      <div className="requirement-match-list">{analysis.requirement_matches.map((item) => <article key={item.requirement_id} className={`requirement-match match-${item.match_status.toLowerCase()}`}>
        <div><span className="match-icon" aria-hidden="true">{item.match_status === "Strong" ? "✓" : item.match_status === "Partial" ? "◐" : "○"}</span><div><h3>{item.requirement_text}</h3><span className={`assessment ${item.match_status.toLowerCase()}`}>{REQUIREMENT_MATCH_LABELS[item.match_status]}</span></div></div>
        <p>{item.reason}</p>
        {item.evidence_sources.length > 0 && <details><summary>查看支持证据</summary><ul>{item.evidence_sources.map((source) => <li key={`${source.source_type}-${source.source_id}`}><strong>{source.context}</strong><span>{source.text}</span></li>)}</ul></details>}
      </article>)}</div>
    </section>

    <section id="resume" className="analysis-module resume-guidance">
      <div className="module-number">03</div><div className="module-heading"><span>Resume Optimization</span><h2>简历优化</h2><p>针对这个岗位，你的简历最值得优先调整这些内容。所有具体改写仍会经过证据校验。</p></div>
      {analysis.suggested_preparation.length ? <ol>{analysis.suggested_preparation.map((item, index) => <li key={`${item.title}-${index}`}><span>{String(index + 1).padStart(2, "0")}</span><div><h3>{item.title}</h3><p>{item.action}</p></div></li>)}</ol> : <p className="muted">当前没有额外的简历优化重点。</p>}
      <div className="resume-next-step">{persistedId ? <button className="secondary-button" onClick={() => navigate(`/jobs/${persistedId}?tab=resume`)}>查看具体修改建议</button> : <><p>加入我的岗位后，可生成逐条、可追溯的简历修改建议。</p><button className="secondary-button" disabled={adding} onClick={() => void addToMyJobs()}>加入后继续优化</button></>}</div>
    </section>
  </main>;
}

export default function AnalyzeJobPage() {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [stage, setStage] = useState("");
  const [error, setError] = useState("");
  const [preview, setPreview] = useState<JobPreview | null>(null);
  const [analysis, setAnalysis] = useState<FitAnalysisPreview | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const value = input.trim();
    if (!isUrl(value) && value.length < 50) {
      setError("请粘贴更完整的岗位描述（至少 50 个字符），或输入岗位链接。");
      return;
    }
    setLoading(true); setError(""); setStage(isUrl(value) ? "正在读取岗位链接…" : "正在整理岗位要求…");
    try {
      const parsed = isUrl(value) ? await jobsApi.previewUrl(value) : await jobsApi.previewJd(value);
      setPreview(parsed); setStage("正在匹配你的真实经历…");
      setAnalysis(await jobsApi.analyzePreview(parsed.structured_jd));
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "岗位分析失败，请稍后重试。");
    } finally { setLoading(false); setStage(""); }
  }

  if (preview && analysis) return <AnalysisResults preview={preview} analysis={analysis} onReset={() => { setPreview(null); setAnalysis(null); setInput(""); }} />;

  return <main className="analyze-home">
    <section className="analyze-hero">
      <span className="hero-sparkle" aria-hidden="true">✦</span>
      <span className="eyebrow">Evidence-grounded job analysis</span>
      <h1>分析一个岗位</h1>
      <p>粘贴岗位链接或 JD，快速看懂岗位要求、匹配程度和简历优化方向。</p>
      <form className="analyze-input-card" onSubmit={submit}>
        <label htmlFor="job-input">岗位链接或完整 JD</label>
        <textarea id="job-input" rows={8} value={input} onChange={(event) => setInput(event.target.value)} placeholder="粘贴岗位链接或完整 JD" maxLength={100000} />
        {error && <div className="error" role="alert">{error}{isUrl(input) && <span> 当前无法自动读取时，你仍可以直接粘贴完整 JD。</span>}</div>}
        <div className="analyze-input-footer"><span>{isUrl(input) ? "将尝试安全读取公开岗位页面" : input ? `${input.length.toLocaleString()} 字` : "支持来自官网、招聘群或朋友转发的 JD"}</span><button className="submit-button" type="submit" disabled={loading}>{loading ? <><span className="spinner" />{stage}</> : "开始分析 →"}</button></div>
      </form>
      <Link className="manual-add-link" to="/jobs/new">也可以手动填写岗位信息</Link>
    </section>
    <section className="analyze-steps" aria-label="分析步骤"><div><span>01</span><strong>看懂岗位要求</strong></div><div><span>02</span><strong>查看你的匹配度</strong></div><div><span>03</span><strong>优化你的简历</strong></div></section>
  </main>;
}
