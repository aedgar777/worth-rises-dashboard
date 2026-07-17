import type { MatchedRate } from "../types";

export type RateMode = "in_state" | "out_of_state";

export interface RateBucket {
  min: number;
  max: number;
  color: string;
  label: string;
}

/** Fallback per-minute range from Worth Rises test data before any upload. */
export const SAMPLE_RATE_MIN = 0.01;
export const SAMPLE_RATE_MAX = 0.21;

const BUCKET_COLORS = [
  "#86efac",
  "#bef264",
  "#fde047",
  "#fdba74",
  "#fb923c",
  "#ef4444",
];

export const NO_DATA_COLOR = "#e2e8f0";

const DEFAULT_BUCKET_COUNT = 6;

function roundToCents(value: number): number {
  return Math.round(value * 100) / 100;
}

function floorToCents(value: number): number {
  return Math.floor(value * 100) / 100;
}

function ceilToCents(value: number): number {
  return Math.ceil(value * 100) / 100;
}

function formatRateAmount(value: number): string {
  return roundToCents(value).toFixed(2);
}

function formatBucketLabel(min: number, max: number, isLast: boolean): string {
  if (isLast) {
    return `$${formatRateAmount(min)}+`;
  }
  return `$${formatRateAmount(min)} – $${formatRateAmount(max)}`;
}

export function collectRatesFromResults(results: MatchedRate[]): number[] {
  const rates: number[] = [];

  for (const row of results) {
    if (row.match_status === "unmatched") {
      continue;
    }
    if (row.in_state_rate != null) {
      rates.push(row.in_state_rate);
    }
    if (row.out_of_state_rate != null) {
      rates.push(row.out_of_state_rate);
    }
  }

  return rates;
}

export function buildRateBuckets(
  rates: number[],
  bucketCount = DEFAULT_BUCKET_COUNT,
): RateBucket[] {
  const rawMin = rates.length ? Math.min(...rates) : SAMPLE_RATE_MIN;
  const rawMax = rates.length ? Math.max(...rates) : SAMPLE_RATE_MAX;
  const min = floorToCents(rawMin);
  const max = ceilToCents(rawMax);
  const span = max - min || 0.01;
  const step = span / bucketCount;

  return Array.from({ length: bucketCount }, (_, index) => {
    const bucketMin = roundToCents(min + step * index);
    const bucketMax =
      index === bucketCount - 1 ? Infinity : roundToCents(min + step * (index + 1));
    return {
      min: bucketMin,
      max: bucketMax,
      color: BUCKET_COLORS[index] ?? BUCKET_COLORS[BUCKET_COLORS.length - 1],
      label: formatBucketLabel(
        bucketMin,
        index === bucketCount - 1 ? bucketMin : bucketMax,
        index === bucketCount - 1,
      ),
    };
  });
}

export function rateToColor(
  rate: number | null | undefined,
  buckets: RateBucket[],
): string {
  if (rate == null || Number.isNaN(rate)) {
    return NO_DATA_COLOR;
  }

  for (const bucket of buckets) {
    if (rate >= bucket.min && rate < bucket.max) {
      return bucket.color;
    }
  }

  return buckets[buckets.length - 1]?.color ?? NO_DATA_COLOR;
}

export function pickRate(
  row: { in_state_rate: number | null; out_of_state_rate: number | null },
  mode: RateMode,
): number | null {
  return mode === "in_state" ? row.in_state_rate : row.out_of_state_rate;
}

export function resolveCountyRateRow(
  countyRates: Map<string, MatchedRate>,
  stateRates: Map<string, MatchedRate>,
  stateAbbr: string,
  countyName: string,
  countyKeyFn: (state: string, county: string) => string,
): MatchedRate | null {
  const key = countyKeyFn(stateAbbr, countyName);
  const countyRow = countyRates.get(key);
  if (countyRow && countyRow.match_status !== "unmatched") {
    return countyRow;
  }

  const stateRow = stateRates.get(stateAbbr.toUpperCase());
  if (stateRow) {
    return stateRow;
  }

  return null;
}
