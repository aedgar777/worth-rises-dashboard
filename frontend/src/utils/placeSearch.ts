export function extractCountyAndState(
  components: google.maps.GeocoderAddressComponent[],
): { county: string; state: string } | null {
  let county = "";
  let state = "";

  for (const component of components) {
    if (component.types.includes("administrative_area_level_1")) {
      state = component.short_name;
    }
    if (component.types.includes("administrative_area_level_2")) {
      county = component.long_name;
    }
  }

  if (!state) {
    return null;
  }

  if (!county) {
    for (const component of components) {
      if (
        component.types.includes("locality") ||
        component.types.includes("sublocality") ||
        component.types.includes("neighborhood")
      ) {
        county = component.long_name;
        break;
      }
    }
  }

  if (!county) {
    return null;
  }

  return { county, state };
}

export function isBelowStateLevel(components: google.maps.GeocoderAddressComponent[]): boolean {
  const hasState = components.some((component) =>
    component.types.includes("administrative_area_level_1"),
  );
  const hasSubState = components.some((component) =>
    component.types.some((type) =>
      [
        "administrative_area_level_2",
        "administrative_area_level_3",
        "locality",
        "sublocality",
        "neighborhood",
        "postal_code",
        "route",
        "street_address",
        "premise",
        "establishment",
        "point_of_interest",
      ].includes(type),
    ),
  );

  return hasState && hasSubState;
}
