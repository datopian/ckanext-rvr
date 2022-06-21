/* Module for handling the spatial querying
 */
this.ckan.module('rvr-spatial-query', function ($, _) {
    return {
      options: {
        i18n: {
        },
        style: {
          color: '#F06F64',
          weight: 2,
          opacity: 1,
          fillColor: '#F06F64',
          fillOpacity: 0.1,
          clickable: false
        }
      },
      template: {

      },
  
      initialize: function () {
        var module = this;
        $.proxyAll(this, /_on/);
  
        var corner1 = L.latLng(52.58198281531925, 10.1568603515625)
        var corner2 = L.latLng(49.8122251229721, 4.2132568359375)
        bounds = L.latLngBounds(corner1, corner2);

        this.options.default_extent = bounds;
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
        var previous_box;
        var previous_extent;
        var is_exanded = false;
        var should_zoom = true;
        var form = $("#dataset-search");
        // CKAN 2.1
        if (!form.length) {
            form = $(".search-form");
        }
  
        var buttons;
  
        // Add necessary fields to the search form if not already created
        $(['ext_bbox', 'ext_prev_extent']).each(function(index, item){
          if ($("#" + item).length === 0) {
            $('<input type="hidden" />').attr({'id': item, 'name': item}).appendTo(form);
          }
        });

        // OK map time
        const mapConfig = {
            'type': 'wms',
            'wms.url': 'https://geodaten.metropoleruhr.de/spw2',
            'wms.layers': 'spw2_light',
            'wms.version': '1.3.0'
        }
        map = ckan.rvrWebMap(
          'dataset-map-container',
          mapConfig,
          {
            attributionControl: false,
            drawControlTooltips: false,
            maxBounds: this.options.default_extent,
            maxBoundsViscosity: 0.8,
            minZoom: 7.2
          }
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
  
        // OK add the expander
        $('a.leaflet-draw-draw-rectangle', module.el).on('click', function(e) {
          if (!is_exanded) {
            $('body').addClass('dataset-map-expanded');
            if (should_zoom && !extentLayer) {
              map.zoomIn();
            }
            resetMap();
            is_exanded = true;
          }
        });
        var buttonsHtml = [
          '<div id="dataset-map-edit-buttons">',
          '<a href="javascript:;" class="btn cancel">'+ this._('Cancel')+ '</a> ',
          '<a href="javascript:;" class="btn apply disabled">'+ this._('Apply')+ '</a>',
          '</div>'
        ].join('')
        // Setup the expanded buttons
        buttons = $(buttonsHtml).insertBefore('#dataset-map-attribution');
  
        // Handle the cancel expanded action
        $('.cancel', buttons).on('click', function() {
          $('body').removeClass('dataset-map-expanded');
          if (extentLayer) {
            map.removeLayer(extentLayer);
          }
          setPreviousExtent();
          setPreviousBBBox();
          resetMap();
          is_exanded = false;
        });
  
        // Handle the apply expanded action
        $('.apply', buttons).on('click', function() {
          if (extentLayer) {
            $('body').removeClass('dataset-map-expanded');
            is_exanded = false;
            resetMap();
            // Eugh, hacky hack.
            setTimeout(function() {
              map.fitBounds(extentLayer.getBounds());
              submitForm();
            }, 200);
          }
        });
  
        // When user finishes drawing the box, record it and add it to the map
        map.on('draw:created', function (e) {
          if (extentLayer) {
            map.removeLayer(extentLayer);
          }
          extentLayer = e.layer;
          $('#ext_bbox').val(extentLayer.getBounds().toBBoxString());
          map.addLayer(extentLayer);
          $('.apply', buttons).removeClass('disabled').addClass('btn-primary');
        });
  
        // Record the current map view so we can replicate it after submitting
        map.on('moveend', function(e) {
          $('#ext_prev_extent').val(map.getBounds().toBBoxString());
        });
  
        // Ok setup the default state for the map
        var previous_bbox;
        setPreviousBBBox();
        setPreviousExtent();
  
        // OK, when we expand we shouldn't zoom then
        map.on('zoomstart', function(e) {
          should_zoom = false;
        });
  
  
        // Is there an existing box from a previous search?
        function setPreviousBBBox() {
          previous_bbox = module._getParameterByName('ext_bbox');
          if (previous_bbox) {
            $('#ext_bbox').val(previous_bbox);
            extentLayer = module._drawExtentFromCoords(previous_bbox.split(','))
            map.addLayer(extentLayer);
            map.fitBounds(extentLayer.getBounds());
          }
        }
  
        // Is there an existing extent from a previous search?
        function setPreviousExtent() {
          previous_extent = module._getParameterByName('ext_prev_extent');
          if (previous_extent) {
            coords = previous_extent.split(',');
            map.fitBounds([[coords[1], coords[0]], [coords[3], coords[2]]]);
          } else {
            if (!previous_bbox){
                map.fitBounds(module.options.default_extent);
            }
          }
        }
  
        // Reset map view
        function resetMap() {
          L.Util.requestAnimFrame(map.invalidateSize, map, !1, map._container);
        }
  
        // Add the loading class and submit the form
        function submitForm() {
          setTimeout(function() {
            form.submit();
          }, 800);
        }
      }
    }
  });
