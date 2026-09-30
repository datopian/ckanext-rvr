import json
import logging

import ckan.plugins.toolkit as tk
import shapely.geometry
from shapely import wkt as shapely_wkt
from shapely.errors import ShapelyError
from ckanext.spatial.lib import normalize_bbox

log = logging.getLogger(__name__)

# ~10m at the latitude of the Ruhr area, keeps the outline visually identical
# while shrinking detailed city boundaries from hundreds of KB to a few KB
DEFAULT_SIMPLIFY_TOLERANCE = 0.0001


def shape_from_wkt(value):
    """
    Parses a WKT string (e.g. the `spatial_text` of DCAT datasets that publish
    `dct:spatial` as a WKT literal). Returns None if it is not valid WKT.
    """
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        shape = shapely_wkt.loads(value)
    except (ShapelyError, ValueError, TypeError):
        return None
    if shape.is_empty:
        return None
    return shape


def geojson_from_wkt(value):
    """
    Converts a WKT string to a simplified GeoJSON string that can be stored in
    `spatial`, or returns None if it can't be converted.
    """
    shape = shape_from_wkt(value)
    if shape is None:
        return None

    tolerance = float(tk.config.get(
        "ckanext.rvr.spatial_simplify_tolerance", DEFAULT_SIMPLIFY_TOLERANCE))
    if tolerance > 0 and shape.geom_type != "Point":
        simplified = shape.simplify(tolerance, preserve_topology=True)
        if simplified.is_valid and not simplified.is_empty:
            shape = simplified

    if not normalize_bbox(list(shape.bounds)):
        log.warning("WKT geometry out of bounds, ignoring: %s", value[:100])
        return None

    return json.dumps(shapely.geometry.mapping(shape))


def bbox_from_wkt(value):
    """
    Returns the minx/miny/maxx/maxy dict expected by the solr-bbox backend of
    ckanext-spatial, or None if the value isn't valid WKT.
    """
    shape = shape_from_wkt(value)
    if shape is None:
        return None
    return normalize_bbox(list(shape.bounds))
