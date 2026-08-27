import { useEffect, useState } from "react";

import { fitAnalysisApi } from "./api";
import {
  REQUIREMENT_IMPORTANCE_LABELS,
  REQUIREMENT_MATCH_LABELS,
} from "./analysis-utils";
import { formatFullDate } from "./job-utils";
import type { FitAnalysis, FitAnalysisState } from "./types";

export function FitAnalysisEmpty({
  analyzing,
  onAnalyze,
}: {
  analyzing: boolean;
  onAnalyze: () => void;
}) {
  return (
    <section className="fit-empty">
      <span className="eyebrow">Evidence-grounded match</span>
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
  const visiblePreparation = showAllPreparation
    ? analysis.suggested_preparation
    : analysis.suggested_preparation.slice(0, 3);
  return (
    <div className="fit-analysis">
      {isStale && <div className="stale-notice" role="status"><strong>当前匹配分析可能已过期</strong><span>求职档案或岗位信息已更新，建议重新分析。</span></div>}
      <section className="fit-score-card">
        <div className="score-ring" style={{ "--score": `${analysis.match_score * 3.6}deg` } as React.CSSProperties}>
          <div><strong>{analysis.match_score}</strong><span>/ 100</span></div>
        </div>
        <div className="fit-score-copy">
          <span className="card-kicker">Match Score</span>
          <h2>你的岗位匹配情况</h2>
          <p>{analysis.summary}</p>
          <small>最后分析：{formatFullDate(analysis.updated_at)}</small>
        </div>
        <button className="secondary-button" onClick={onReanalyze} disabled={analyzing}>{analyzing ? "正在重新分析…" : "重新分析"}</button>
      </section>

      <div className="fit-two-column">
        <section className="fit-card strengths"><span className="card-kicker">核心优势</span><h2>最值得强调的匹配点</h2>{analysis.strengths.length ? <div className="fit-item-list">{analysis.strengths.map((item) => <article key={item.requirement_ids.join("-")}><h3>{item.title}</h3><p>{item.explanation}</p><ul>{item.evidence.map((source) => <li key={`${source.source_type}-${source.source_id}`}><span>{source.context}</span>{source.text}</li>)}</ul></article>)}</div> : <p className="muted">暂未发现有充分证据支持的核心优势。</p>}</section>
        <section className="fit-card gaps"><span className="card-kicker">暂无匹配证据</span><h2>需要补充或确认的要求</h2>{analysis.gaps.length ? <div className="fit-item-list">{analysis.gaps.map((item) => <article key={item.requirement_id} className={`gap-${item.severity}`}><div className="gap-heading"><h3>{item.requirement}</h3><span>{item.evidence_status === "partial" ? "部分匹配" : "暂无证据"}</span></div><p>{item.explanation}</p>{item.next_step && <small>可以准备：{item.next_step}</small>}</article>)}</div> : <p className="muted">所有核心要求目前都有可用证据。</p>}</section>
      </div>

      <section className="fit-card evidence-map">
        <span className="card-kicker">逐项匹配</span><h2>我有哪些、还缺哪些</h2>
        <div className="evidence-table-wrap"><table><thead><tr><th>岗位要求</th><th>重要性</th><th>匹配状态</th><th>简历 / 经历证据</th><th>判断依据</th></tr></thead><tbody>{analysis.requirement_matches.map((item) => <tr key={item.requirement_id}><td><strong>{item.requirement_text}</strong>{item.is_hard_requirement && <span className="hard-badge">硬性要求</span>}</td><td>{REQUIREMENT_IMPORTANCE_LABELS[item.importance]}</td><td><span className={`assessment ${item.match_status.toLowerCase()}`}>{REQUIREMENT_MATCH_LABELS[item.match_status]}</span></td><td>{item.evidence_sources.length ? <ul>{item.evidence_sources.map((source) => <li key={`${source.source_type}-${source.source_id}`}><span>{source.context}</span>{source.text}</li>)}</ul> : <span className="muted">未找到支持证据</span>}</td><td>{item.reason}</td></tr>)}</tbody></table></div>
      </section>

      <section className="fit-card fit-preparation">
        <span className="card-kicker">简历优化方向</span><h2>最值得优先突出的内容</h2>
        {visiblePreparation.length ? <ol>{visiblePreparation.map((item, index) => <li key={`${item.title}-${index}`}><span>{String(index + 1).padStart(2, "0")}</span><div><h3>{item.title}</h3><p>{item.action}</p></div></li>)}</ol> : <p className="muted">暂无额外准备建议。</p>}
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
