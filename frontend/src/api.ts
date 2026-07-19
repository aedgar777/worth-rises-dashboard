import axios from "axios";
import type { MatchedRate, ProcessResponse, ProviderFacility, Summary } from "./types";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8080";

const api = axios.create({
  baseURL: API_URL,
  timeout: 300_000,
});

export async function processCsv(
  rawProviderFile: File,
  onProgress?: (percent: number) => void,
): Promise<ProcessResponse> {
  const form = new FormData();
  form.append("raw_provider", rawProviderFile);
  const { data } = await api.post<ProcessResponse>("/api/process", form, {
    onUploadProgress: (event) => {
      if (!onProgress) {
        return;
      }
      if (event.total) {
        onProgress(Math.round((event.loaded / event.total) * 70));
      } else if (event.loaded > 0) {
        onProgress(35);
      }
    },
  });
  onProgress?.(95);
  return data;
}

export async function fetchResults(uploadId: number): Promise<MatchedRate[]> {
  const { data } = await api.get<MatchedRate[]>(`/api/uploads/${uploadId}/results`);
  return data;
}

export async function fetchSummary(uploadId: number): Promise<Summary> {
  const { data } = await api.get<Summary>(`/api/uploads/${uploadId}/summary`);
  return data;
}

export async function fetchFacilityStates(uploadId: number): Promise<string[]> {
  const { data } = await api.get<string[]>(`/api/uploads/${uploadId}/facility-states`);
  return data;
}

export async function fetchFacilities(
  uploadId: number,
  state?: string,
): Promise<ProviderFacility[]> {
  const { data } = await api.get<ProviderFacility[]>(
    `/api/uploads/${uploadId}/facilities`,
    { params: state ? { state } : undefined },
  );
  return data;
}
