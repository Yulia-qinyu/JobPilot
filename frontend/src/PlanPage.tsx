import { FormEvent, useEffect, useMemo, useState } from "react";

import { jobsApi, planningApi, workspaceApi } from "./api";
import PlanningAgentCard from "./PlanningAgentCard";
import type { JobListItem, PlanItem, PlanningToday, PlanType } from "./types";

const TYPE_LABELS: Record<PlanType, string> = {
  application: "投递", resume: "简历", interview_prep: "面试准备",
  job_search: "岗位搜索", follow_up: "跟进", other: "其他",
};

function PlanGroup({ title, values, onToggle, onDelete }: {
  title: string;
  values: PlanItem[];
  onToggle: (item: PlanItem) => void;
  onDelete: (item: PlanItem) => void;
}) {
  return <section className="plan-group">
    <h2>{title}<span>{values.length}</span></h2>
    {values.length ? <div className="plan-list">{values.map((item) => <article className={`plan-item ${item.status}`} key={item.id}>
      <button className="plan-check" aria-label={item.status === "done" ? "重新设为未完成" : "标记完成"} onClick={() => onToggle(item)}>{item.status === "done" ? "✓" : ""}</button>
      <div><div className="plan-meta"><span>{item.date}{item.time_optional ? ` · ${item.time_optional}` : ""}</span><span className="soft-badge">{TYPE_LABELS[item.type]}</span></div><h3>{item.title}</h3>{item.job && <p>关联：{item.job.company} · {item.job.role}</p>}{item.notes && <p>{item.notes}</p>}</div>
      <button className="danger-text-button" onClick={() => onDelete(item)}>删除</button>
    </article>)}</div> : <p className="plan-empty">暂时没有计划。</p>}
  </section>;
}

export default function PlanPage() {
  const now = new Date();
  const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
  const [items, setItems] = useState<PlanItem[]>([]);
  const [jobs, setJobs] = useState<JobListItem[]>([]);
  const [form, setForm] = useState({ title: "", date: today, time_optional: "", job_id: "", type: "other" as PlanType, notes: "" });
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState("");
  const [planning, setPlanning] = useState<PlanningToday | null>(null);
  const [planningLoading, setPlanningLoading] = useState(false);
  const [planningError, setPlanningError] = useState("");

  async function load() {
    const [plans, jobList, planningState] = await Promise.all([workspaceApi.plans(), jobsApi.list(), planningApi.today()]);
    setItems(plans); setJobs(jobList); setPlanning(planningState);
  }
  useEffect(() => {
    let active = true;
    Promise.all([workspaceApi.plans(), jobsApi.list(), planningApi.today()])
      .then(([plans, jobList, planningState]) => { if (active) { setItems(plans); setJobs(jobList); setPlanning(planningState); } })
      .catch((cause: Error) => { if (active) setError(cause.message); });
    return () => { active = false; };
  }, []);
  const grouped = useMemo(() => ({
    today: items.filter((item) => item.status === "todo" && item.date === today),
    upcoming: items.filter((item) => item.status === "todo" && item.date !== today),
    done: items.filter((item) => item.status === "done"),
  }), [items, today]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    try {
      await workspaceApi.createPlan({ ...form, time_optional: form.time_optional || null, job_id: form.job_id ? Number(form.job_id) : null, notes: form.notes || null });
      setForm((current) => ({ ...current, title: "", time_optional: "", notes: "" }));
      setShowForm(false); await load();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "计划保存失败。"); }
  }
  async function toggle(item: PlanItem) { await workspaceApi.updatePlan(item.id, { status: item.status === "done" ? "todo" : "done" }); await load(); }
  async function remove(item: PlanItem) { if (!window.confirm(`删除计划「${item.title}」？`)) return; await workspaceApi.deletePlan(item.id); await load(); }
  async function generateAdvice(force: boolean) {
    setPlanningLoading(true); setPlanningError("");
    try { setPlanning(await planningApi.generate(force)); }
    catch (cause) { setPlanningError(cause instanceof Error ? cause.message : "这次规划没有成功，可以稍后再试。"); }
    finally { setPlanningLoading(false); }
  }
  async function addAdviceToPlan(itemId: string) {
    if (!planning?.snapshot) return;
    setPlanningError("");
    try { await planningApi.addToPlan(planning.snapshot.id, itemId); await load(); }
    catch (cause) { setPlanningError(cause instanceof Error ? cause.message : "加入计划失败。"); }
  }

  return <main className="workspace-shell plan-page">
    <header className="workspace-heading compact"><div><span className="eyebrow">Your application plan</span><h1>我的计划</h1><p>记录准备做什么和已经完成什么，JobPilot 会在未来规划时参考这些真实记录。</p></div><button className="primary-link button-link" onClick={() => setShowForm((value) => !value)}>+ 添加计划</button></header>
    {error && <div className="error" role="alert">{error}</div>}
    <PlanningAgentCard planning={planning} loading={planningLoading} error={planningError} onGenerate={(force) => void generateAdvice(force)} onAddToPlan={(itemId) => void addAdviceToPlan(itemId)} />
    {showForm && <form className="plan-form" onSubmit={submit}>
      <label>标题<input required value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} /></label>
      <label>日期<input type="date" required value={form.date} onChange={(event) => setForm({ ...form, date: event.target.value })} /></label>
      <label>时间（可选）<input type="time" value={form.time_optional} onChange={(event) => setForm({ ...form, time_optional: event.target.value })} /></label>
      <label>类型<select value={form.type} onChange={(event) => setForm({ ...form, type: event.target.value as PlanType })}>{Object.entries(TYPE_LABELS).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
      <label>关联岗位（可选）<select value={form.job_id} onChange={(event) => setForm({ ...form, job_id: event.target.value })}><option value="">不关联岗位</option>{jobs.map((job) => <option key={job.id} value={job.id}>{job.company} · {job.role}</option>)}</select></label>
      <label className="plan-notes">Notes（可选）<textarea rows={3} value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} /></label>
      <div><button className="submit-button" type="submit">保存计划</button><button className="secondary-button" type="button" onClick={() => setShowForm(false)}>取消</button></div>
    </form>}
    <PlanGroup title="今天" values={grouped.today} onToggle={(item) => void toggle(item)} onDelete={(item) => void remove(item)} />
    <PlanGroup title="接下来" values={grouped.upcoming} onToggle={(item) => void toggle(item)} onDelete={(item) => void remove(item)} />
    <PlanGroup title="已完成" values={grouped.done} onToggle={(item) => void toggle(item)} onDelete={(item) => void remove(item)} />
  </main>;
}
