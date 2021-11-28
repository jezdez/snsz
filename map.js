mapboxgl.accessToken = 'pk.eyJ1IjoiamV6ZGV6IiwiYSI6ImNrd2dtdWJhZTBxMDAyeG1vODJreWxxbjMifQ.MEHP3O86li5jZXRVw9iv2g';

const map = new mapboxgl.Map({
    container: 'map', // container element id
    style: 'mapbox://styles/mapbox/streets-v11',
    center: [13.4585052, 50.9295798], // initial map center in [lon, lat]
    zoom: 7
});

map.on('load', () => {
    map.addSource('schools', {
        type: 'geojson',
        data: 'data/schools.geojson'
    });
    map.addControl(
        new MapboxGeocoder({
            accessToken: mapboxgl.accessToken,
            mapboxgl: mapboxgl,
            clearAndBlurOnEsc: true,
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
                    return (
                        i.id.split('.').shift() === 'region' &&
                        i.text === 'Sachsen'
                    );
                });
            },

        })
    );
    map.addControl(new mapboxgl.NavigationControl());
    map.addLayer(
        {
            'id': 'schools',
            'type': 'circle',
            'source': 'schools',
            'paint': {
                'circle-stroke-color': 'white',
                'circle-stroke-width': 1,
                'circle-color': [
                    'case',
                    ['boolean', ['get', 'new'], false],
                    '#c42d3f',
                    '#0D3A35'
                ]
            }
        }
    );

    // Create a popup, but don't add it to the map yet.
    const popup = new mapboxgl.Popup({
        closeButton: true,
        closeOnClick: true
    });

    map.on('click', 'schools', (e) => {
        // Change the cursor style as a UI indicator.
        map.getCanvas().style.cursor = 'pointer';

        // Copy coordinates array.
        const coordinates = e.features[0].geometry.coordinates.slice();
        const name = e.features[0].properties.name;
        const address = e.features[0].properties.address;
        const status = e.features[0].properties.status;
        const validity = e.features[0].properties.validity;
        const url = e.features[0].properties.url;
        const new_ = e.features[0].properties.new;
        // Ensure that if the map is zoomed out such that multiple
        // copies of the feature are visible, the popup appears
        // over the copy being pointed to.
        while (Math.abs(e.lngLat.lng - coordinates[0]) > 180) {
            coordinates[0] += e.lngLat.lng > coordinates[0] ? 360 : -360;
        }
        // Populate the popup and set its coordinates based on the feature found.
        var popup_html;
        if (new_) {
            popup_html = `
                <h2><span class="red">NEU: </span>${name}</h2>
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
    map.on('mouseenter', 'schools', () => {
        map.getCanvas().style.cursor = 'pointer';
    });

    // Change it back to a pointer when it leaves.
    map.on('mouseleave', 'schools', () => {
        map.getCanvas().style.cursor = '';
    });
});
