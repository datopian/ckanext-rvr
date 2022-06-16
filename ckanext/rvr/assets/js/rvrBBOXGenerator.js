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

        initialize: function () {
            $.proxyAll(this, /_on/);
            var corner1 = L.latLng(51.2, 8.1);
            var corner2 = L.latLng(52, 6.1);
            bounds = L.latLngBounds(corner1, corner2);

            // Get the current spatial data
            var currentGeoJSON = this.el.data('currentspatial');
            var spatialFieldId = this.el.data('spatialfield');

            this.options.default_extent = bounds;
            this.currentGeoJSON = currentGeoJSON;
            this.spatialFieldId = spatialFieldId;
            this.el.ready(this._onReady);
        },

        _getParameterByName: function (name) {
            var match = RegExp('[?&]' + name + '=([^&]*)')
                            .exec(window.location.search);
            return match ?
                decodeURIComponent(match[1].replace(/\+/g, ' '))
                : null;
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
                minZoom: 8
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
                setCurrent(true);
            });
    
            // When user finishes drawing the box, record it and add it to the map
            map.on('draw:created', function (e) {
                if (extentLayer) {
                    map.removeLayer(extentLayer);
                }
                extentLayer = e.layer;
                map.addLayer(extentLayer);
                $('#apply-map-draw-modal').removeClass('disabled').addClass('btn-primary');
            });

            // The zoom leafletMapOption doesn't seem to work, so manually zoom on load
            map.on('load', e => map.setZoom(7.2));
    
            // Ok setup the default state for the map
            setCurrent();
    
            function setCurrent(useExtent=false) {
                if (useExtent === true) {
                    console.log("USING CURRENT EXTENT LAYER")
                    map.addLayer(extentLayer);
                    map.fitBounds(extentLayer.getBounds());
                } else if (module.currentGeoJSON instanceof Object) {
                    console.log("USING EXTENT LAYER FROM GEOJSON")
                    extentLayer = module._drawExtentFromGeoJSON(module.currentGeoJSON);
                    map.addLayer(extentLayer);
                    map.fitBounds(extentLayer.getBounds());
                } else {
                    map.fitBounds(module.options.default_extent)
                }
            }

            // Apply updates to map
            function applyChange() {
                $('#apply-map-draw-modal').removeClass('btn-primary').addClass('disabled');
                console.log("ELEMENT SPATIAL FIELD VALUE", $(`#${module.spatialFieldId}`).val());
                $(`#${module.spatialFieldId}`).val(JSON.stringify(extentLayer.toGeoJSON().geometry));
                console.log("SECOND SPATIAL FIELD VALUE", $(`#${module.spatialFieldId}`).val());
            }
        }
    }
});
