import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { dashboardApi, jobsApi } from "./api";
import JobTable from "./JobTable";
import type { DashboardData, JobListItem, JobStatus } from "./types";

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState<number | null>(null);

  const load = () => dashboardApi.get().then(setData).catch((cause: Error) => setError(cause.message));
  useEffect(() => { void load(); }, []);

  async function updateStatus(job: JobListItem, status: JobStatus) {
    setBusyId(job.id);
    setError("");
    try {
      await jobsApi.update(job.id, { status });
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "状态更新失败，请重试。");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <main className="workspace-shell dashboard-page">
      <header className="workspace-heading">
        <div><span className="eyebrow">秋招进度一览</span><h1>今天，继续推进。</h1><p>集中管理岗位、投递阶段与下一步行动。</p></div>
        <Link className="primary-link" to="/jobs/new">+ 添加岗位</Link>
      </header>
      {error && <div className="error" role="alert">{error}</div>}
      {!data ? <div className="page-loading"><span className="spinner dark" />正在加载首页…</div> : <>
        <section className="metric-grid" aria-label="招聘进度">
          <article><strong>{data.counts.total}</strong><span>个岗位</span></article>
          <article><strong>{data.counts.applied}</strong><span>个已投递</span></article>
          <article><strong>{data.counts.interviews}</strong><span>个面试</span></article>
          <article><strong>{data.counts.offers}</strong><span>个 Offer</span></article>
        </section>

        <section className="target-overview">
          <div className="section-heading"><div><span className="eyebrow">当前目标</span><h2>你的求职方向</h2></div><Link to="/profile">编辑求职档案</Link></div>
          <div className="target-overview-grid">
            <div><span>目标公司</span><p>{data.profile.target_companies.map((item) => item.name).join(" · ") || "暂未设置"}</p></div>
            <div><span>目标岗位</span><p>{data.profile.target_roles.map((item) => item.name).join(" · ") || "暂未设置"}</p></div>
            <div><span>目标城市</span><p>{data.profile.preferred_location || "暂未设置"}</p></div>
          </div>
        </section>

        <section className="job-pool-section">
          <div className="section-heading"><div><span className="eyebrow">Job Pool</span><h2>岗位池</h2></div><Link to="/jobs">查看全部岗位</Link></div>
          <JobTable jobs={data.jobs.slice(0, 8)} onStatusChange={updateStatus} busyId={busyId} />
        </section>
      </>}
    </main>
  );
}
