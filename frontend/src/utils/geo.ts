export const COUNTY_GEOJSON_URL =
  "https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json";

/** Two-digit FIPS code → USPS state abbreviation */
export const FIPS_TO_STATE: Record<string, string> = {
  "01": "AL",
  "02": "AK",
  "04": "AZ",
  "05": "AR",
  "06": "CA",
  "08": "CO",
  "09": "CT",
  "10": "DE",
  "11": "DC",
  "12": "FL",
  "13": "GA",
  "15": "HI",
  "16": "ID",
  "17": "IL",
  "18": "IN",
  "19": "IA",
  "20": "KS",
  "21": "KY",
  "22": "LA",
  "23": "ME",
  "24": "MD",
  "25": "MA",
  "26": "MI",
  "27": "MN",
  "28": "MS",
  "29": "MO",
  "30": "MT",
  "31": "NE",
  "32": "NV",
  "33": "NH",
  "34": "NJ",
  "35": "NM",
  "36": "NY",
  "37": "NC",
  "38": "ND",
  "39": "OH",
  "40": "OK",
  "41": "OR",
  "42": "PA",
  "44": "RI",
  "45": "SC",
  "46": "SD",
  "47": "TN",
  "48": "TX",
  "49": "UT",
  "50": "VT",
  "51": "VA",
  "53": "WA",
  "54": "WV",
  "55": "WI",
  "56": "WY",
};

export const STATE_FIPS: Record<string, string> = Object.fromEntries(
  Object.entries(FIPS_TO_STATE).map(([fips, abbr]) => [abbr, fips]),
);

export function normalizeCountyName(name: string): string {
  return name
    .replace(/\s+County$/i, "")
    .replace(/\./g, "")
    .replace(/\s+/g, " ")
    .trim()
    .toUpperCase()
    .replace(/^ST\s/, "SAINT ")
    .replace(/^ST\.\s/, "SAINT ");
}

export function countyKey(state: string, county: string): string {
  return `${state.toUpperCase()}-${normalizeCountyName(county)}`;
}

export function formatRate(value: number | null | undefined): string {
  if (value == null) {
    return "—";
  }
  return `$${(Math.round(value * 100) / 100).toFixed(2)}`;
}

export function ratesDiffer(
  a: number | null | undefined,
  b: number | null | undefined,
  epsilon = 0.001,
): boolean {
  if (a == null && b == null) {
    return false;
  }
  if (a == null || b == null) {
    return true;
  }
  return Math.abs(a - b) > epsilon;
}

export interface CountyGeoFeature {
  id: string;
  name: string;
  stateAbbr: string;
}

export function findCountyFips(
  features: CountyGeoFeature[],
  county: string,
  stateAbbr: string,
): string | null {
  const target = normalizeCountyName(county);
  const stateUpper = stateAbbr.toUpperCase();
  for (const feature of features) {
    if (
      feature.stateAbbr === stateUpper &&
      normalizeCountyName(feature.name) === target
    ) {
      return feature.id;
    }
  }
  return null;
}
