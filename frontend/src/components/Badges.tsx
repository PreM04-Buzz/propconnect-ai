import type { LeadStage } from "../api/client";
import { stageLabel } from "../lib/format";

export function PriorityBadge({ priority }: { priority?: string | null }) {
  if (!priority) return null;
  return <span className={`badge priority-${priority}`}>{priority} priority</span>;
}

export function StageBadge({ stage }: { stage?: LeadStage | null }) {
  if (!stage) return <span className="badge">No lead</span>;
  return <span className={`badge stage-${stage}`}>{stageLabel(stage)}</span>;
}

export function ScoreRing({ score }: { score?: number | null }) {
  if (score == null) return <span className="score-ring muted">–</span>;
  const tone = score >= 70 ? "high" : score >= 40 ? "medium" : "low";
  return (
    <span className={`score-ring priority-${tone}`} title={`Lead score ${score}/100`}>
      {score}
    </span>
  );
}
