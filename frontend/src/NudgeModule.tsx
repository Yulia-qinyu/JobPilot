import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { nudgesApi, workspaceApi } from "./api";
import { nudgeHref, STRATEGY_LABELS } from "./nudge-utils";
import type { JobSearchStrategy, Nudge } from "./types";

/** Pure presentation. Returns a minimal line when there is nothing to show. */
export function NudgePanel({
  nudges,
  strategyLabel,
}: {
  nudges: Nudge[];
  strategyLabel: string | null;
}) {
  if (!nudges.length) {
    return (
      <p className="nudge-module-empty">
        {strategyLabel
          ? `按「${strategyLabel}」看，当前没有需要特别处理的岗位。`
          : "当前没有需要特别处理的岗位。"}
      </p>
    );
  }
  return (
    <section className="nudge-module" aria-label="求职提醒">
      <div className="nudge-module-head">
        <div>
          <span className="card-kicker">求职提醒</span>
          <h2>{nudges.length} 件事值得处理</h2>
        </div>
        {strategyLabel && <p>根据你的「{strategyLabel}」和当前岗位状态整理。</p>}
      </div>
      <ul className="nudge-list">
        {nudges.map((nudge, index) => (
          <li
            key={`${nudge.type}-${nudge.job_id ?? "pool"}-${index}`}
            className="nudge-item"
            data-priority={nudge.priority}
          >
            <div className="nudge-copy">
              <h3>{nudge.title}</h3>
              <p>{nudge.message}</p>
            </div>
            <Link className="nudge-cta" to={nudgeHref(nudge)}>
              去看看
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

export default function NudgeModule() {
  const [nudges, setNudges] = useState<Nudge[]>([]);
  const [strategy, setStrategy] = useState<JobSearchStrategy | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let active = true;
    Promise.all([nudgesApi.list(), workspaceApi.getStrategy()])
      .then(([list, s]) => {
        if (!active) return;
        setNudges(list);
        setStrategy(s.job_search_strategy);
      })
      .catch(() => {
        /* Nudges are advisory: on failure show nothing rather than an error. */
      })
      .finally(() => {
        if (active) setReady(true);
      });
    return () => {
      active = false;
    };
  }, []);

  if (!ready) return null;
  return (
    <NudgePanel
      nudges={nudges}
      strategyLabel={strategy ? STRATEGY_LABELS[strategy] : null}
    />
  );
}
