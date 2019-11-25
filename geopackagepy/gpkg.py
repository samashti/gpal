import os

import sqlite3
import numpy as np
import pandas as pd
from shapely import wkb
import geopandas as gpd
from pandas import DataFrame, Series
from geopandas import GeoDataFrame, GeoSeries
from shapely.geometry.base import BaseGeometry


from geopackagepy import gpkg_constants as const

DEFAULT_GEO_COLUMN_NAME = 'geom'


class GeoPackageFrame(GeoDataFrame, DataFrame):
    """
    Returns a GeoPackageFrame corresponding to the result of the query
    string, which must contain a geometry column in gpkg binary buffer
    representation.

    Parameters
    ----------
    crs : str (optional)
        Coordinate system
    geometry : str or array (optional)
        If str, column to use as geometry. If array, will be set as 'geometry'
    """
    _internal_names = ['_data', '_cacher', '_item_cache', '_cache',
                       'is_copy', '_subtyp', '_index',
                       '_default_kind', '_default_fill_value', '_metadata',
                       '__array_struct__', '__array_interface__']

    _metadata = ['crs', '_geometry_column_name']

    _geometry_column_name = DEFAULT_GEO_COLUMN_NAME

    def __init__(self, *args, **kwargs):
        crs = kwargs.pop('crs', None)
        geometry = kwargs.pop('geometry', self._geometry_column_name)
        super(GeoPackageFrame, self).__init__(*args, **kwargs)
        if geometry is not None:
            self._get_geometry(geometry, crs=crs, inplace=True)
        self._invalidate_sindex()

    def __getstate__(self):
        meta = dict((k, getattr(self, k, None)) for k in self._metadata)
        return dict(_data=self._data, _typ=self._typ,
                    _metadata=self._metadata, **meta)

    def __setattr__(self, attr, val):
        # have to special case geometry b/c pandas tries to use as column...
        if attr == 'geometry':
            object.__setattr__(self, attr, val)
        else:
            super(GeoPackageFrame, self).__setattr__(attr, val)

    def _get_geometry(self, col, crs=None, drop=True, inplace=False):
        if inplace:
            frame = self
        else:
            frame = self.copy()

        if not crs:
            _, srsid = self._read_geom(frame[col].iloc[0])
            self.crs = {'init':f'epsg:{srsid}'}
        else:
            self.crs = crs

        geo_column_name = 'geometry'
        level = frame[col].apply(
            lambda x: self._read_geom(x)[0] if x else None
        )

        if drop:
            frame.drop(col, 1, inplace=True)

        if isinstance(level, GeoSeries) and level.crs != crs:
            # Avoids caching issues/crs sharing issues
            level = level.copy()
            level.crs = crs

        # Check that we are using a listlike of geometries
        if not all(isinstance(item, BaseGeometry) or pd.isnull(item) for item in level):
            raise TypeError("Input geometry column must contain valid geometry objects.")
        frame[geo_column_name] = level
        frame._geometry_column_name = geo_column_name
        frame.crs = self.crs
        frame = frame.pipe(GeoDataFrame, crs=self.crs, geometry=geo_column_name)
        frame._invalidate_sindex()
        if not inplace:
            return frame

    def _read_geom(self, buffer):
        magikString = buffer.decode(encoding='ascii', errors='ignore')[0:2]
        if magikString != const.GEOPACKAGE_GEOMETRY_MAGIC_NUMBER:
            raise ValueError('Unexpected GeoPackage Geometry magic number')

        version = np.frombuffer(buffer, dtype='uint8', offset=2)[0]
        flags = np.frombuffer(buffer, dtype='uint8', offset=3)[0]

        if version != const.GEOPACKAGE_GEOMETRY_VERSION_1:
            raise ValueError('Unexpected GeoPackage Geometry version')

        flags_dict = self._read_flags(flags)

        dt = '<i2' if flags_dict['byteOrder'] else '>i2'
        srsID = np.frombuffer(buffer, dtype=dt, count=1, offset=4)[0]

        envelopeAndOffset = self._read_envelope(buffer, flags_dict)
        offset = envelopeAndOffset['offset']
        wkbBuffer = buffer[offset:]

        geometry = wkb.loads(wkbBuffer)

        return geometry, srsID

    def _read_flags(self, flagsInt):
        output = dict()
        # Verify the reserved bits at 7 and 6 are 0
        reserved7 = (flagsInt >> 7) & 1
        reserved6 = (flagsInt >> 6) & 1
        if reserved6 != 0 or reserved7 != 0:
            raise ValueError(
        'Unexpected GeoPackage Geometry flags. Flag bit 7 and 6 should both be 0'
        )

        # Get the binary type from bit 5, 0 for standard and 1 for extended
        binaryType = (flagsInt >> 5) & 1
        output.update(extended=binaryType==1)

        # Get the empty geometry flag from bit 4, 0 for non-empty and 1 for
        # empty
        emptyValue = (flagsInt >> 4) & 1
        output.update(empty=emptyValue==1)

        # Get the envelope contents indicator code (3-bit unsigned integer from
        # bits 3, 2, and 1)
        envelopeIndicator = (flagsInt >> 1) & 7
        if envelopeIndicator > 4:
            raise ValueError(
        'Unexpected GeoPackage Geometry flags. Envelope contents indicator must be between 0 and 4'
        )
        output.update(envelopeIndicator=envelopeIndicator)

        # Get the byte order from bit 0, 0 for Big Endian and 1 for Little Endian
        byteOrderValue = flagsInt & 1
        output.update(byteOrder=byteOrderValue)

        return output

    def _read_envelope(self, buffer, flags_dict):
        dt = np.dtype('d')
        readMethod = dt.newbyteorder('<') if flags_dict['byteOrder'] else dt.newbyteorder('>')

        envelopeByteOffset = 8
        reads = 0
        envelopeAndOffset = {
            'envelope': None,
            'offset': envelopeByteOffset
        }

        if flags_dict['envelopeIndicator'] <= 0:
            return envelopeAndOffset

        # Read x and y values and create envelope
        envelope = {}
        envelope['minx'] = np.frombuffer(
            buffer, dtype=readMethod,
            count=1, offset=envelopeByteOffset + 8 * reads)[0]
        reads += 1
        envelope['maxx'] = np.frombuffer(
            buffer, dtype=readMethod,
            count=1, offset=envelopeByteOffset + 8 * reads)[0]
        reads += 1
        envelope['miny'] = np.frombuffer(
            buffer, dtype=readMethod,
            count=1, offset=envelopeByteOffset + 8 * reads)[0]
        reads += 1
        envelope['maxy'] = np.frombuffer(
            buffer, dtype=readMethod,
            count=1, offset=envelopeByteOffset + 8 * reads)[0]


        envelope['hasZ'] = False
        envelope['hasM'] = False

        # read z values
        if flags_dict['envelopeIndicator'] == 2 or flags_dict['envelopeIndicator'] == 4:
            envelope['hasZ'] = True
            reads += 1
            envelope['minZ'] = np.frombuffer(
                buffer, dtype=readMethod,
                count=1, offset=envelopeByteOffset + 8 * reads)[0]
            reads += 1
            envelope['maxZ'] = np.frombuffer(
                buffer, dtype=readMethod,
                count=1, offset=envelopeByteOffset + 8 * reads)[0]

        # read m values
        if flags_dict['envelopeIndicator'] == 3 or flags_dict['envelopeIndicator'] == 4:
            envelope['hasM'] = True
            reads += 1
            envelope['minM'] = np.frombuffer(
                buffer, dtype=readMethod,
                count=1, offset=envelopeByteOffset + 8 * reads)[0]
            reads += 1
            envelope['maxM'] = np.frombuffer(
                buffer, dtype=readMethod,
                count=1, offset=envelopeByteOffset + 8 * reads)[0]

        reads += 1
        envelopeAndOffset['envelope'] = envelope
        envelopeAndOffset['offset'] = envelopeByteOffset + (8 * reads)

        return envelopeAndOffset
