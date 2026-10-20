import { FormEvent, useEffect, useState } from "react";

import { jobNotesApi } from "./api";
import { formatDateTime } from "./job-utils";
import type { JobNote } from "./types";

export default function JobNotesDrawer({ jobId, jobLabel, onClose, onChanged }: {
  jobId: number;
  jobLabel: string;
  onClose: () => void;
  onChanged?: () => void;
}) {
  const [notes, setNotes] = useState<JobNote[]>([]);
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    try { setNotes(await jobNotesApi.list(jobId)); setError(""); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "备注加载失败。"); }
    finally { setLoading(false); }
  }
  useEffect(() => {
    let active = true;
    jobNotesApi.list(jobId)
      .then((items) => { if (active) { setNotes(items); setError(""); } })
      .catch((cause: Error) => { if (active) setError(cause.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [jobId]);

  async function create(event: FormEvent) {
    event.preventDefault();
    if (!content.trim()) return;
    setSaving(true);
    try { await jobNotesApi.create(jobId, content.trim()); setContent(""); await load(); onChanged?.(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "备注保存失败。"); }
    finally { setSaving(false); }
  }
  async function edit(note: JobNote) {
    const value = window.prompt("修改备注", note.content)?.trim();
    if (!value || value === note.content) return;
    try { await jobNotesApi.update(jobId, note.id, value); await load(); onChanged?.(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "备注更新失败。"); }
  }
  async function remove(note: JobNote) {
    if (!window.confirm("删除这条备注？")) return;
    try { await jobNotesApi.delete(jobId, note.id); await load(); onChanged?.(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "备注删除失败。"); }
  }

  return <div className="notes-drawer-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <aside className="notes-drawer" role="dialog" aria-modal="true" aria-labelledby="notes-drawer-title">
      <header><div><span className="eyebrow">岗位备注</span><h2 id="notes-drawer-title">{jobLabel}</h2></div><button className="quiet-button" onClick={onClose} aria-label="关闭备注">关闭</button></header>
      <div className="notes-timeline">
        {loading ? <div className="page-loading"><span className="spinner dark" />正在加载备注…</div> : notes.length ? notes.map((note) => <article className={`note-item note-${note.author_type}`} key={note.id}>
          <div><strong>{note.author_type === "agent" ? "Agent" : "你"}</strong><time>{formatDateTime(note.created_at)}</time></div>
          <p>{note.content}</p>
          {note.author_type === "human" && <div className="note-actions"><button onClick={() => void edit(note)}>编辑</button><button className="danger-text-button" onClick={() => void remove(note)}>删除</button></div>}
        </article>) : <div className="notes-empty">还没有备注。可以记录 HR 沟通、下一步或其他申请信息。</div>}
      </div>
      {error && <div className="error" role="alert">{error}</div>}
      <form className="note-composer" onSubmit={create}><label htmlFor={`note-${jobId}`}>新增备注</label><textarea id={`note-${jobId}`} rows={4} value={content} onChange={(event) => setContent(event.target.value)} placeholder="记录新的申请信息…" maxLength={10000} /><button className="primary-button" disabled={saving || !content.trim()}>{saving ? "正在保存…" : "添加备注"}</button></form>
    </aside>
  </div>;
}
