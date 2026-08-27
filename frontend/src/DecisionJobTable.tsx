import { Link, useNavigate } from "react-router-dom";

import { APPLICATION_STATUS_LABELS } from "./analysis-utils";
import { formatFullDate, JOB_STATUSES } from "./job-utils";
import type { ApplicationStatusDefinition, DecisionJobItem } from "./types";

export default function DecisionJobTable({ jobs, statuses = [], busyId, onStatusChange, onDelete }: {
  jobs: DecisionJobItem[];
  statuses?: ApplicationStatusDefinition[];
  busyId: number | null;
  onStatusChange: (job: DecisionJobItem, statusId: number) => void;
  onDelete: (job: DecisionJobItem) => void;
}) {
  const navigate = useNavigate();
  if (!jobs.length) return <div className="jobs-empty"><span aria-hidden="true">✦</span><h3>还没有加入岗位</h3><p>先分析一个岗位，或者手动添加你已经在关注的机会。</p><div><Link className="primary-link" to="/analyze">分析一个岗位</Link><Link className="secondary-button" to="/jobs/new">手动添加</Link></div></div>;
  return <div className="job-table-wrap"><table className="job-table workspace-job-table">
    <thead><tr><th>岗位</th><th>地点</th><th>Match Score</th><th>状态</th><th>最近更新</th><th><span className="sr-only">操作</span></th></tr></thead>
    <tbody>{jobs.map((job) => <tr key={job.id} tabIndex={0} onClick={() => navigate(`/jobs/${job.id}`)} onKeyDown={(event) => { if (event.key === "Enter") navigate(`/jobs/${job.id}`); }}>
      <td><Link to={`/jobs/${job.id}`} onClick={(event) => event.stopPropagation()}><strong>{job.role}</strong><span>{job.company}</span></Link></td>
      <td>{job.location || <span className="muted">未注明</span>}</td>
      <td>{job.match_is_stale ? <span className="stale-score">已过期</span> : job.match_score === null ? <span className="pending-score">待分析</span> : <span className="table-match-score">{job.match_score}%</span>}</td>
      <td onClick={(event) => event.stopPropagation()}><select className={`status-select status-${job.status.toLowerCase().replaceAll(" ", "-")}`} value={job.application_status_id ?? ""} disabled={busyId === job.id} aria-label={`更新 ${job.company} ${job.role} 的状态`} onChange={(event) => onStatusChange(job, Number(event.target.value))}>{statuses.length ? statuses.map((status) => <option key={status.id} value={status.id}>{status.label}</option>) : JOB_STATUSES.map((status) => <option key={status} value="">{APPLICATION_STATUS_LABELS[status]}</option>)}</select></td>
      <td>{formatFullDate(job.updated_at)}</td>
      <td onClick={(event) => event.stopPropagation()}><button className="danger-text-button" disabled={busyId === job.id} onClick={() => onDelete(job)}>删除</button></td>
    </tr>)}</tbody>
  </table></div>;
}
