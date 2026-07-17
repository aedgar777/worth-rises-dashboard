import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { GoogleMap, InfoWindow, useJsApiLoader } from "@react-google-maps/api";
import type { MatchedRate } from "../types";
import { PlaceSearch } from "./PlaceSearch";
import {
  COUNTY_GEOJSON_URL,
  FIPS_TO_STATE,
  countyKey,
  findCountyFips,
  formatRate,
  ratesDiffer,
  type CountyGeoFeature,
} from "../utils/geo";
import {
  NO_DATA_COLOR,
  buildRateBuckets,
  collectRatesFromResults,
  pickRate,
  rateToColor,
  resolveCountyRateRow,
  type RateMode,
} from "../utils/rateColors";

interface MapViewProps {
  results: MatchedRate[];
}

interface CountyPopup {
  position: google.maps.LatLng;
  countyName: string;
  stateAbbr: string;
  countyResult: MatchedRate | null;
  stateResult: MatchedRate | null;
}

interface GeoJsonFeature {
  type: string;
  id?: string | number;
  properties?: Record<string, unknown>;
  geometry: unknown;
}

interface GeoJsonCollection {
  type: string;
  features: GeoJsonFeature[];
}

const MAP_CONTAINER_STYLE = { width: "100%", height: "520px", borderRadius: "12px" };
const MAP_LIBRARIES: ("places")[] = ["places"];

let geoJsonCache: GeoJsonCollection | null = null;

async function loadGeoJson(): Promise<GeoJsonCollection> {
  if (!geoJsonCache) {
    const response = await fetch(COUNTY_GEOJSON_URL);
    geoJsonCache = (await response.json()) as GeoJsonCollection;
  }
  return geoJsonCache;
}

function buildCountyFeatures(collection: GeoJsonCollection): CountyGeoFeature[] {
  const features: CountyGeoFeature[] = [];
  for (const feature of collection.features) {
    const stateFips = String((feature.properties as { STATE?: string })?.STATE ?? "");
    const id = String(feature.id ?? "");
    const name = String((feature.properties as { NAME?: string })?.NAME ?? "");
    const stateAbbr = FIPS_TO_STATE[stateFips] ?? "";
    if (!id || !name || !stateAbbr) {
      continue;
    }
    features.push({ id, name, stateAbbr });
  }
  return features;
}

