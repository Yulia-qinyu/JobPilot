import { useEffect, useState } from "react";

import { fitAnalysisApi } from "./api";
import {
  REQUIREMENT_IMPORTANCE_LABELS,
  REQUIREMENT_MATCH_LABELS,
} from "./analysis-utils";
import { formatFullDate } from "./job-utils";
import PreparationRecommendations from "./PreparationRecommendations";
import { linkedRequirementTexts, requirementTextMap, safeUserCopy } from "./requirement-display";
import type { FitAnalysis, FitAnalysisState } from "./types";

const ELIGIBILITY_LABELS = {
  Supported: "已支持",
  PotentialGap: "可能存在门槛差距",
  Unknown: "待确认",
} as const;

export function FitAnalysisEmpty({
  analyzing,
  onAnalyze,
}: {
  analyzing: boolean;
  onAnalyze: () => void;
}) {
  return (
    <section className="fit-empty">
      <span className="eyebrow">基于真实经历的匹配</span>
      <h2>看看你已经具备什么、还缺少什么证据</h2>
      <p>分析只使用已保存的主简历、已验证经历事实和结构化 JD，最终分数由确定性规则计算。</p>
      <button className="primary-link button-link" onClick={onAnalyze} disabled={analyzing}>
        {analyzing ? <><span className="spinner" />正在分析匹配度…</> : "分析匹配度"}
      </button>
    </section>
  );
}

export function FitAnalysisFailure({ message }: { message: string }) {
  return <div className="error fit-error" role="alert">{message}</div>;
}

export function FitAnalysisLoading() {
  return <section className="fit-loading"><span className="spinner dark" />正在读取匹配分析…</section>;
}

