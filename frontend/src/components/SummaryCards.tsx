import type { Summary } from "../types";
import { formatRate } from "../utils/geo";

interface SummaryCardsProps {
  summary: Summary;
}

export function SummaryCards({ summary }: SummaryCardsProps) {
  return (
    <div className="summary-grid">
      <article className="card">
        <h3>Total Jurisdictions</h3>
        <p className="metric">{summary.total}</p>
      </article>
      <article className="card matched">
        <h3>Matched</h3>
        <p className="metric">{summary.matched}</p>
      </article>
      <article className="card review">
        <h3>Needs Review</h3>
        <p className="metric">{summary.review}</p>
      </article>
      <article className="card unmatched">
        <h3>Unmatched</h3>
        <p className="metric">{summary.unmatched}</p>
      </article>
      <article className="card">
        <h3>Avg In-State Rate</h3>
        <p className="metric">
          {formatRate(summary.avg_in_state_rate)}
        </p>
      </article>
      <article className="card">
        <h3>Avg Out-of-State Rate</h3>
        <p className="metric">
          {formatRate(summary.avg_out_of_state_rate)}
        </p>
      </article>
    </div>
  );
}
