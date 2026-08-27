import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { jobImportsApi } from "./api";
import { isImportTerminal, isSupportedByteDanceSearchUrl, startImportPolling } from "./job-import-utils";
import type { JobImportSession } from "./types";

const ERROR_MESSAGES: Record<string, string> = {
  JOB_SOURCE_RESULT_TOO_LARGE: "搜索结果过多，请先在招聘官网进一步缩小筛选范围。",
  JOB_SOURCE_UNAVAILABLE: "暂时无法读取招聘网站，请稍后重新提交。",
  JOB_IMPORT_FAILED: "岗位导入未完成，请稍后重新提交。",
};

export function JobImportProgress({ session }: { session: JobImportSession }) {
  const terminal = isImportTerminal(session.status);
  const total = Math.max(session.discovered_count, 1);
  const percent = Math.min(100, Math.round((session.processed_count / total) * 100));
  const statusText = session.status === "Queued"
    ? "等待开始…"
    : session.stage === "Discovering"
      ? "正在发现岗位…"
      : session.stage === "Importing"
        ? "正在导入岗位…"
        : session.status === "Failed"
          ? "导入失败"
          : session.status === "Partial"
            ? "部分岗位已导入"
            : "导入完成";
  return (
    <section className={`import-progress import-${session.status.toLowerCase()}`} aria-live="polite">
      <header><div><span className="card-kicker">Import Session #{session.id}</span><h2>{statusText}</h2></div><strong>{session.stage === "Discovering" ? session.discovered_count : `${session.processed_count} / ${session.discovered_count}`}</strong></header>
      <div className="progress-track"><span style={{ width: `${session.stage === "Discovering" ? 8 : percent}%` }} /></div>
      <div className="import-counts">
        <div><strong>{session.discovered_count}</strong><span>已发现</span></div>
        <div><strong>{session.imported_count}</strong><span>新增</span></div>
        <div><strong>{session.updated_count}</strong><span>更新</span></div>
        <div><strong>{session.duplicate_count}</strong><span>重复</span></div>
        <div><strong>{session.failed_count}</strong><span>失败</span></div>
      </div>
      {session.error_code && <div className="error" role="alert">{ERROR_MESSAGES[session.error_code] || "导入未完成，请稍后重新提交。"}</div>}
      {terminal && session.status !== "Failed" && <Link className="primary-link" to={`/jobs?import_session=${session.id}`}>查看本次导入岗位</Link>}
    </section>
  );
}

export default function JobImportPanel() {
  const [url, setUrl] = useState("");
  const [session, setSession] = useState<JobImportSession | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const sessionId = session?.id;
  const sessionStatus = session?.status;

  useEffect(() => {
    if (!sessionId || !sessionStatus || isImportTerminal(sessionStatus)) return;
    return startImportPolling(
      () => jobImportsApi.get(sessionId),
      (next) => { setSession(next); setError(""); },
      (cause) => setError(cause.message),
    );
  }, [sessionId, sessionStatus]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!isSupportedByteDanceSearchUrl(url)) {
      setError("请粘贴 ByteDance 社招或校招的搜索结果 URL。");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      setSession(await jobImportsApi.create(url.trim()));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "岗位导入创建失败。");
    } finally {
      setSubmitting(false);
    }
  }

  if (session) return <JobImportProgress session={session} />;
  return (
    <section className="add-job-card import-card">
      <form onSubmit={submit}>
        <label>ByteDance 搜索结果 URL<input type="url" value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://jobs.bytedance.com/campus/position?..." required /></label>
        <p className="import-help">请先在 ByteDance 招聘官网设置城市、职位类别或关键词，再复制搜索结果页 URL。导入只负责发现、标准化和保存岗位，不会自动运行匹配分析。</p>
        {error && <div className="error" role="alert">{error}</div>}
        <div className="form-actions"><button className="primary-link button-link" type="submit" disabled={submitting || !url.trim()}>{submitting ? <><span className="spinner" />正在创建导入任务…</> : "开始导入岗位"}</button></div>
      </form>
    </section>
  );
}
