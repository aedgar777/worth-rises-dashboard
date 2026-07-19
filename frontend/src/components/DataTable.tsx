import { useEffect, useMemo, useState } from "react";
import { fetchFacilities, fetchFacilityStates } from "../api";
import type { MatchedRate, ProviderFacility } from "../types";
import { downloadResultsCsv, downloadUnmatchedCsv } from "../utils/exportCsv";
import { formatRate } from "../utils/geo";
import { formatJurisdiction, getStateName } from "../utils/jurisdiction";

interface DataTableProps {
  results: MatchedRate[];
  uploadId: number;
}

function sortStateRows(rows: MatchedRate[]): MatchedRate[] {
  return [...rows].sort((a, b) =>
    getStateName(a.state).localeCompare(getStateName(b.state)),
  );
}

function sortCountyRows(rows: MatchedRate[]): MatchedRate[] {
  return [...rows].sort((a, b) => (a.county ?? "").localeCompare(b.county ?? ""));
}

function sortFacilities(rows: ProviderFacility[]): ProviderFacility[] {
  return [...rows].sort((a, b) => {
    const stateOrder = getStateName(a.state).localeCompare(getStateName(b.state));
    if (stateOrder !== 0) {
      return stateOrder;
    }
    return a.facility_name.localeCompare(b.facility_name);
  });
}

function JurisdictionTable({
  title,
  rows,
  emptyMessage,
}: {
  title: string;
  rows: MatchedRate[];
  emptyMessage: string;
}) {
  return (
    <div className="table-section">
      <h4>{title}</h4>
      {rows.length === 0 ? (
        <p className="hint">{emptyMessage}</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Jurisdiction</th>
              <th>In-State</th>
              <th>Out-of-State</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id}>
                <td>{formatJurisdiction(row)}</td>
                <td>{formatRate(row.in_state_rate)}</td>
                <td>{formatRate(row.out_of_state_rate)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function FacilityTable({
  rows,
  emptyMessage,
}: {
  rows: ProviderFacility[];
  emptyMessage: string;
}) {
  return (
    <div className="table-section">
      <h4>Provider facilities</h4>
      {rows.length === 0 ? (
        <p className="hint">{emptyMessage}</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>State</th>
              <th>Facility</th>
              <th>Address</th>
              <th>In-State</th>
              <th>Out-of-State</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id}>
                <td>{getStateName(row.state)}</td>
                <td>{row.facility_name}</td>
                <td>{row.facility_address ?? "—"}</td>
                <td>{formatRate(row.in_state_rate)}</td>
                <td>{formatRate(row.out_of_state_rate)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export function DataTable({ results, uploadId }: DataTableProps) {
  const matched = useMemo(
    () => results.filter((row) => row.match_status === "matched"),
    [results],
  );
  const stateRows = sortStateRows(
    matched.filter((row) => row.jurisdiction_type === "state"),
  );

  const matchedStateOptions = useMemo(
    () => [...new Set(matched.map((row) => row.state))].sort(),
    [matched],
  );

  const [facilityStates, setFacilityStates] = useState<string[]>([]);
  const [selectedState, setSelectedState] = useState<string>("");
  const [allFacilities, setAllFacilities] = useState<ProviderFacility[]>([]);
  const [allFacilitiesLoading, setAllFacilitiesLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;

    fetchFacilityStates(uploadId)
      .then((states) => {
        if (cancelled) {
          return;
        }
        const options = states.length > 0 ? states : matchedStateOptions;
        setFacilityStates(options);
        setSelectedState((current) =>
          current && options.includes(current) ? current : (options[0] ?? ""),
        );
      })
      .catch(() => {
        if (!cancelled) {
          setFacilityStates(matchedStateOptions);
          setSelectedState(matchedStateOptions[0] ?? "");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [uploadId, matchedStateOptions]);

  useEffect(() => {
    let cancelled = false;
    setAllFacilitiesLoading(true);

    fetchFacilities(uploadId)
      .then((rows) => {
        if (!cancelled) {
          setAllFacilities(sortFacilities(rows));
        }
      })
      .catch(() => {
        if (!cancelled) {
          setAllFacilities([]);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setAllFacilitiesLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [uploadId]);

  const countyRows = useMemo(
    () =>
      sortCountyRows(
        matched.filter(
          (row) =>
            row.jurisdiction_type === "county" && row.state === selectedState,
        ),
      ),
    [matched, selectedState],
  );

  const selectedStateLabel = selectedState ? getStateName(selectedState) : "";
  const pendingCount = results.filter(
    (row) => row.match_status === "review" || row.match_status === "unmatched",
  ).length;

  return (
    <div className="table-panel">
      <div className="table-header">
        <div>
          <h3>Matched rates</h3>
          <p className="hint table-header-hint">
            Tables show matched jurisdictions and every raw provider facility from
            your upload. Use the downloads for cleaned matched rows or unmatched
            and review rows with reasons.
          </p>
        </div>
        <div className="table-header-actions">
          <button
            type="button"
            className="secondary-button"
            onClick={() => downloadResultsCsv(results)}
          >
            Download cleaned list
          </button>
          <button
            type="button"
            className="secondary-button"
            onClick={() => downloadUnmatchedCsv(results)}
            disabled={pendingCount === 0}
          >
            Download unmatched list
          </button>
        </div>
      </div>

      {matched.length === 0 ? (
        <p className="hint">No matched jurisdictions yet.</p>
      ) : (
        <JurisdictionTable
          title="States"
          rows={stateRows}
          emptyMessage="No matched state jurisdictions yet."
        />
      )}

      <FacilityTable
        rows={allFacilitiesLoading ? [] : allFacilities}
        emptyMessage={
          allFacilitiesLoading
            ? "Loading provider facilities…"
            : "No provider facilities found for this upload."
        }
      />

      {matched.length > 0 && (
        <>
          <div className="state-filter">
            <label htmlFor="state-select" className="state-filter-label">
              Select a state
            </label>
            <p className="hint state-filter-hint">
              Use this dropdown to view matched county jurisdictions for that
              state.
            </p>
            <select
              id="state-select"
              className="state-select"
              value={selectedState}
              onChange={(event) => setSelectedState(event.target.value)}
              disabled={facilityStates.length === 0}
            >
              {facilityStates.length === 0 ? (
                <option value="">No states available</option>
              ) : (
                facilityStates.map((state) => (
                  <option key={state} value={state}>
                    {getStateName(state)}
                  </option>
                ))
              )}
            </select>
          </div>

          {selectedState && (
            <JurisdictionTable
              title={`${selectedStateLabel} counties`}
              rows={countyRows}
              emptyMessage={`No county-level data for ${selectedStateLabel}.`}
            />
          )}
        </>
      )}
    </div>
  );
}
