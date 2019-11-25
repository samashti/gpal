import sys
import sqlite3
import pandas as pd

from geopackagepy import GeoPackageFrame


def read_gpkg(sql, filepath, geom_col='geom', crs=None, index_col=None,
              coerce_float=True, parse_dates=None, params=None):
    """
    Returns a GeoPackageFrame corresponding to the result of the query
    string, which must contain a geometry column in WKB representation.

    Parameters
    ----------
    sql : string
        SQL query to execute in selecting entries from database, or name
        of the table to read from the database.
    filepath : string
        Geopackage file path to be read using the function.
    geom_col : string, default 'geom'
        column name to convert to shapely geometries
    crs : dict or str, optional
        CRS to use for the returned GeoDataFrame; if not set, tries to
        determine CRS from the SRID associated with the first geometry in
        the database, and assigns that to all geometries.


    Returns
    -------
    GeoPackageFrame

    Example
    -------
    SQLite3
    >>> sql = "SELECT geom, kind FROM polygons"
    >>> df = geopackagepy.read_gpkg(sql, 'file.gpkg')
    """

    con = sqlite3.connect(filepath)
    df = pd.read_sql(sql, con, index_col=index_col, coerce_float=coerce_float,
                     parse_dates=parse_dates, params=params)

    if geom_col not in df:
        raise ValueError("Query missing geometry column '{}'".format(geom_col))

    return GeoPackageFrame(df, crs=crs, geometry=geom_col)
