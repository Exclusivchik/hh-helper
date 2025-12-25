// ammap.js — ТВОЯ логика, без переписывания

let chart = null;
let polygonSeries = null;
let root = null;

let regionsData = [];
let isZoomedToRegion = false;
let initialMapState = null;
let selectedRegionId = null;

function initAmMap(regions) {
    regionsData = regions || [];

    am5.ready(function() {
        root = am5.Root.new("chartdiv", {
            autoResize: true
        });

        root.setThemes([]);

        const projection = am5map.geoMercator();

        chart = root.container.children.push(
            am5map.MapChart.new(root, {
                projection,
                panX: "none",
                panY: "none",
                zoomLevel: 0.75,
                minZoomLevel: 0.75,
                maxZoomLevel: 8,
                homeGeoPoint: { latitude: 60, longitude: 100 }
            })
        );

        polygonSeries = chart.series.push(
            am5map.MapPolygonSeries.new(root, {
                geoJSON: am5geodata_russiaLow,
                valueField: "value",
                calculateAggregates: true
            })
        );

        polygonSeries.mapPolygons.template.setAll({
            tooltipText: "{name}",
            interactive: true,
            cursorOverStyle: "pointer",
            stroke: am5.color(0xffffff),
            strokeWidth: 1,
            fill: am5.color(0x3498db)
        });

        polygonSeries.mapPolygons.template.states.create("hover", {
            fill: am5.color(0xFFA726),
            strokeWidth: 2
        });

        polygonSeries.data.setAll(regionsData);

        initialMapState = {
            longitude: 100,
            latitude: 65,
            zoomLevel: 0.75
        };

        polygonSeries.events.once("inited", function () {
            chart.goHome();
        });

        polygonSeries.mapPolygons.each(function(polygon) {
            polygon.events.on("click", function(ev) {
                if (isZoomedToRegion) return;

                const data = ev.target.dataItem.dataContext;
                if (!data) return;

                polygonSeries.mapPolygons.each(p => {
                    p.set("fillOpacity", p === polygon ? 1 : 0.3);
                    p.set("interactive", false);
                });

                polygon.set("fill", am5.color(0x27ae60));
                polygon.set("strokeWidth", 3);

                const centroid = polygon.visualCentroid();
                if (centroid) {
                    chart.zoomToGeoPoint(
                        { longitude: centroid.longitude, latitude: centroid.latitude },
                        4,
                        true,
                        600
                    );
                }

                isZoomedToRegion = true;
                selectedRegionId = data.id;

                document.getElementById('backButton').style.display = 'block';
                document.getElementById('detailsButton').style.display = 'block';
            });
        });

        document.querySelector('.loading')?.remove();
        initRegionSearch();
    });
}

function goBackToMap() {
    polygonSeries.mapPolygons.each(p => {
        p.remove("fill");
        p.set("fillOpacity", 1);
        p.set("interactive", true);
        p.set("strokeWidth", 1);
    });

    isZoomedToRegion = false;
    selectedRegionId = null;

    chart.zoomToGeoPoint(
        { longitude: initialMapState.longitude, latitude: initialMapState.latitude },
        initialMapState.zoomLevel,
        true,
        600
    );

    document.getElementById('backButton').style.display = 'none';
    document.getElementById('detailsButton').style.display = 'none';
}

function goToRegionDetails() {
    if (selectedRegionId) {
        window.location.href = `/ammap/region/${selectedRegionId}`;
    }
}

/* === ПОИСК — ТВОЙ ЖЕ === */
function initRegionSearch() {
    const input = document.getElementById('regionSearch');
    const results = document.getElementById('searchResults');

    input.addEventListener('input', function () {
        const q = this.value.toLowerCase().trim();
        if (!q) {
            results.classList.remove('active');
            results.innerHTML = '';
            return;
        }

        const matches = regionsData.filter(r =>
            r.name.toLowerCase().includes(q)
        ).slice(0, 10);

        results.innerHTML = matches.map(r => `
            <div class="search-result-item" onclick="selectRegion('${r.id}')">
                ${r.name}
            </div>
        `).join('');

        results.classList.add('active');
    });
}

function selectRegion(regionId) {
    polygonSeries.mapPolygons.each(p => {
        if (p.dataItem.dataContext.id === regionId) {
            p.events.dispatch("click");
        }
    });
}

window.initAmMap = initAmMap;
window.goBackToMap = goBackToMap;
window.goToRegionDetails = goToRegionDetails;
window.selectRegion = selectRegion;
