import { FormEvent, useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { discoveryApi } from "./api";
import { ROLE_FAMILIES, ROLE_FAMILY_LABELS } from "./decision-utils";
import { nextRefinementSelection } from "./discovery-selection";
import { buildDiscoveryParams, DISCOVERY_TAG_LABELS, type DiscoveryFilters } from "./discovery-utils";
import type { DiscoveryRefinementTag, DiscoveryResult, DiscoveryResultPage, DiscoverySession } from "./types";

const EMPTY_RESULTS: DiscoveryResultPage = { items: [], total: 0, page: 1, page_size: 25, total_pages: 0 };
const TERMINAL = new Set(["Completed", "Partial", "Failed", "Expired"]);
const RELEVANCE_LABELS = { High: "最符合本次目标", Medium: "可能感兴趣", Low: "其他结果" } as const;
const PERSONALIZED_LABELS = { Strong: "最符合本次目标，也与我的经历相关", Relevant: "符合本次目标", Neutral: "其他结果" } as const;
const RECRUITMENT_LABELS: Record<string, string> = { campus: "校招", experienced: "社招" };

export function DiscoveryProgress({ session }: { session: DiscoverySession }) {
  const title = session.state === "Searching" ? "正在搜索岗位…" : session.state === "Completed" ? "搜索完成" : session.state === "Partial" ? "搜索部分完成" : session.state === "Failed" ? "搜索失败" : session.state === "Expired" ? "搜索会话已过期" : session.state === "NeedsClarification" || session.state === "NeedsRefinement" ? "等待确认必要搜索条件" : "准备搜索";
  return <section className={`discovery-progress ${session.state.toLowerCase()}`}>
    <div><strong>{title}</strong><span>已发现 {session.discovered_count} · 临时结果 {session.result_count} · 重复 {session.duplicate_count}</span></div>
    {session.source_progress.length > 0 && <div className="source-progress">{session.source_progress.map((source) => <span key={`${source.source}-${source.channel || source.tenant || "default"}`} className={source.status.toLowerCase()}>{source.company}{source.channel && RECRUITMENT_LABELS[source.channel] ? ` · ${RECRUITMENT_LABELS[source.channel]}` : ""} · {source.status === "Completed" ? `${source.discovered_count} 个` : source.status === "Failed" ? "暂时失败" : source.status === "Searching" ? "搜索中" : "等待中"}</span>)}</div>}
    {session.source_plan?.coverage_message && <p>{session.source_plan.coverage_message}</p>}
    {session.result_cap_reached && <p>来源结果超过本次搜索预算，请进一步缩小搜索条件。</p>}
    <small>已搜索 {session.selected_sources.length} 个受支持来源 · Intent Claude calls: {session.claude_api_calls} · Phase 3 calls: 0</small>
  </section>;
}

export function DiscoveryResultCard({ result, busy, onAdd }: { result: DiscoveryResult; busy: boolean; onAdd: () => void }) {
  const personalized = result.personalization_derived;
  const bandLabel = personalized ? PERSONALIZED_LABELS[personalized.band] : RELEVANCE_LABELS[result.search_derived.relevance_band];
  return <article className={`discovery-card ${result.search_derived.excluded_by_current_search ? "excluded" : ""}`}>
    <div className="discovery-card-main"><span className={`relevance-band ${result.search_derived.relevance_band.toLowerCase()}`}>{bandLabel}</span><h3>{result.normalized.role}</h3><p>{result.normalized.company} · {result.normalized.location || "城市未注明"} · {ROLE_FAMILY_LABELS[result.deterministic_derived.role_family]}</p><small>{result.identity.provider === "greenhouse" ? `Greenhouse · ${result.identity.tenant}` : "ByteDance"}{result.normalized.recruitment_type ? ` · ${RECRUITMENT_LABELS[result.normalized.recruitment_type] || result.normalized.recruitment_type}` : ""}{result.normalized.published_date ? ` · ${result.normalized.published_date}` : ""}</small></div>
    <div className="why-job"><strong>Why this job</strong><ul>{result.search_derived.reason_items.map((reason, index) => <li className={reason.kind} key={`${reason.code}-${index}`}>{reason.kind === "matched" ? "✓" : reason.kind === "warning" || reason.kind === "excluded" ? "⚠" : "?"} {reason.label}</li>)}</ul>{personalized && <details className="personalization-evidence"><summary>为什么推荐给我？</summary><h4>与我的经历相关</h4><ul>{personalized.candidate_reasons.map((reason, index) => <li className="matched" key={`${reason.reason_type}-${index}`}>✓ {reason.display}</li>)}{personalized.candidate_reasons.length === 0 && <li className="unknown">? 暂无额外的候选人经历信号</li>}</ul><h4>潜在门槛</h4><ul>{personalized.candidate_constraint_signals.map((signal, index) => <li className={signal.status === "PotentialGap" ? "warning" : signal.status === "Unknown" ? "unknown" : "matched"} key={`${signal.type}-${index}`}>{signal.status === "Supported" ? "✓" : signal.status === "PotentialGap" ? "⚠" : "?"} {signal.display}</li>)}{personalized.candidate_constraint_signals.length === 0 && <li className="unknown">? 未检测到可比较的明确门槛</li>}</ul><h4>Supporting Candidate Evidence</h4><ul>{personalized.evidence.map((evidence) => <li key={evidence.evidence_ref}><strong>{evidence.context}</strong>：{evidence.text_summary}<small>{evidence.evidence_ref}</small></li>)}</ul></details>}</div>
    <div className="discovery-card-action">{result.in_my_jobs ? <><span className="already-added">已加入 My Jobs</span>{result.persistent_job_id && <Link to={`/jobs/${result.persistent_job_id}`}>查看岗位</Link>}</> : <button className="primary-link button-link" disabled={busy} onClick={onAdd}>{busy ? "正在加入…" : "Add to My Jobs"}</button>}<a href={result.identity.canonical_url} target="_blank" rel="noreferrer">原岗位 ↗</a></div>
  </article>;
}

export function RefinementPanel({ session, selectedTags, loading, onToggle, onSearch }: { session: DiscoverySession; selectedTags: string[]; loading: boolean; onToggle: (tag: DiscoveryRefinementTag) => void; onSearch: () => void }) {
  const required = session.state === "NeedsClarification" || session.required_refinement_groups.length > 0;
  const groups = required ? session.required_refinement_groups : session.optional_refinement_groups;
  return <section className="refinement-panel"><h2>{required ? "需要先确认一个关键条件" : "你还可以进一步选择（可跳过）"}</h2>{groups.map((group) => <div className="refinement-group" key={group.id}><h3>{group.label}</h3><div className="refinement-tags">{group.tags.map((tag) => <button type="button" disabled={loading} className={selectedTags.includes(tag.id) ? "selected" : ""} onClick={() => onToggle(tag)} key={tag.id}>{tag.label}</button>)}</div></div>)}<div className="refinement-actions"><button className="primary-link button-link" onClick={onSearch} disabled={loading || required}>这些就够了，开始搜索</button></div></section>;
}

export function PersonalizationToggle({ enabled, loading, message, onToggle }: { enabled: boolean; loading: boolean; message?: string | null; onToggle: (enabled: boolean) => void }) {
  return <div className={`personalization-toggle ${enabled ? "enabled" : ""}`}><label><input aria-label="个性化推荐" type="checkbox" checked={enabled} disabled={loading} onChange={(event) => onToggle(event.target.checked)} /><span>个性化推荐：{loading ? "加载中" : enabled ? "开启" : "关闭"}</span></label><small>{enabled ? "会使用你已确认的求职档案和经历证据优化排序与解释；不会改变本次搜索条件。" : "当前结果仅依据本次搜索条件，不读取你的求职档案。"}</small>{message && <em>{message}</em>}</div>;
}

export function DiscoveryFiltersBar({ filters, onChange }: { filters: DiscoveryFilters; onChange: (key: keyof DiscoveryFilters, value: string) => void }) {
  return <section className="discovery-filters" aria-label="发现结果筛选">
    <input aria-label="城市" placeholder="城市" value={filters.location} onChange={(event) => onChange("location", event.target.value)} />
    <input aria-label="公司" placeholder="公司" value={filters.company} onChange={(event) => onChange("company", event.target.value)} />
    <select aria-label="岗位方向" value={filters.role_family} onChange={(event) => onChange("role_family", event.target.value)}><option value="">全部方向</option>{ROLE_FAMILIES.map((family) => <option value={family} key={family}>{ROLE_FAMILY_LABELS[family]}</option>)}</select>
    <select aria-label="招聘类型" value={filters.recruitment_type} onChange={(event) => onChange("recruitment_type", event.target.value)}><option value="">全部招聘类型</option><option value="campus">校招</option><option value="experienced">社招</option></select>
    <select aria-label="相关度" value={filters.relevance} onChange={(event) => onChange("relevance", event.target.value)}><option value="">全部相关度</option><option value="High">最符合本次目标</option><option value="Medium">可能感兴趣</option><option value="Low">其他结果</option></select>
    <select aria-label="My Jobs 状态" value={filters.already_in_my_jobs} onChange={(event) => onChange("already_in_my_jobs", event.target.value)}><option value="">全部</option><option value="false">尚未加入</option><option value="true">已加入 My Jobs</option></select>
    <label className="excluded-toggle"><input type="checkbox" checked={filters.include_excluded === "true"} onChange={(event) => onChange("include_excluded", event.target.checked ? "true" : "")} />查看已排除结果</label>
    <select aria-label="排序" value={filters.sort} onChange={(event) => onChange("sort", event.target.value)}><option value="relevance">本次目标优先</option><option value="published">最近发布</option><option value="company">公司</option></select>
  </section>;
}

export default function DiscoverPage() {
  const [input, setInput] = useState("");
  const [session, setSession] = useState<DiscoverySession | null>(null);
  const [results, setResults] = useState<DiscoveryResultPage>(EMPTY_RESULTS);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState<DiscoveryFilters>({ location: "", company: "", role_family: "", recruitment_type: "", relevance: "", already_in_my_jobs: "", include_excluded: "", sort: "relevance" });
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [tagLabels, setTagLabels] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [personalizationEnabled, setPersonalizationEnabled] = useState(false);
  const [personalizationLoading, setPersonalizationLoading] = useState(false);
  const sessionId = session?.id;
  const sessionState = session?.state;

  const loadResults = useCallback(async (activeSession: DiscoverySession, activePage = page, activeFilters = filters) => {
    setResults(await discoveryApi.results(activeSession.id, buildDiscoveryParams(activePage, activeFilters)));
  }, [filters, page]);

  useEffect(() => {
    if (!sessionId || !sessionState || TERMINAL.has(sessionState) || sessionState === "NeedsClarification" || sessionState === "NeedsRefinement" || sessionState === "Ready") return;
    let active = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const poll = async () => {
      try {
        const current = await discoveryApi.get(sessionId);
        if (!active) return;
        if (current.state === "Completed" || current.state === "Partial") await loadResults(current, 1);
        setSession(current);
        if (!TERMINAL.has(current.state)) timer = setTimeout(poll, 1000);
      } catch (cause) { if (active) setError(cause instanceof Error ? cause.message : "搜索状态读取失败。"); }
    };
    timer = setTimeout(poll, 700);
    return () => { active = false; if (timer) clearTimeout(timer); };
  }, [sessionId, sessionState, loadResults]);

  async function start(active: DiscoverySession) {
    await discoveryApi.search(active.id);
    setSession({ ...active, state: "Searching" });
  }

  async function submit(event: FormEvent) {
    event.preventDefault(); setLoading(true); setError(""); setResults(EMPTY_RESULTS); setPage(1); setSelectedTags([]); setTagLabels({});
    try {
      const created = await discoveryApi.create(input.trim(), personalizationEnabled);
      setSession(created); setSelectedTags(created.search_context.refinement_tag_ids);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "岗位搜索失败。"); }
    finally { setLoading(false); }
  }

  async function toggleTag(tag: DiscoveryRefinementTag) {
    if (!session) return;
    const groups = [...session.required_refinement_groups, ...session.optional_refinement_groups];
    const previous = selectedTags;
    const next = nextRefinementSelection(previous, tag, groups);
    setSelectedTags(next);
    setTagLabels((current) => ({ ...current, [tag.id]: tag.label }));
    setLoading(true); setError("");
    try {
      const updated = await discoveryApi.updateContext(session.id, { selected_tag_ids: next });
      setSession(updated); setSelectedTags(updated.search_context.refinement_tag_ids);
    } catch (cause) { setSelectedTags(previous); setError(cause instanceof Error ? cause.message : "搜索条件更新失败。"); }
    finally { setLoading(false); }
  }

  async function beginSearch() {
    if (!session) return;
    setLoading(true); setError("");
    try { await start(session); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "岗位搜索失败。"); }
    finally { setLoading(false); }
  }

  async function add(result: DiscoveryResult) {
    if (!session) return;
    setBusyId(result.result_id); setError("");
    try { await discoveryApi.add(session.id, result.result_id); await loadResults(session); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "加入 My Jobs 失败。"); }
    finally { setBusyId(null); }
  }

  async function togglePersonalization(enabled: boolean) {
    setPersonalizationEnabled(enabled);
    if (!session) return;
    setPersonalizationLoading(true); setError("");
    try {
      const updated = await discoveryApi.updateContext(session.id, { personalization_enabled: enabled });
      setSession(updated);
      if (updated.state === "Completed" || updated.state === "Partial") await loadResults(updated, 1);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "个性化状态更新失败。");
    } finally { setPersonalizationLoading(false); }
  }

  function changeFilter(key: keyof DiscoveryFilters, value: string) {
    const next = { ...filters, [key]: value };
    setPage(1); setFilters(next);
    if (session && (session.state === "Completed" || session.state === "Partial")) loadResults(session, 1, next).catch((cause: Error) => setError(cause.message));
  }
  function changePage(next: number) { setPage(next); if (session) loadResults(session, next).catch((cause: Error) => setError(cause.message)); }
  const terminalSuccess = session && (session.state === "Completed" || session.state === "Partial");
  const contextLabels = session ? Array.from(new Set([
    ...session.search_context.explicit_concepts.filter((concept) => concept.polarity === "include").map((concept) => concept.raw_text),
    ...session.search_context.explicit_constraints.company_groups.map((group) => group === "large_tech" ? "大厂" : group),
    ...session.search_context.selected_tag_ids.map((id) => tagLabels[id] || DISCOVERY_TAG_LABELS[id] || id),
  ])) : [];
  const showRefinement = session && (session.state === "NeedsClarification" || session.state === "NeedsRefinement" || (session.state === "Ready" && session.optional_refinement_groups.length > 0));

  return <main className="workspace-shell discover-page">
    <header className="workspace-heading"><div><span className="eyebrow">Discover</span><h1>今天你想搜索什么机会？</h1><p>用自然语言描述目标，JobPilot 只搜索当前受支持的招聘源。</p></div></header>
    <section className="discover-search-card">
      <form onSubmit={submit}><label>搜索目标或招聘链接<input aria-label="搜索输入" value={input} onChange={(event) => setInput(event.target.value)} placeholder="北京 AI Agent 产品经理，应届，不要运营" required /></label><button className="primary-link button-link" disabled={loading || input.trim().length < 2}>{loading ? "正在理解…" : "开始"}</button></form>
      <PersonalizationToggle enabled={personalizationEnabled} loading={personalizationLoading} message={session?.personalization_message} onToggle={togglePersonalization} />
      <p className="muted">当前产品搜索聚焦国内岗位，并支持自然语言和 ByteDance 招聘搜索链接。</p>
    </section>
    {error && <div className="error" role="alert">{error}</div>}
    {session && contextLabels.length > 0 && <section className="search-context"><strong>我理解你想找：</strong><div>{contextLabels.map((label, index) => <span key={`${label}-${index}`}>{label}</span>)}</div><small>{session.search_context.parsing_method === "deterministic" ? "规则解析" : "规则 + AI 语义理解"} · 当前搜索条件优先</small></section>}
    {showRefinement && <RefinementPanel session={session} selectedTags={selectedTags} loading={loading} onToggle={toggleTag} onSearch={beginSearch} />}
    {session && !showRefinement && session.state === "Ready" && <section className="refinement-panel"><button className="primary-link button-link" disabled={loading} onClick={beginSearch}>开始搜索</button></section>}
    {session && !showRefinement && session.state !== "Ready" && <DiscoveryProgress session={session} />}
    {terminalSuccess && <>
      <DiscoveryFiltersBar filters={filters} onChange={changeFilter} />
      <section className="discovery-results"><div className="discovery-results-heading"><h2>临时搜索结果</h2><span>{results.total} 个岗位 · 未加入的结果不会保存</span></div>{!results.items.length && <div className="jobs-empty"><h3>没有符合筛选条件的岗位</h3><p>请调整结果筛选，或开始新的搜索。</p></div>}{results.items.map((result) => <DiscoveryResultCard key={result.result_id} result={result} busy={busyId === result.result_id} onAdd={() => add(result)} />)}</section>
      {results.total_pages > 1 && <nav className="pagination"><button disabled={page <= 1} onClick={() => changePage(page - 1)}>上一页</button><span>第 {page} / {results.total_pages} 页</span><button disabled={page >= results.total_pages} onClick={() => changePage(page + 1)}>下一页</button></nav>}
    </>}
  </main>;
}
