import sys
import sqlite3
import pandas as pd

from geopackagepy import GeoPackageFrame, read_gpkg

"""

CREATE VIEW my_view AS SELECT foo.fid AS OGC_FID, foo.geom, ... FROM foo JOIN another_table ON foo.some_id = another_table.other_id;

INSERT INTO gpkg_contents (table_name, identifier, data_type, srs_id) VALUES ( 'my_view', 'my_view', 'features', 4326);

INSERT INTO gpkg_geometry_columns (table_name, column_name, geometry_type_name, srs_id, z, m) values ('my_view', 'my_geom', 'GEOMETRY', 4326, 0, 0);

gpkg_contents
gpkg_ogr_contents
gpkg_geometry_columns

"""