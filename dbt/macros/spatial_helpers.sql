-- Return the area of a geometry column in square kilometres (geography cast).
{% macro area_km2(col) %}
    (ST_Area({{ col }}::geography) / 1000000.0)
{% endmacro %}

-- Build a WKT polygon string from four bounding-box floats.
{% macro bbox_polygon(west, south, east, north) %}
    ST_GeomFromText(
        'POLYGON((' ||
            {{ west }}  || ' ' || {{ south }} || ', ' ||
            {{ east }}  || ' ' || {{ south }} || ', ' ||
            {{ east }}  || ' ' || {{ north }} || ', ' ||
            {{ west }}  || ' ' || {{ north }} || ', ' ||
            {{ west }}  || ' ' || {{ south }} ||
        '))',
        4326
    )
{% endmacro %}

-- Return TRUE when two geometry columns overlap (ST_Intersects wrapper).
{% macro intersects(geom_a, geom_b) %}
    ST_Intersects({{ geom_a }}, {{ geom_b }})
{% endmacro %}

-- Spatial union aggregate across a partition (for window-style CTEs).
{% macro union_footprints(geom_col) %}
    ST_Union({{ geom_col }})
{% endmacro %}