export function MapView({ results }: MapViewProps) {
  const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY ?? "";
  const { isLoaded, loadError } = useJsApiLoader({
    googleMapsApiKey: apiKey,
    libraries: MAP_LIBRARIES,
  });

  const mapRef = useRef<google.maps.Map | null>(null);
  const dataLayerRef = useRef<google.maps.Data | null>(null);
  const featuresRef = useRef<CountyGeoFeature[]>([]);
  const pendingSearchRef = useRef<{ county: string; state: string } | null>(null);

  const [geoReady, setGeoReady] = useState(false);
  const [highlightedFips, setHighlightedFips] = useState<string | null>(null);
  const [popup, setPopup] = useState<CountyPopup | null>(null);
  const [rateMode, setRateMode] = useState<RateMode>("in_state");
  const [searchError, setSearchError] = useState<string | null>(null);

  const stateRates = useMemo(() => {
    const map = new Map<string, MatchedRate>();
    for (const row of results) {
      if (row.jurisdiction_type === "state" && row.match_status !== "unmatched") {
        map.set(row.state.toUpperCase(), row);
      }
    }
    return map;
  }, [results]);

  const countyRates = useMemo(() => {
    const map = new Map<string, MatchedRate>();
    for (const row of results) {
      if (
        row.jurisdiction_type === "county" &&
        row.county &&
        row.match_status !== "unmatched"
      ) {
        map.set(countyKey(row.state, row.county), row);
      }
    }
    return map;
  }, [results]);

  const rateBuckets = useMemo(
    () => buildRateBuckets(collectRatesFromResults(results)),
    [results],
  );

  const countyRatesRef = useRef(countyRates);
  const stateRatesRef = useRef(stateRates);
  countyRatesRef.current = countyRates;
  stateRatesRef.current = stateRates;

  const fipsToRate = useMemo(() => {
    const map = new Map<string, number | null>();
    for (const feature of featuresRef.current) {
      const row = resolveCountyRateRow(
        countyRates,
        stateRates,
        feature.stateAbbr,
        feature.name,
        countyKey,
      );
      map.set(feature.id, row ? pickRate(row, rateMode) : null);
    }
    return map;
  }, [countyRates, stateRates, rateMode, geoReady]);

  const refreshLayerStyle = useCallback(() => {
    const layer = dataLayerRef.current;
    if (!layer) {
      return;
    }

    layer.setStyle((feature) => {
      const fips = String(feature.getId() ?? "");
      const isHighlighted = fips === highlightedFips;
      const rate = fipsToRate.get(fips) ?? null;
      const fillColor = rateToColor(rate, rateBuckets);
      const hasRate = rate != null;

      return {
        fillColor,
        fillOpacity: hasRate ? 0.72 : 0.18,
        strokeColor: isHighlighted ? "#b45309" : hasRate ? "#475569" : "#94a3b8",
        strokeWeight: isHighlighted ? 2.5 : hasRate ? 0.9 : 0.5,
        clickable: true,
      };
    });
  }, [fipsToRate, highlightedFips, rateBuckets]);

  const refreshLayerStyleRef = useRef(refreshLayerStyle);
  refreshLayerStyleRef.current = refreshLayerStyle;

  useEffect(() => {
    refreshLayerStyle();
  }, [refreshLayerStyle, geoReady]);

  useEffect(() => {
    let cancelled = false;

    loadGeoJson()
      .then((collection) => {
        if (cancelled) {
          return;
        }
        featuresRef.current = buildCountyFeatures(collection);
        setGeoReady(true);
      })
      .catch(() => {
        if (!cancelled) {
          featuresRef.current = [];
          setGeoReady(true);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const openCountyPopup = useCallback((fips: string, position: google.maps.LatLng) => {
    const feature = featuresRef.current.find((item) => item.id === fips);
    if (!feature) {
      return;
    }

    const key = countyKey(feature.stateAbbr, feature.name);
    const countyResult = countyRatesRef.current.get(key) ?? null;
    setPopup({
      position,
      countyName: feature.name,
      stateAbbr: feature.stateAbbr,
      countyResult,
      stateResult: stateRatesRef.current.get(feature.stateAbbr) ?? null,
    });
  }, []);

  const openCountyPopupRef = useRef(openCountyPopup);
  openCountyPopupRef.current = openCountyPopup;

  const focusCounty = useCallback(
    (county: string, stateAbbr: string) => {
      setSearchError(null);
      const fips = findCountyFips(featuresRef.current, county, stateAbbr);
      if (!fips) {
        setSearchError(`Could not locate ${county} on the map.`);
        return;
      }

      setHighlightedFips(fips);

      const layer = dataLayerRef.current;
      const map = mapRef.current;
      if (!layer || !map) {
        pendingSearchRef.current = { county, state: stateAbbr };
        return;
      }

      const feature = layer.getFeatureById(fips);
      if (!feature) {
        setSearchError(`County boundary not loaded yet for ${county}, ${stateAbbr}.`);
        return;
      }

      const bounds = new google.maps.LatLngBounds();
      const geometry = feature.getGeometry();
      geometry?.forEachLatLng((latLng) => bounds.extend(latLng));
      if (!bounds.isEmpty()) {
        map.fitBounds(bounds, 48);
        openCountyPopupRef.current(fips, bounds.getCenter());
      }
    },
    [],
  );

  const focusCountyRef = useRef(focusCounty);
  focusCountyRef.current = focusCounty;

  const attachDataLayer = useCallback((map: google.maps.Map) => {
    if (dataLayerRef.current) {
      return;
    }

    if (!featuresRef.current.length) {
      return;
    }

    const layer = new google.maps.Data({ map });
    dataLayerRef.current = layer;

    void loadGeoJson().then((collection) => {
      layer.addGeoJson(collection);
      refreshLayerStyleRef.current();

      layer.addListener("click", (event: google.maps.Data.MouseEvent) => {
        const fips = String(event.feature.getId() ?? "");
        setHighlightedFips(fips);
        openCountyPopupRef.current(fips, event.latLng!);
      });

      if (pendingSearchRef.current) {
        const pending = pendingSearchRef.current;
        pendingSearchRef.current = null;
        window.setTimeout(
          () => focusCountyRef.current(pending.county, pending.state),
          0,
        );
      }
    });
  }, []);

  useEffect(() => {
    if (mapRef.current && geoReady) {
      attachDataLayer(mapRef.current);
    }
  }, [attachDataLayer, geoReady]);

  if (!apiKey) {
    return (
      <div className="map-panel">
        <p className="error">Set VITE_GOOGLE_MAPS_API_KEY to display the Google Map.</p>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="map-panel">
        <p className="error">Failed to load Google Maps.</p>
      </div>
    );
  }

  if (!isLoaded) {
    return (
      <div className="map-panel">
        <p className="hint">Loading map…</p>
      </div>
    );
  }

  return (
    <div className="map-panel">
      <PlaceSearch
        onCountyFound={focusCounty}
        onSearchError={(message) => setSearchError(message)}
      />
      {searchError && <p className="error search-error">{searchError}</p>}

      <div className="map-layout">
        <div className="map-main">
          <GoogleMap
            mapContainerStyle={MAP_CONTAINER_STYLE}
            center={{ lat: 39.8283, lng: -98.5795 }}
            zoom={4}
            options={{ mapTypeControl: false, streetViewControl: false }}
            onLoad={(map) => {
              mapRef.current = map;
              if (geoReady) {
                attachDataLayer(map);
              }
            }}
            onUnmount={() => {
              mapRef.current = null;
              if (dataLayerRef.current) {
                dataLayerRef.current.setMap(null);
                dataLayerRef.current = null;
              }
            }}
          >
            {popup && (
              <InfoWindow
                position={popup.position}
                onCloseClick={() => {
                  setPopup(null);
                  setHighlightedFips(null);
                }}
              >
                <CountyRatePopup popup={popup} />
              </InfoWindow>
            )}
          </GoogleMap>
        </div>

        <aside className="map-sidebar">
          <fieldset className="rate-mode-fieldset">
            <legend>Rate type</legend>
            <label className="rate-mode-option">
              <input
                type="radio"
                name="rate-mode"
                value="in_state"
                checked={rateMode === "in_state"}
                onChange={() => setRateMode("in_state")}
              />
              In-state
            </label>
            <label className="rate-mode-option">
              <input
                type="radio"
                name="rate-mode"
                value="out_of_state"
                checked={rateMode === "out_of_state"}
                onChange={() => setRateMode("out_of_state")}
              />
              Out-of-state
            </label>
          </fieldset>

          <div className="rate-legend">
            <p className="rate-legend-title">Rate ($/min)</p>
            {rateBuckets.map((bucket) => (
              <div key={bucket.label} className="rate-legend-row">
                <span
                  className="rate-legend-swatch"
                  style={{ backgroundColor: bucket.color }}
                />
                <span>{bucket.label}</span>
              </div>
            ))}
            <div className="rate-legend-row">
              <span
                className="rate-legend-swatch"
                style={{ backgroundColor: NO_DATA_COLOR }}
              />
              <span>No matched data</span>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}

function CountyRatePopup({ popup }: { popup: CountyPopup }) {
  const { countyName, stateAbbr, countyResult, stateResult } = popup;
  const countyIn = countyResult?.in_state_rate ?? null;
  const countyOut = countyResult?.out_of_state_rate ?? null;
  const stateIn = stateResult?.in_state_rate ?? null;
  const stateOut = stateResult?.out_of_state_rate ?? null;

  const inDiffers = ratesDiffer(countyIn, stateIn);
  const outDiffers = ratesDiffer(countyOut, stateOut);
  const countySpecific =
    countyResult != null &&
    countyResult.jurisdiction_type === "county" &&
    countyResult.county != null;
  const showBoth = countySpecific && (inDiffers || outDiffers);

  return (
    <div className="map-info">
      <strong>
        {countyName} County, {stateAbbr}
      </strong>
      {countySpecific ? (
        <>
          <p className="rate-section-label">County rates</p>
          <p>In-state: {formatRate(countyIn)}</p>
          <p>Out-of-state: {formatRate(countyOut)}</p>
          {showBoth && (
            <>
              <p className="rate-section-label">State rates</p>
              <p>In-state: {formatRate(stateIn)}</p>
              <p>Out-of-state: {formatRate(stateOut)}</p>
            </>
          )}
        </>
      ) : (
        <>
          <p className="rate-section-label">State rates</p>
          <p>In-state: {formatRate(stateIn)}</p>
          <p>Out-of-state: {formatRate(stateOut)}</p>
          <p className="place-desc">Showing state-level rates for this county.</p>
        </>
      )}
    </div>
  );
}
