export interface ProviderFacility {
  id: number;
  state: string;
  county: string | null;
  facility_id: string | null;
  facility_name: string;
  provider: string | null;
  in_state_rate: number | null;
  out_of_state_rate: number | null;
  facility_address: string | null;
}

export interface MatchedRate {
  id: number;
  jurisdiction_type: string;
  state: string;
  county: string | null;
  facility_name: string | null;
  provider: string | null;
  in_state_rate: number | null;
  out_of_state_rate: number | null;
  match_status: "matched" | "review" | "unmatched";
  match_confidence: number;
  notes: string | null;
  facility_rules: string | null;
  latitude: number | null;
  longitude: number | null;
  place_id: string | null;
  place_description: string | null;
}

export interface ProcessResponse {
  upload_id: number;
  jurisdiction_count: number;
  matched_count: number;
  review_count: number;
  unmatched_count: number;
}

export interface Summary {
  total: number;
  matched: number;
  review: number;
  unmatched: number;
  avg_in_state_rate: number | null;
  avg_out_of_state_rate: number | null;
  by_state: Array<{
    state: string;
    matched: number;
    review: number;
    unmatched: number;
    avg_in_state: number | null;
  }>;
}
