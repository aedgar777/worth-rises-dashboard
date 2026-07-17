import { useCallback, useState } from "react";
import { fetchResults, processCsv } from "../api";
import type { MatchedRate } from "../types";

export function useDashboard() {
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [uploadId, setUploadId] = useState<number | null>(null);
  const [results, setResults] = useState<MatchedRate[]>([]);
  const [view, setView] = useState<"map" | "table">("map");

  const handleUpload = useCallback(async (rawProvider: File) => {
    setLoading(true);
    setProgress(0);
    setError(null);
    try {
      const response = await processCsv(rawProvider, setProgress);
      setUploadId(response.upload_id);
      const rows = await fetchResults(response.upload_id);
      setProgress(100);
      logUnmatched(rows);
      setResults(rows);
      setView("map");
    } catch (err) {
      const message =
        axiosErrorMessage(err) ?? "Upload failed. Check your CSV files and API connection.";
      setError(message);
    } finally {
      setLoading(false);
      setProgress(0);
    }
  }, []);

  return {
    loading,
    progress,
    error,
    uploadId,
    results,
    view,
    setView,
    handleUpload,
  };
}

function logUnmatched(rows: MatchedRate[]) {
  const unmatched = rows.filter((row) => row.match_status === "unmatched");
  if (!unmatched.length) {
    return;
  }

  console.group(`Unmatched jurisdictions (${unmatched.length})`);
  for (const row of unmatched) {
    const label =
      row.facility_name ??
      (row.county
        ? `${row.county} County, ${row.state}`
        : `${row.state} (${row.jurisdiction_type})`);
    console.log(label, "—", row.notes ?? "No matching facility found");
  }
  console.groupEnd();
}

function axiosErrorMessage(err: unknown): string | null {
  if (typeof err === "object" && err !== null && "response" in err) {
    const response = (err as { response?: { data?: { detail?: string } } }).response;
    if (response?.data?.detail) return String(response.data.detail);
  }
  if (err instanceof Error) return err.message;
  return null;
}