export function FitAnalysisResult({
  analysis,
  isStale,
  analyzing,
  onReanalyze,
}: {
  analysis: FitAnalysis;
  isStale: boolean;
  analyzing: boolean;
  onReanalyze: () => void;
}) {
  const [showAllPreparation, setShowAllPreparation] = useState(false);
  // Requirement Taxonomy V2 overlays default to [] on the backend but a legacy
  // or partial analysis payload can omit them. Normalize once so job detail
  // never white-screens on a missing array.
  const eligibilityRequirements = analysis.eligibility_requirements ?? [];
  const knowledgeRequirements = analysis.knowledge_requirements ?? [];
  const visiblePreparation = showAllPreparation
    ? analysis.suggested_preparation
    : analysis.suggested_preparation.slice(0, 3);
  const requirementLabels = requirementTextMap(analysis.requirement_matches);
  const allRequirementTexts = [...requirementLabels.values()];
  return (
    <div className="fit-analysis">
      {isStale && <div className="stale-notice" role="status"><strong>当前匹配分析可能已过期</strong><span>求职档案或岗位信息已更新，建议重新分析。</span></div>}
      <section className={`fit-score-card ${analysis.match_score === null ? "score-is-unavailable" : ""}`}>
        <div className="score-ring" style={{ "--score": `${(analysis.match_score ?? 0) * 3.6}deg` } as React.CSSProperties}>
          <div><strong>{analysis.match_score ?? "—"}</strong><span>{analysis.match_score === null ? "不评分" : "/ 100"}</span></div>
        </div>
        <div className="fit-score-copy">
          <span className="card-kicker">Match Score</span>
          <h2>{analysis.match_score === null ? "该岗位暂无可评分履历要求" : "你的岗位匹配情况"}</h2>
          <p>{safeUserCopy(analysis.summary, allRequirementTexts)}</p>
          <small>最后分析：{formatFullDate(analysis.updated_at)}</small>
        </div>
        <button className="secondary-button reanalyze-button" onClick={onReanalyze} disabled={analyzing}>{analyzing ? "正在重新分析…" : "↻ 重新分析"}</button>
      </section>

      {eligibilityRequirements.length > 0 && <section className="fit-card taxonomy-result-card eligibility-results">
        <span className="card-kicker">岗位资格</span><h2>明确门槛单独核验</h2>
        <p className="section-supporting-copy">资格要求不计入 Match Score；缺少信息会标记为待确认，而不是自动判定不满足。</p>
        <div className="taxonomy-result-list">{eligibilityRequirements.map((item) => <article key={item.requirement_id}>
          <div><h3>{item.requirement_text}</h3><span className={`eligibility-state eligibility-${item.status.toLowerCase()}`}>{ELIGIBILITY_LABELS[item.status]}</span></div>
          <p>{item.reason}</p>
        </article>)}</div>
      </section>}

      <div className="fit-two-column">
        <section className="fit-card strengths"><span className="card-kicker">核心优势</span><h2>最值得强调的匹配点</h2>{analysis.strengths.length ? <div className="fit-item-list">{analysis.strengths.map((item) => { const linked = linkedRequirementTexts(item.requirement_ids, requirementLabels); return <article key={item.requirement_ids.join("-")}><h3>{safeUserCopy(item.title, linked)}</h3><p>{safeUserCopy(item.explanation, linked)}</p><ul>{item.evidence.map((source) => <li key={`${source.source_type}-${source.source_id}`}><span>{source.context}</span>{source.text}</li>)}</ul></article>; })}</div> : <p className="muted">暂未发现有充分证据支持的核心优势。</p>}</section>
        <section className="fit-card gaps"><span className="card-kicker">暂无匹配证据</span><h2>需要补充或确认的要求</h2>{analysis.gaps.length ? <div className="fit-item-list">{analysis.gaps.map((item) => { const linked = [item.requirement]; return <article key={item.requirement_id} className={`gap-${item.severity}`}><div className="gap-heading"><h3>{item.requirement}</h3><span>{item.evidence_status === "partial" ? "部分匹配" : "暂无证据"}</span></div><p>{safeUserCopy(item.explanation, linked)}</p>{item.next_step && <small>可以准备：{safeUserCopy(item.next_step, linked)}</small>}</article>; })}</div> : <p className="muted">所有核心要求目前都有可用证据。</p>}</section>
      </div>

      <section className="fit-card evidence-map">
        <span className="card-kicker">逐项匹配</span><h2>我有哪些、还缺哪些</h2>
        {analysis.requirement_matches.length ? <div className="requirement-evidence-list">{analysis.requirement_matches.map((item) => <article key={item.requirement_id}>
          <header><h3>{item.requirement_text}</h3><div className="requirement-badges"><span className="importance-badge">{REQUIREMENT_IMPORTANCE_LABELS[item.importance]}</span><span className={`assessment ${item.match_status.toLowerCase()}`}>{REQUIREMENT_MATCH_LABELS[item.match_status]}</span>{item.is_hard_requirement && <span className="hard-badge">硬性要求</span>}</div></header>
          <div className="requirement-evidence-grid">
            <section><h4>支持证据</h4>{item.evidence_sources.length ? <ul>{item.evidence_sources.map((source) => <li key={`${source.source_type}-${source.source_id}`}><span>{source.context}</span><p>{source.text}</p></li>)}</ul> : <p className="muted">当前没有可引用的已验证证据。</p>}</section>
            <section><h4>判断依据</h4><p>{safeUserCopy(item.reason, [item.requirement_text])}</p></section>
          </div>
        </article>)}</div> : <div className="score-unavailable"><strong>Match Score 暂不可用</strong><p>该岗位没有可由履历证据稳定判断的要求，因此不会显示 0 分。</p></div>}
      </section>

      {knowledgeRequirements.length > 0 && <section className="fit-card taxonomy-result-card knowledge-results">
        <span className="card-kicker">岗位知识要求</span><h2>面试前值得准备的知识主题</h2>
        <p className="section-supporting-copy">这些主题不计入 Match Score，可作为面试准备方向。</p>
        <div className="knowledge-result-list">{knowledgeRequirements.map((item) => {
          const topics = item.knowledge_topics ?? [];
          return <article key={item.requirement_id}>
            <h3>{item.requirement_text}</h3>
            {topics.length > 0 && <div className="topic-tags">{topics.map((topic) => <span key={topic}>{topic}</span>)}</div>}
          </article>;
        })}</div>
      </section>}

      <section className="fit-card fit-preparation">
        <span className="card-kicker">简历优化方向</span><h2>最值得优先突出的内容</h2>
        {visiblePreparation.length ? <PreparationRecommendations items={visiblePreparation} matches={analysis.requirement_matches} /> : <p className="muted">暂无额外准备建议。</p>}
        {analysis.suggested_preparation.length > 3 && <button className="more-button" onClick={() => setShowAllPreparation((value) => !value)}>{showAllPreparation ? "收起建议" : `查看更多建议（${analysis.suggested_preparation.length - 3}）`}</button>}
      </section>
    </div>
  );
}

export default function FitAnalysisPanel({ jobId }: { jobId: number }) {
  const [state, setState] = useState<FitAnalysisState | null>(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    fitAnalysisApi.get(jobId)
      .then((value) => { if (active) setState(value); })
      .catch((cause: Error) => { if (active) setError(cause.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [jobId]);

  async function analyze() {
    setAnalyzing(true); setError("");
    try { setState(await fitAnalysisApi.run(jobId)); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "匹配分析失败，请稍后重试。"); }
    finally { setAnalyzing(false); }
  }

  if (loading) return <FitAnalysisLoading />;
  return <>{error && <FitAnalysisFailure message={error} />}{state?.analysis ? <FitAnalysisResult analysis={state.analysis} isStale={state.is_stale} analyzing={analyzing} onReanalyze={() => void analyze()} /> : <FitAnalysisEmpty analyzing={analyzing} onAnalyze={() => void analyze()} />}</>;
}
