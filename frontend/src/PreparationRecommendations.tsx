import { presentPreparation } from "./requirement-display";
import type { PreparationItem, RequirementMatch } from "./types";

export default function PreparationRecommendations({
  items,
  matches,
}: {
  items: PreparationItem[];
  matches: RequirementMatch[];
}) {
  return <ol className="preparation-recommendations">{items.map((item, index) => {
    const display = presentPreparation(item, matches);
    return <li key={`${item.title}-${index}`}>
      <span className="recommendation-number">{String(index + 1).padStart(2, "0")}</span>
      <div className="recommendation-content">
        <h3>{display.title}</h3>
        {display.requirements.length > 0 && <div className="recommendation-field"><span>对应岗位要求</span><p>{display.requirements.join("；")}</p></div>}
        <div className="recommendation-field"><span>建议方向</span><p>{display.action}</p></div>
      </div>
    </li>;
  })}</ol>;
}
