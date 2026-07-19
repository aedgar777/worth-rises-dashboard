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

function sortJurisdictionRows(rows: MatchedRate[]): MatchedRate[] {
  return [...rows].sort((a, b) => {
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
}

function downloadCsv(lines: string[], filename: string) {
  const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export function downloadResultsCsv(
  results: MatchedRate[],
  filename = "worth-rises-cleaned-list.csv",
) {
  const matched = results.filter((row) => row.match_status === "matched");

  const headers = [
    "type",
    "jurisdiction",
    "state",
    "in_state_rate",
    "out_of_state_rate",
  ];

  const lines = [
    headers.join(","),
    ...sortJurisdictionRows(matched).map((row) =>
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

  downloadCsv(lines, filename);
}

function buildUnmatchedReason(row: MatchedRate): string {
  const parts = [row.facility_rules, row.notes].filter(Boolean);
  return parts.join("; ") || "No match detail recorded";
}

export function downloadUnmatchedCsv(
  results: MatchedRate[],
  filename = "worth-rises-unmatched-list.csv",
) {
  const pending = results.filter(
    (row) => row.match_status === "review" || row.match_status === "unmatched",
  );

  const headers = [
    "type",
    "jurisdiction",
    "state",
    "status",
    "confidence",
    "facility",
    "reason",
  ];

  const lines = [
    headers.join(","),
    ...sortJurisdictionRows(pending).map((row) =>
      [
        row.jurisdiction_type,
        formatJurisdiction(row),
        row.state,
        row.match_status,
        row.match_confidence.toFixed(3),
        row.facility_name ?? "",
        buildUnmatchedReason(row),
      ]
        .map(escapeCsv)
        .join(","),
    ),
  ];

  downloadCsv(lines, filename);
}
