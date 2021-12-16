mapboxgl.accessToken =
  "pk.eyJ1IjoiamV6ZGV6IiwiYSI6ImNrd2dtdWJhZTBxMDAyeG1vODJreWxxbjMifQ.MEHP3O86li5jZXRVw9iv2g";

const map = new mapboxgl.Map({
  container: "map", // container element id
  style: "mapbox://styles/mapbox/streets-v11",
  center: [13.4585052, 50.9295798], // initial map center in [lon, lat]
  zoom: 7,
});

map.on("load", () => {
  map.addSource("schools", {
    type: "geojson",
    data: "data/schools.geojson",
  });

  const filterGroup = document.getElementById("filter-group");
  const allCount = document.getElementById("all-count");

  map.addControl(new mapboxgl.NavigationControl(), "bottom-right");
  map.addControl(
    new MapboxGeocoder({
      accessToken: mapboxgl.accessToken,
      mapboxgl: mapboxgl,
      clearAndBlurOnEsc: true,
      collapsed: true,
      enableEventLogging: false,
      countries: "de",
      language: "de",
      bbox: [11.8723081683, 50.1715419914, 15.0377433357, 51.6831408995],
      // Apply a client-side filter to further limit results
      // to those strictly within the Sachsen region.
      filter: function (item) {
        // returns true if item contains Sachsen region
        return item.context.some((i) => {
          // ID is in the form {index}.{id} per https://github.com/mapbox/carmen/blob/master/carmen-geojson.md
          // This example searches for the `region`
          // named `Sachsen`.
          return i.id.split(".").shift() === "region" && i.text === "Sachsen";
        });
      },
    }),
    "bottom-left"
  );
  // Get the current date as UTC to compare it to the validity upper bound
  const now = new Date(new Date().toUTCString().substr(0, 25));
  const epoch_today = now.setUTCHours(0, 0, 0, 0) / 1000;

  const layers = [
    {
      id: "schools-new",
      name: "neu hinzugefügt",
      filter: ["==", "recently_added", true],
      color: "#c42d3f",
      featureCount: undefined,
    },
    {
      id: "schools-recent",
      name: "aktuell gültig",
      filter: [
        "all",
        [">=", "epoch_valid_to", epoch_today],
      ],
      color: "#0d3a35",
      featureCount: undefined,
    },
    {
      id: "schools-expired",
      name: "abgelaufen",
      filter: [
        "all",
        ["==", "recently_added", false],
        ["<", "epoch_valid_to", epoch_today],
      ],
      color: "grey",
      visible: false,
      featureCount: undefined,
    },
  ];

  // add layers in reverse order, (for z index of dots)
  layers.reverse().forEach(function (layer) {
    map.addLayer({
      id: layer.id,
      type: "circle",
      source: "schools",
      paint: {
        "circle-stroke-color": "white",
        "circle-stroke-width": 1,
        "circle-color": layer.color,
      },
      filter: layer.filter,
    });

    map.setLayoutProperty(
      layer.id,
      "visibility",
      layer.visible === false ? "none" : "visible"
    );

    // Create a popup, but don't add it to the map yet.
    const popup = new mapboxgl.Popup({
      closeButton: true,
      closeOnClick: true,
    });

    map.on("click", layer.id, (e) => {
      // Change the cursor style as a UI indicator.
      map.getCanvas().style.cursor = "pointer";

      // Copy coordinates array.
      const coordinates = e.features[0].geometry.coordinates.slice();
      const name = e.features[0].properties.name;
      const address = e.features[0].properties.address;
      const status = e.features[0].properties.status;
      const validity = e.features[0].properties.validity;
      const url = e.features[0].properties.url;
      const recently_added = e.features[0].properties.recently_added;
      // Ensure that if the map is zoomed out such that multiple
      // copies of the feature are visible, the popup appears
      // over the copy being pointed to.
      while (Math.abs(e.lngLat.lng - coordinates[0]) > 180) {
        coordinates[0] += e.lngLat.lng > coordinates[0] ? 360 : -360;
      }
      // Populate the popup and set its coordinates based on the feature found.
      var popup_html;
      if (recently_added) {
        popup_html = `
                <h3><span class="red">NEU: </span>${name}</h3>
            `;
      } else {
        popup_html = `
                <h3>${name}</h3>
            `;
      }
      popup_html = `${popup_html}
            <p>${address}</p>
            <dl>
                <dt>Status</dt><dd>${status}</dd>
                <dt>Gültig</dt><dd>${validity}</dd>
        `;
      if (typeof url !== "undefined") {
        popup_html = `${popup_html}
                <dt>Download</dt>
                <dd><a href="${url}" rel="noopener noreferrer" target="_blank">Bekanntmachung</a> (PDF, Link zum Sächsischen Staatsministerium für Kultus)</dd>
            `;
      }
      popup_html = `${popup_html}</dl>`;
      popup.setLngLat(coordinates).setHTML(popup_html).addTo(map);
    });

    // Change the cursor to a pointer when the mouse is over the places layer.
    map.on("mouseenter", layer.id, () => {
      map.getCanvas().style.cursor = "pointer";
    });

    // Change it back to a pointer when it leaves.
    map.on("mouseleave", layer.id, () => {
      map.getCanvas().style.cursor = "";
    });
  });

  map.once('idle', () => {
    // map.querySourceFeatures(...) returns values only after the map is loaded
    // and layers have been loaded by the map obj.
    const allSchools = map.querySourceFeatures("schools");
    const allUrls = new Set(allSchools.map(f => f.properties.url));
    allCount.appendChild(document.createTextNode(` (${allUrls.size} insgesamt)`));

    layers.forEach(function (layer) {
      const features = map.querySourceFeatures("schools", {
        validate: true,
        filter: layer.filter
      });

      // Somehow, querySourceFeatures returns many duplicates. Hence,
      // count them only once using a set.
      const urls = new Set(features.map(f => f.properties.url));
      layer.featureCount = urls.size;

      // Add checkbox and label elements for the layer.
      const input = document.createElement("input");
      input.type = "checkbox";
      input.id = layer.id;
      input.checked = !(layer.visible === false);
      filterGroup.appendChild(input);

      const label = document.createElement("label");
      label.setAttribute("for", layer.id);
      filterGroup.appendChild(label);

      const span = document.createElement("span");
      span.setAttribute("class", "circle");
      // ugh... what a mess!
      span.setAttribute("style", `background-color:${layer.color};`);
      label.appendChild(document.createTextNode(" "));
      label.appendChild(span);
      label.appendChild(document.createTextNode(" "));
      label.appendChild(document.createTextNode(`${layer.name} (${layer.featureCount})`));

      // When the checkbox changes, update the visibility of the layer.
      input.addEventListener("change", (e) => {
        map.setLayoutProperty(
          layer.id,
          "visibility",
          e.target.checked ? "visible" : "none"
        );
      });

    });
  });

});

