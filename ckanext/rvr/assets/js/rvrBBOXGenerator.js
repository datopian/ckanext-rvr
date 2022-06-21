/* Module for handling the spatial querying
 */
this.ckan.module('rvr-bbox-generator', function ($, _) {

    return {
        options: {
            i18n: {},
            style: {
                color: '#F06F64',
                weight: 2,
                opacity: 1,
                fillColor: '#F06F64',
                fillOpacity: 0.1,
                clickable: false
            }
        },
        currentGeoJSON: {},
        spatialFieldId: '',
        initialGeoJSON: {},
        parentDefaultGeoJSON: {},

        initialize: function () {
            $.proxyAll(this, /_on/);
            var corner1 = L.latLng(52.58198281531925, 10.1568603515625);
            var corner2 = L.latLng(49.8122251229721, 4.2132568359375);
            bounds = L.latLngBounds(corner1, corner2);

            // Get the current spatial data
            var initialGeoJSON = this.el.data('currentspatial');
            var spatialFieldId = this.el.data('spatialfield');
            var parentDefaultGeoJSON = this.el.data('parentspatial');

            this.options.default_extent = bounds;
            if (initialGeoJSON['coordinates']) {this.initialGeoJSON = initialGeoJSON;}
            if (parentDefaultGeoJSON['coordinates']) {this.parentDefaultGeoJSON = parentDefaultGeoJSON;}
            if (spatialFieldId) { this.spatialFieldId = spatialFieldId;}
            this.el.ready(this._onReady);
        },

        _drawExtentFromCoords: function(xmin, ymin, xmax, ymax) {
            if ($.isArray(xmin)) {
                var coords = xmin;
                xmin = coords[0]; ymin = coords[1]; xmax = coords[2]; ymax = coords[3];
            }
            return new L.Rectangle([[ymin, xmin], [ymax, xmax]],
                                    this.options.style);
        },

        _drawExtentFromGeoJSON: function(geom) {
            return new L.GeoJSON(geom, {style: this.options.style});
        },

        _onReady: function() {
            var module = this;
            var map;
            var extentLayer;

            // OK map time
            const mapConfig = {
                'type': 'wms',
                'wms.url': 'https://geodaten.metropoleruhr.de/spw2',
                'wms.layers': 'spw2_light',
                'wms.version': '1.3.0'
            }
            const leafletMapOptions = {
                attributionControl: false,
                drawControlTooltips: true,
                maxBounds: module.options.default_extent,
                maxBoundsViscosity: 0.9,
                minZoom: 7.2
            }
            map = ckan.rvrWebMap(
                'dataset-map-container',
                mapConfig,
                leafletMapOptions
            );
    
            // Initialize the draw control
            map.addControl(new L.Control.Draw({
                position: 'topright',
                draw: {
                    polyline: false,
                    polygon: false,
                    circle: false,
                    marker: false,
                    rectangle: {shapeOptions: module.options.style}
                }
            }));
    
            // Handle the apply expanded action
            $('#apply-map-draw-modal').on('click', function() {
                applyChange();
            });

            // Handle the cancel expanded action
            $('#cancel-map-draw-modal').on('click', function() {
                cancelChanges();
            });

            // Handle the cancel expanded action
            $('#use-org-spatial').on('click', function() {
                applyParentDefault();
            });
    
            // When user finishes drawing the box, record it and add it to the map
            map.on('draw:created', function (e) {
                $('#cancel-map-draw-modal').removeClass('disabled').addClass('btn-primary');
                if (extentLayer) {
                    map.removeLayer(extentLayer);
                }
                extentLayer = e.layer;
                map.addLayer(extentLayer);
                $('#apply-map-draw-modal').removeClass('disabled').addClass('btn-primary');
            });

            // The zoom leafletMapOption doesn't seem to work, so manually zoom on load
            map.on('load', e => map.setZoom(7.4));
    
            // Ok setup the default state for the map
            setCurrent();
    
            function setCurrent(useExtent=false) {
                if (useExtent === true) {
                    map.addLayer(extentLayer);
                    map.fitBounds(extentLayer.getBounds());
                } else if (module.initialGeoJSON['coordinates']) {
                    extentLayer = module._drawExtentFromGeoJSON(module.initialGeoJSON);
                    map.addLayer(extentLayer);
                    map.fitBounds(extentLayer.getBounds());
                } else {
                    map.fitBounds(module.options.default_extent)
                }
            }

            // Apply updates to map
            function applyChange() {
                setCurrent(true);
                $('#apply-map-draw-modal').removeClass('btn-primary').addClass('disabled');
                module.currentGeoJSON = extentLayer.toGeoJSON().geometry
                $(`#${module.spatialFieldId}`).val(JSON.stringify(module.currentGeoJSON));
                // console.log("SPATIAL FIELD VALUE", $(`#${module.spatialFieldId}`).val());
            }

            function cancelChanges() {
                map.removeLayer(extentLayer);
                setCurrent();
                $('#apply-map-draw-modal').removeClass('btn-primary').addClass('disabled');
                $('#cancel-map-draw-modal').removeClass('btn-primary').addClass('disabled');
                $('#use-org-spatial').removeClass('disabled').addClass('btn-info');
                if (module.initialGeoJSON['coordinates']) {
                    $(`#${module.spatialFieldId}`).val(JSON.stringify(module.initialGeoJSON));
                } else {
                    $(`#${module.spatialFieldId}`).val('');
                }
            }

            function applyParentDefault() {
                $('#cancel-map-draw-modal').removeClass('disabled').addClass('btn-primary');
                $('#use-org-spatial').addClass('disabled').removeClass('btn-info');
                if (extentLayer) {
                    map.removeLayer(extentLayer);
                }
                if (module.parentDefaultGeoJSON['coordinates']) {
                    console.log("USING EXTENT LAYER FROM PARENT GEOJSON")
                    extentLayer = module._drawExtentFromGeoJSON(module.parentDefaultGeoJSON);
                    map.addLayer(extentLayer);
                    map.fitBounds(extentLayer.getBounds());
                    $(`#${module.spatialFieldId}`).val('');
                }
            }
        }
    }
});
