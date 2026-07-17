import { useCallback, useEffect, useRef } from "react";
import { Autocomplete } from "@react-google-maps/api";
import { extractCountyAndState, isBelowStateLevel } from "../utils/placeSearch";

interface PlaceSearchProps {
  onCountyFound: (county: string, state: string) => void;
  onSearchError?: (message: string) => void;
}

export function PlaceSearch({ onCountyFound, onSearchError }: PlaceSearchProps) {
  const autocompleteRef = useRef<google.maps.places.Autocomplete | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const geocoderRef = useRef<google.maps.Geocoder | null>(null);

  const resolveComponents = useCallback(
    (components: google.maps.GeocoderAddressComponent[]) => {
      if (!isBelowStateLevel(components)) {
        onSearchError?.("Pick a location below the state level (county, city, or address).");
        return;
      }

      const match = extractCountyAndState(components);
      if (!match) {
        onSearchError?.("Could not determine a county from that place.");
        return;
      }

      onCountyFound(match.county, match.state);
    },
    [onCountyFound, onSearchError],
  );

  const geocodeQuery = useCallback(
    async (query: string) => {
      const trimmed = query.trim();
      if (!trimmed) {
        return;
      }

      if (!geocoderRef.current) {
        geocoderRef.current = new google.maps.Geocoder();
      }

      try {
        const response = await geocoderRef.current.geocode({
          address: trimmed,
          componentRestrictions: { country: "us" },
        });

        const result = response.results[0];
        if (!result?.address_components?.length) {
          onSearchError?.("No results found for that search.");
          return;
        }

        resolveComponents(result.address_components);
      } catch {
        onSearchError?.("Search failed. Try another location.");
      }
    },
    [onSearchError, resolveComponents],
  );

  const handlePlaceChanged = useCallback(() => {
    const place = autocompleteRef.current?.getPlace();
    if (place?.address_components?.length) {
      resolveComponents(place.address_components);
      return;
    }

    const query = inputRef.current?.value ?? "";
    if (query.trim()) {
      void geocodeQuery(query);
    }
  }, [geocodeQuery, resolveComponents]);

  useEffect(() => {
    const autocomplete = autocompleteRef.current;
    if (!autocomplete) {
      return;
    }

    const listener = autocomplete.addListener("place_changed", handlePlaceChanged);
    return () => {
      google.maps.event.removeListener(listener);
    };
  }, [handlePlaceChanged]);

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    const place = autocompleteRef.current?.getPlace();
    if (place?.address_components?.length) {
      resolveComponents(place.address_components);
      return;
    }

    void geocodeQuery(inputRef.current?.value ?? "");
  };

  return (
    <form className="place-search" onSubmit={handleSubmit}>
      <Autocomplete
        onLoad={(instance) => {
          autocompleteRef.current = instance;
        }}
        onUnmount={() => {
          autocompleteRef.current = null;
        }}
        options={{
          componentRestrictions: { country: "us" },
          fields: ["address_components", "geometry", "name"],
        }}
      >
        <input
          ref={inputRef}
          type="search"
          className="place-search-input"
          placeholder="Search place or address…"
          aria-label="Search place or address"
        />
      </Autocomplete>
    </form>
  );
}
