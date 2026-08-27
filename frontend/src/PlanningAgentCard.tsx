import type { PlanningToday } from "./types";

const PRIORITY_LABELS = { high: "优先", medium: "建议", low: "可选" } as const;
const ACTION_LABELS = {
  apply: "Apply",
  resume: "Resume",
  interview_prep: "面试准备",
  job_search: "岗位搜索",
  follow_up: "Follow up",
  review: "Review",
  plan: "Plan",
  other: "Next step",
} as const;

export default function PlanningAgentCard({ planning, loading, error, onGenerate, onAddToPlan }: {
  planning: PlanningToday | null;
  loading: boolean;
  error: string;
  onGenerate: (force: boolean) => void;
  onAddToPlan: (itemId: string) => void;
}) {
  const snapshot = planning?.snapshot;
  const focusItems = snapshot?.items.slice(0, 3) ?? [];
  const supportingItems = snapshot?.items.slice(3) ?? [];
  function AdviceItem({ item, index, compact = false }: {
    item: NonNullable<typeof snapshot>["items"][number];
    index: number;
    compact?: boolean;
  }) {
    return <article className={`advice-item${compact ? " compact" : ""}`}>
      {!compact && <span className="advice-number" aria-hidden="true">{String(index + 1).padStart(2, "0")}</span>}
      <div className="advice-copy">
        <div className="advice-labels"><span className="advice-priority" data-priority={item.priority}>{PRIORITY_LABELS[item.priority]}</span><span className="advice-action-badge">{ACTION_LABELS[item.action_type]}</span></div>
        <h3>{item.title}</h3><p>{item.reason}</p>
      </div>
      <button className="advice-add-button" disabled={item.added_plan_item_id !== null} onClick={() => onAddToPlan(item.id)}>{item.added_plan_item_id !== null ? "已加入计划" : "＋ 加入计划"}</button>
    </article>;
  }
  return <section className="planning-agent-card" aria-label="今日规划助手">
    <div className="planning-agent-heading">
      <div><span className="agent-sparkle">✦</span><div><span className="eyebrow">Today’s focus</span><h2>{snapshot ? "今天先把最重要的 3 件事推进掉" : "今天需要一点小助攻吗？"}</h2></div></div>
      {!snapshot && !planning?.empty_context && <button className="submit-button" disabled={loading} onClick={() => onGenerate(false)}>✨ 帮我规划今天</button>}
    </div>
    {!snapshot && !loading && <p className="planning-agent-intro">{planning?.empty_message || "我会看看你的岗位、计划和最近进度，帮你排一下今天最值得做的事情。"}</p>}
    {loading && <div className="planning-agent-loading" role="status"><span />正在看看你的求职进度…</div>}
    {error && <div className="planning-agent-error" role="alert">{error}<button onClick={() => onGenerate(Boolean(snapshot))}>重试</button></div>}
    {snapshot && <>
      {planning?.is_stale && <div className="planning-stale" role="status"><span>你的计划有更新</span><button onClick={() => onGenerate(true)} disabled={loading}>✨ 重新规划</button></div>}
      <p className="planning-summary">{snapshot.summary}</p>
      <div className="advice-list">{focusItems.map((item, index) => <AdviceItem item={item} index={index} key={item.id} />)}</div>
      {supportingItems.length > 0 && <details className="supporting-advice"><summary>还有 {supportingItems.length} 个可以顺手推进的事项 <span>查看全部 →</span></summary><div>{supportingItems.map((item, index) => <AdviceItem item={item} index={index + 3} compact key={item.id} />)}</div></details>}
      <footer className="planning-agent-footer"><span>生成于 {new Date(snapshot.generated_at).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })}</span>{!planning?.is_stale && <button onClick={() => onGenerate(true)} disabled={loading}>✨ 重新规划</button>}</footer>
      {snapshot.status === "Fallback" && <p className="planning-fallback-note">本次使用了安全的状态建议；没有自动修改任何岗位或计划。</p>}
    </>}
  </section>;
}
