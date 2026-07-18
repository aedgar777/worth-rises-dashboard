import type { MatchedRate } from "../types";
import { formatJurisdiction, getStateName } from "./jurisdiction";

function escapeCsv(value: string | number | null | undefined): string {
  if (value == null) {
    return "";
  }
  const text = String(value);
  if (text.includes(",") || text.includes('"') || text.includes("\n")) {
    return `"${text.replace(/"/g, '""')}"`;
  }
  return text;
}

export function downloadResultsCsv(
  results: MatchedRate[],
  filename = "worth-rises-matched-rates.csv",
) {
  const matched = results.filter((row) => row.match_status === "matched");

  const headers = [
    "type",
    "jurisdiction",
    "state",
    "in_state_rate",
    "out_of_state_rate",
  ];

  const sorted = [...matched].sort((a, b) => {
    const typeOrder = a.jurisdiction_type.localeCompare(b.jurisdiction_type);
    if (typeOrder !== 0) {
      return typeOrder;
    }
    const stateOrder = getStateName(a.state).localeCompare(getStateName(b.state));
    if (stateOrder !== 0) {
      return stateOrder;
    }
    return (a.county ?? "").localeCompare(b.county ?? "");
  });

  const lines = [
    headers.join(","),
    ...sorted.map((row) =>
      [
        row.jurisdiction_type,
        formatJurisdiction(row),
        row.state,
        row.in_state_rate ?? "",
        row.out_of_state_rate ?? "",
      ]
        .map(escapeCsv)
        .join(","),
    ),
  ];

  const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
