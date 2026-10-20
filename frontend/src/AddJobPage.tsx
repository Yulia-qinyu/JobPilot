import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { ApiError, jobsApi, workspaceApi } from "./api";
import type { ApplicationStatusDefinition, JobPreview } from "./types";

type Mode = "quick" | "url" | "jd";

function splitLines(value: string): string[] {
  return value.split("\n").map((item) => item.trim().replace(/^[-•]\s*/, "")).filter(Boolean);
}

export default function AddJobPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<Mode>("quick");
  const [url, setUrl] = useState("");
  const [jd, setJd] = useState("");
  const [preview, setPreview] = useState<JobPreview | null>(null);
  const [company, setCompany] = useState("");
  const [role, setRole] = useState("");
  const [location, setLocation] = useState("");
  const [recruitmentType, setRecruitmentType] = useState("");
  const [publishedDate, setPublishedDate] = useState("");
  const [responsibilities, setResponsibilities] = useState("");
  const [requiredSkills, setRequiredSkills] = useState("");
  const [preferredSkills, setPreferredSkills] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showPasteFallback, setShowPasteFallback] = useState(false);
  const [quickCompany, setQuickCompany] = useState("");
  const [quickRole, setQuickRole] = useState("");
  const [quickLocation, setQuickLocation] = useState("");
  const [quickApplicationDate, setQuickApplicationDate] = useState("");
  const [quickStatusId, setQuickStatusId] = useState("");
  const [statuses, setStatuses] = useState<ApplicationStatusDefinition[]>([]);

  useEffect(() => {
    workspaceApi.statuses().then((items) => {
      setStatuses(items);
      setQuickStatusId(String(items.find((item) => item.key === "interested")?.id || ""));
    }).catch((cause: Error) => setError(cause.message));
  }, []);

  function applyPreview(value: JobPreview) {
    setPreview(value);
    setCompany(value.company || "");
    setRole(value.role || "");
    setLocation(value.location || "");
    setRecruitmentType(value.recruitment_type || "");
    setPublishedDate(value.published_date || "");
    setResponsibilities(value.structured_jd.responsibilities.join("\n"));
    setRequiredSkills(value.structured_jd.required_skills.join("\n"));
    setPreferredSkills(value.structured_jd.preferred_skills.join("\n"));
  }

  async function parse(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setShowPasteFallback(false);
    try {
      applyPreview(mode === "url" ? await jobsApi.previewUrl(url) : await jobsApi.previewJd(jd));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "岗位解析失败，请稍后重试。");
      setShowPasteFallback(mode === "url" && cause instanceof ApiError && cause.code === "JOB_URL_UNREADABLE");
    } finally {
      setLoading(false);
    }
  }

  async function saveQuick(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      await jobsApi.quickCreate({
        company: quickCompany.trim(),
        role: quickRole.trim(),
        location: quickLocation.trim() || null,
        application_date: quickApplicationDate || null,
        application_status_id: quickStatusId ? Number(quickStatusId) : null,
      });
      navigate("/my-jobs");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "岗位添加失败，请稍后重试。");
    } finally {
      setLoading(false);
    }
  }

  function selectMode(value: Mode) {
    setMode(value);
    setError("");
    setShowPasteFallback(false);
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    if (!preview) return;
    setLoading(true);
    setError("");
    try {
      const job = await jobsApi.create({
        ...preview,
        company: company.trim(),
        role: role.trim(),
        location: location.trim() || null,
        recruitment_type: recruitmentType.trim() || null,
        published_date: publishedDate || null,
        structured_jd: {
          ...preview.structured_jd,
          company: company.trim(),
          role: role.trim(),
          location: location.trim() || null,
          recruitment_type: recruitmentType.trim() || null,
          published_date: publishedDate || null,
          responsibilities: splitLines(responsibilities),
          required_skills: splitLines(requiredSkills),
          preferred_skills: splitLines(preferredSkills),
        },
      });
      navigate(`/jobs/${job.id}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "岗位保存失败，请稍后重试。");
    } finally {
      setLoading(false);
    }
  }

  if (preview) {
    return (
      <main className="workspace-shell add-job-page">
        <header className="workspace-heading compact"><div><span className="eyebrow">确认岗位信息</span><h1>解析结果是否准确？</h1><p>保存前可以修正关键字段。确认后会加入我的岗位。</p></div></header>
        {error && <div className="error" role="alert">{error}</div>}
        <form className="confirmation-form" onSubmit={save}>
          <div className="confirmation-grid">
            <label>公司<input value={company} onChange={(event) => setCompany(event.target.value)} required maxLength={255} /></label>
            <label>岗位<input value={role} onChange={(event) => setRole(event.target.value)} required maxLength={255} /></label>
            <label>城市<input value={location} onChange={(event) => setLocation(event.target.value)} maxLength={255} /></label>
            <label>招聘类型<input value={recruitmentType} onChange={(event) => setRecruitmentType(event.target.value)} placeholder="例如：校园招聘" maxLength={120} /></label>
            <label>发布时间<input type="date" value={publishedDate} onChange={(event) => setPublishedDate(event.target.value)} /></label>
          </div>

          <section className="quick-preview confirmation-quick">
            <span className="card-kicker">JD 速览</span>
            <h2>{preview.structured_jd.role_summary || "暂未提取岗位概述"}</h2>
            <div className="quick-columns">
              <div><h3>重点要求</h3>{preview.structured_jd.key_requirements.length ? <ol>{preview.structured_jd.key_requirements.map((item) => <li key={`${item.title}-${item.explanation}`}><strong>{item.title}</strong><span>{item.explanation}</span></li>)}</ol> : <p className="muted">暂未提取</p>}</div>
              <div><h3>建议掌握</h3><div className="topic-tags">{preview.structured_jd.knowledge_topics.map((topic) => <span key={topic}>{topic}</span>)}{!preview.structured_jd.knowledge_topics.length && <p className="muted">暂未提取</p>}</div></div>
            </div>
          </section>

          <div className="confirmation-textareas">
            <label>岗位职责（每行一项）<textarea rows={8} value={responsibilities} onChange={(event) => setResponsibilities(event.target.value)} /></label>
            <label>必选要求（每行一项）<textarea rows={8} value={requiredSkills} onChange={(event) => setRequiredSkills(event.target.value)} /></label>
            <label>加分项（每行一项）<textarea rows={6} value={preferredSkills} onChange={(event) => setPreferredSkills(event.target.value)} /></label>
          </div>
          <div className="form-actions"><button type="button" className="secondary-button" onClick={() => navigate("/my-jobs")}>取消</button><button className="primary-link button-link" type="submit" disabled={loading || !company.trim() || !role.trim()}>{loading ? "正在保存…" : "确认并加入我的岗位"}</button></div>
        </form>
      </main>
    );
  }

  return (
    <main className="workspace-shell add-job-page">
      <header className="workspace-heading compact"><div><span className="eyebrow">Add Job</span><h1>添加岗位</h1><p>快速记录一个机会，或通过岗位链接和完整 JD 获取分析信息。</p></div></header>
      <section className="add-job-card">
        <div className="mode-tabs"><button type="button" className={mode === "quick" ? "active" : ""} onClick={() => selectMode("quick")}>快速添加</button><button type="button" className={mode === "url" ? "active" : ""} onClick={() => selectMode("url")}>岗位链接</button><button type="button" className={mode === "jd" ? "active" : ""} onClick={() => selectMode("jd")}>粘贴 JD</button></div>
        {mode === "quick" ? <form onSubmit={saveQuick}>
          <div className="quick-add-grid">
            <label>岗位名称 *<input value={quickRole} onChange={(event) => setQuickRole(event.target.value)} maxLength={255} required /></label>
            <label>公司名称 *<input value={quickCompany} onChange={(event) => setQuickCompany(event.target.value)} maxLength={255} required /></label>
            <label>地点<input value={quickLocation} onChange={(event) => setQuickLocation(event.target.value)} maxLength={255} placeholder="可选" /></label>
            <label>投递日期<input type="date" value={quickApplicationDate} onChange={(event) => setQuickApplicationDate(event.target.value)} /></label>
            <label>当前状态<select value={quickStatusId} onChange={(event) => setQuickStatusId(event.target.value)}>{!quickStatusId && <option value="">感兴趣</option>}{statuses.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label>
          </div>
          <p className="quick-add-note">只加入“我的岗位”，不会解析 JD 或自动运行匹配分析。</p>
          {error && <div className="error" role="alert">{error}</div>}
          <div className="form-actions"><button type="button" className="secondary-button" onClick={() => navigate("/my-jobs")}>取消</button><button className="primary-link button-link" type="submit" disabled={loading || !quickCompany.trim() || !quickRole.trim()}>{loading ? "正在添加…" : "添加岗位"}</button></div>
        </form> : <form onSubmit={parse}>
          {mode === "url" ? <label>公开岗位链接<input type="url" value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://talent.example.com/job/..." required /></label> : <label>完整职位描述<textarea value={jd} onChange={(event) => setJd(event.target.value)} rows={15} minLength={50} maxLength={100000} placeholder="在这里粘贴完整 JD，内容将保持原始语言…" required /><span className="char-count">{jd.length.toLocaleString()} / 100,000</span></label>}
          {error && <div className="error" role="alert">{error}</div>}
          {showPasteFallback && <button type="button" className="fallback-button" onClick={() => { setMode("jd"); setError(""); setShowPasteFallback(false); }}>改为手动粘贴 JD</button>}
          <div className="form-actions"><button type="button" className="secondary-button" onClick={() => navigate("/my-jobs")}>取消</button><button className="primary-link button-link" type="submit" disabled={loading || (mode === "url" ? !url.trim() : jd.trim().length < 50)}>{loading ? <><span className="spinner" />正在解析岗位…</> : "解析岗位信息"}</button></div>
        </form>}
      </section>
      {mode !== "quick" && <p className="safe-fetch-note">只读取单个公开页面。JobPilot 不会绕过登录、反爬验证或访问内部网络。</p>}
    </main>
  );
}
