import type { MatchedRate } from "../types";
import { formatJurisdiction } from "./jurisdiction";

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

export function downloadResultsCsv(results: MatchedRate[], filename = "worth-rises-results.csv") {
  const headers = [
    "type",
    "jurisdiction",
    "state",
    "county",
    "facility",
    "in_state_rate",
    "out_of_state_rate",
    "status",
    "confidence",
    "place",
    "facility_rules",
    "notes",
  ];

  const sorted = [...results].sort((a, b) => {
    const typeOrder = a.jurisdiction_type.localeCompare(b.jurisdiction_type);
    if (typeOrder !== 0) {
      return typeOrder;
    }
    const stateOrder = a.state.localeCompare(b.state);
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
        row.county ?? "",
        row.facility_name ?? "",
        row.in_state_rate ?? "",
        row.out_of_state_rate ?? "",
        row.match_status,
        row.match_confidence.toFixed(3),
        row.place_description ?? "",
        row.facility_rules ?? "",
        row.notes ?? "",
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
