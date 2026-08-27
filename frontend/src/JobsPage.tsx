import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { jobDecisionsApi, jobsApi, workspaceApi } from "./api";
import DecisionJobTable from "./DecisionJobTable";
import type { ApplicationStatusDefinition, DecisionJobItem, DecisionJobPage } from "./types";

const EMPTY_PAGE: DecisionJobPage = { items: [], total: 0, page: 1, page_size: 50, total_pages: 0 };

export default function JobsPage() {
  const [data, setData] = useState<DecisionJobPage>(EMPTY_PAGE);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({ company: "", application_status: "", match_status: "", sort: "recent" });
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [statuses, setStatuses] = useState<ApplicationStatusDefinition[]>([]);
  const [managing, setManaging] = useState(false);
  const [newStatus, setNewStatus] = useState("");

  const load = useCallback(async () => {
    const params = new URLSearchParams({ page: String(page), page_size: "50", sort: filters.sort });
    Object.entries(filters).forEach(([key, value]) => { if (value && key !== "sort") params.set(key, value); });
    try { setData(await jobDecisionsApi.list(params)); setError(""); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "岗位加载失败。"); }
    finally { setLoading(false); }
  }, [filters, page]);

  useEffect(() => {
    let active = true;
    const params = new URLSearchParams({ page: String(page), page_size: "50", sort: filters.sort });
    Object.entries(filters).forEach(([key, value]) => { if (value && key !== "sort") params.set(key, value); });
    jobDecisionsApi.list(params)
      .then((value) => { if (active) { setData(value); setError(""); } })
      .catch((cause: Error) => { if (active) setError(cause.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [filters, page]);
  useEffect(() => { workspaceApi.statuses().then(setStatuses).catch((cause: Error) => setError(cause.message)); }, []);
  function changeFilter(key: string, value: string) { setPage(1); setFilters((current) => ({ ...current, [key]: value })); }
  async function updateStatus(job: DecisionJobItem, statusId: number) {
    setBusyId(job.id);
    try { await jobsApi.update(job.id, { application_status_id: statusId }); await load(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "状态更新失败。"); }
    finally { setBusyId(null); }
  }
  async function addStatus() { if (!newStatus.trim()) return; try { await workspaceApi.createStatus(newStatus.trim()); setStatuses(await workspaceApi.statuses()); setNewStatus(""); } catch (cause) { setError(cause instanceof Error ? cause.message : "状态创建失败。"); } }
  async function renameStatus(item: ApplicationStatusDefinition) { const label = window.prompt("新的状态名称", item.label)?.trim(); if (!label || label === item.label) return; try { await workspaceApi.updateStatus(item.id, { label }); setStatuses(await workspaceApi.statuses()); await load(); } catch (cause) { setError(cause instanceof Error ? cause.message : "状态更新失败。"); } }
  async function removeStatus(item: ApplicationStatusDefinition) { if (item.is_system_default) return; const targetText = window.prompt("若有岗位使用此状态，请输入迁移目标状态 ID；未使用可留空。", "")?.trim(); if (targetText === undefined) return; try { await workspaceApi.deleteStatus(item.id, targetText ? Number(targetText) : undefined); setStatuses(await workspaceApi.statuses()); await load(); } catch (cause) { setError(cause instanceof Error ? cause.message : "状态删除失败。"); } }
  async function deleteJob(job: DecisionJobItem) {
    if (!window.confirm(`删除「${job.company} · ${job.role}」？该岗位的分析、简历优化和投递记录也会删除。`)) return;
    setBusyId(job.id);
    try { await jobsApi.delete(job.id); await load(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "岗位删除失败。"); }
    finally { setBusyId(null); }
  }

  return <main className="workspace-shell jobs-page">
    <header className="workspace-heading compact"><div><span className="eyebrow">Application workspace</span><h1>我的岗位</h1><p>统一管理准备投递和已经投递的岗位。</p></div><div className="heading-actions"><button className="secondary-button" onClick={() => setManaging((value) => !value)}>管理状态</button><Link className="primary-link" to="/jobs/new">+ 手动添加岗位</Link></div></header>
    {managing && <section className="status-manager"><div><h2>管理状态</h2><p>默认状态可重命名和排序；自定义状态在没有岗位使用时可以删除。</p></div><div className="status-definition-list">{statuses.map((item) => <div key={item.id}><span>{item.label}</span><small>ID {item.id}{item.is_system_default ? " · 默认" : " · 自定义"}</small><button onClick={() => void renameStatus(item)}>重命名</button>{!item.is_system_default && <button className="danger-text-button" onClick={() => void removeStatus(item)}>删除</button>}</div>)}</div><div className="inline-add"><input value={newStatus} onChange={(event) => setNewStatus(event.target.value)} placeholder="例如：一面" /><button onClick={() => void addStatus()}>新增状态</button></div></section>}
    <section className="workspace-toolbar" aria-label="岗位筛选">
      <div className="status-filter-pills"><button className={!filters.application_status ? "active" : ""} onClick={() => changeFilter("application_status", "")}>全部</button>{statuses.map((value) => <button className={filters.application_status === String(value.id) ? "active" : ""} key={value.id} onClick={() => changeFilter("application_status", String(value.id))}>{value.label}</button>)}</div>
      <div className="compact-filters"><input aria-label="公司筛选" placeholder="搜索公司" value={filters.company} onChange={(event) => changeFilter("company", event.target.value)} /><select aria-label="匹配状态" value={filters.match_status} onChange={(event) => changeFilter("match_status", event.target.value)}><option value="">全部匹配状态</option><option value="pending">待分析</option><option value="analyzed">已分析</option><option value="stale">分析已过期</option></select><select aria-label="排序" value={filters.sort} onChange={(event) => changeFilter("sort", event.target.value)}><option value="recent">最近更新</option><option value="company">公司</option><option value="match_score">匹配度</option></select></div>
    </section>
    {error && <div className="error" role="alert">{error}</div>}
    {loading ? <div className="page-loading"><span className="spinner dark" />正在加载岗位…</div> : <DecisionJobTable jobs={data.items} statuses={statuses} onStatusChange={updateStatus} onDelete={deleteJob} busyId={busyId} />}
    {!loading && data.total_pages > 1 && <nav className="pagination" aria-label="分页"><button disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>上一页</button><span>第 {data.page} / {data.total_pages} 页 · 共 {data.total} 个岗位</span><button disabled={page >= data.total_pages} onClick={() => setPage((value) => value + 1)}>下一页</button></nav>}
  </main>;
}
