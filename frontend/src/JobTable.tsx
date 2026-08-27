import { Link, useNavigate } from "react-router-dom";

import { APPLICATION_STATUS_LABELS } from "./analysis-utils";
import { formatJobDate, JOB_STATUSES } from "./job-utils";
import type { JobListItem, JobStatus } from "./types";

export default function JobTable({
  jobs,
  onStatusChange,
  busyId,
}: {
  jobs: JobListItem[];
  onStatusChange: (job: JobListItem, status: JobStatus) => void;
  busyId?: number | null;
}) {
  const navigate = useNavigate();
  if (!jobs.length) {
    return (
      <div className="jobs-empty">
        <h3>岗位池还是空的</h3>
        <p>添加第一个岗位，把分散的招聘信息集中到 JobPilot。</p>
        <Link className="primary-link" to="/jobs/new">+ 添加岗位</Link>
      </div>
    );
  }

  return (
    <div className="job-table-wrap">
      <table className="job-table">
        <thead><tr><th>公司</th><th>岗位</th><th>匹配度</th><th>状态</th><th>加入时间</th></tr></thead>
        <tbody>
          {jobs.map((job) => (
            <tr
              key={job.id}
              tabIndex={0}
              onClick={() => navigate(`/jobs/${job.id}`)}
              onKeyDown={(event) => { if (event.key === "Enter") navigate(`/jobs/${job.id}`); }}
            >
              <td><strong>{job.company}</strong></td>
              <td><Link to={`/jobs/${job.id}`} onClick={(event) => event.stopPropagation()}>{job.role}</Link></td>
              <td>{job.match_score === null ? <span className="pending-score">待分析</span> : `${job.match_score}%`}</td>
              <td onClick={(event) => event.stopPropagation()}>
                <select
                  className={`status-select status-${job.status.toLowerCase().replaceAll(" ", "-")}`}
                  value={job.status}
                  disabled={busyId === job.id}
                  aria-label={`更新 ${job.company} ${job.role} 的状态`}
                  onChange={(event) => onStatusChange(job, event.target.value as JobStatus)}
                >
                  {JOB_STATUSES.map((status) => <option key={status} value={status}>{APPLICATION_STATUS_LABELS[status]}</option>)}
                </select>
              </td>
              <td>{formatJobDate(job.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
