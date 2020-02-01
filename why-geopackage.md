# From Shapefiles to Geojsons ... to `GeoPackage`

## `Problems with shapefiles:`

* sluggish
* multifile format (.shp, .dbf., .shx, .prj, encoding, other indexes, etc.)
* Attribute names are limited to 10 characters
* Inconsistencies because of ESRI's wkt
* File size is restricted to 2 GB
* single vector layer but 6 files to handle.
* only contain one geometry type per file

____________________________________________________________________________________________________________________________________________

## `Problems with geojson:`

* file for a similar number of features on shapefile / geopackage is almost double in size.
* no spatial indexing and so, loading the file in python or qgis is very slow.
* It's loaded into memory in full at once, which might create problem in different situations.
* Loads slow, but memory usage is similar or more compared to shapefile / geopackage
* If the file size exceeds some limit the features might written incomplete and hence making the file corrupt.

____________________________________________________________________________________________________________________________________________

## `GEOPACKAGE:`

`Advantages:`
* Open source, based on sqlite database. very lightweight but highly compatible.
* Accessible by non-gis softwares as well.
* Compared to shapefile ~1.1 - 1.3 times lighter file size and >2 times lighter wrt geojson.
```bash
$ fs roads_demo/*
193M	roads_demo/roads_valid.geojson
 70M	roads_demo/roads_valid.gpkg
 81M	roads_demo/shp
```

* since the layer is inherently rtree indexed, loading file on qgis or making queries on the file database is very fast.
* no limit on file size, can handle large number of features in a lightweight file size.
* can have right and full column names as opposed to shapefiles.
* Faster work-flow than with Shapfiles
* Can have multiple vector layers in a same file.

```bash
$ ogrinfo ./outputs/bangalore_poc_outputs.gpkg

INFO: Open of './outputs/bangalore_poc_outputs.gpkg' using driver 'GPKG' successful.

1: roads_area_hex8 (Multi Polygon)
2: roads_area_hex9 (Multi Polygon)
3: roads_area_major_segments (Multi Polygon)
4: roads_lines_v1 (Line String)
5: roads_poly_line_vertices (Point)
6: intersection_node_points (Point)
7: end_node_points (Point)
```

* the file can also include non-spatial tables
```bash
$ ogrinfo ./india_villages_master_2011.gpkg

INFO: Open of './india_villages_master_2011.gpkg' using driver 'GPKG' successful.

1: data_master (None) # (non-spatial)
2: village_codes_mapping (None) # (non-spatial)
3: village_points (Point)
4: voronoi_polygons (Multi Polygon)
```

* Loading and editing features on qgis is faster.
* file can be handled using GDAL, QGIS, python, R, sqlite, postgres (with few limitations to features on each platform)
* laoding geopackage to postgres is faster, since it's already a database format and indexed (compared to shapefile or geojson)
* can support raster data as well. (with limitations)

____________________________________________________________________________________________________________________________________________

## `How we can use this in our workflow?`

____________________________________________________________________________________________________________________________________________

### `Large output files`

relatively lighter file size, spatially indexed
* building level affluence output with 26 columns. (reading, visualizing, querying only parts, apply transformations)
* magik buildings data for large metros (~1.2 mil building each major metro)

____________________________________________________________________________________________________________________________________________

### `Tiled tables - multi layer geopackage`

Some really large outputs such as delhi buildings ~3.6 mil features, could be handled in grids.

Divide the bbox of delhi into 20 square/rectangular grids, and save buildings in each grid as a separate layer in the same geopackage file.
Easier to load only parts, if needed to filter. 

But, What about loading entire dataset???

____________________________________________________________________________________________________________________________________________

### `Reduce/avoid redundant files for outputs`

* file.csv and file.shp (.dbf, .cpg, .prj, .shx)
* file.csv and file.geojson

Geopackage can have non-spatial table to avoid an extra csv file.

```bash
$ ogrinfo ./test.gpkg

INFO: Open of './test.gpkg' using driver 'GPKG' successful.

1: data_master (None) # (non-spatial) has all the attributes of the outputs.
3: feat_points_layer (Point) # only primary key from data master with geometry col.
4: feat_polygons_layer (Multi Polygon) # only primary key from data master with geometry col.
```

again, this is not required if it's just one vector layer.

____________________________________________________________________________________________________________________________________________

### `Spatial Views`

A saved sql query that can be used to access data from multiple tables within a geopackage.

```sql
CREATE VIEW my_view AS SELECT foo.fid AS OGC_FID, foo.geom, ... FROM foo JOIN another_table ON foo.some_id = another_table.other_id;

INSERT INTO gpkg_contents (table_name, identifier, data_type, srs_id) VALUES ( 'my_view', 'my_view', 'features', 4326);

INSERT INTO gpkg_geometry_columns (table_name, column_name, geometry_type_name, srs_id, z, m) values ('my_view', 'my_geom', 'GEOMETRY', 4326, 0, 0);
```

```bash
$ ogrinfo ./test.gpkg

INFO: Open of './test.gpkg' using driver 'GPKG' successful.

1: data_master (None) # (non-spatial)
3: feat_points_layer (Point)
4: feat_polygons_layer (Multi Polygon)
5: view_feat_points_master (Point)
6: view_feat_polygons_master (Multi Polygon)
```

____________________________________________________________________________________________________________________________________________

### `Handling Geography masters`

Keep only primary keys and create table views.
* `data_master` file to have all the attributes.
```python
In [1]: con = sqlite3.connect('./india_villages_master_2011.gpkg')

In [2]: df = pd.read_sql('SELECT * FROM data_master LIMIT 100', con)

In [3]: df.info()
<class 'pandas.core.frame.DataFrame'>
RangeIndex: 100 entries, 0 to 99
Data columns (total 16 columns):
index                 100 non-null int64
id                    100 non-null object
country_name          100 non-null object
state_code            100 non-null object
state_name            100 non-null object
district_code         100 non-null float64
district_name         100 non-null object
block_code            100 non-null float64
block_name            100 non-null object
village_code          100 non-null object
village_code_short    100 non-null float64
village_name          100 non-null object
subdistrict_code      100 non-null object
subdistrict_name      100 non-null object
year                  100 non-null int64
total_households      100 non-null int64
dtypes: float64(3), int64(3), object(10)
memory usage: 12.6+ KB
```
* `village_points` layer has village code and point geometries.

```python
In [1]: con = sqlite3.connect('./india_villages_master_2011.gpkg')

In [2]: gdf = gpkg.read_gpkg('SELECT * FROM village_points LIMIT 100', file)

In [3]: gdf.info()
<class 'geopackagepy.gpkg.GeoPackageFrame'>
RangeIndex: 100 entries, 0 to 99
Data columns (total 3 columns):
fid             100 non-null int64
village_code    100 non-null object
geometry        100 non-null object
dtypes: int64(1), object(2)
memory usage: 2.4+ KB
```

* `voronoi_polygons` layer has village code and voronoi geometries.

```python
In [1]: con = sqlite3.connect('./india_villages_master_2011.gpkg')

In [2]: gdf = gpkg.read_gpkg('SELECT * FROM voronoi_polygons LIMIT 100', file)

In [3]: gdf.info()
<class 'geopackagepy.gpkg.GeoPackageFrame'>
RangeIndex: 100 entries, 0 to 99
Data columns (total 3 columns):
fid             100 non-null int64
village_code    100 non-null object
geometry        100 non-null object
dtypes: int64(1), object(2)
memory usage: 2.4+ KB
```

* spatial views `view_india_village_points` and `view_india_village_voronoi` to view joined master attributes to geometries.

```python
In [1]: con = sqlite3.connect('./india_villages_master_2011.gpkg')

In [2]: gdf = gpkg.read_gpkg('SELECT * FROM view_india_village_voronoi WHERE state_name = "Kerala"', file)

In [3]: gdf.info()
<class 'geopackagepy.gpkg.GeoPackageFrame'>
RangeIndex: 1018 entries, 0 to 1017
Data columns (total 17 columns):
index                 1018 non-null int64
id                    1018 non-null object
country_name          1018 non-null object
state_code            1018 non-null object
state_name            1018 non-null object
district_code         1018 non-null float64
district_name         1018 non-null object
block_code            1018 non-null float64
block_name            1018 non-null object
village_code          1018 non-null object
village_code_short    1018 non-null float64
village_name          1018 non-null object
subdistrict_code      1018 non-null object
subdistrict_name      1018 non-null object
year                  1018 non-null int64
total_households      1018 non-null int64
geometry              1018 non-null object
dtypes: float64(3), int64(3), object(11)
memory usage: 135.3+ KB

In [4]: gdf = gpkg.read_gpkg('SELECT * FROM view_india_village_points WHERE state_name = "Kerala"', file)

In [5]: gdf.info()
<class 'geopackagepy.gpkg.GeoPackageFrame'>
RangeIndex: 1018 entries, 0 to 1017
Data columns (total 17 columns):
index                 1018 non-null int64
id                    1018 non-null object
country_name          1018 non-null object
state_code            1018 non-null object
state_name            1018 non-null object
district_code         1018 non-null float64
district_name         1018 non-null object
block_code            1018 non-null float64
block_name            1018 non-null object
village_code          1018 non-null object
village_code_short    1018 non-null float64
village_name          1018 non-null object
subdistrict_code      1018 non-null object
subdistrict_name      1018 non-null object
year                  1018 non-null int64
total_households      1018 non-null int64
geometry              1018 non-null object
dtypes: float64(3), int64(3), object(11)
memory usage: 135.3+ KB
```

* the new `india_villages_master_2011.gpkg` which has master attributes along with point and voronoi geometries is `460MB` in file size as opposed to the village_points shapefile of `520MB` + village_voronoi shapefile of `820MB` and csv file of `110MB` for india village master.

____________________________________________________________________________________________________________________________________________

### `WIP files (vector layers)`

_/filepath/to/dataset/_

```bash

$ ns3 /filepath/to/dataset/ -limit 300

/filepath/to/dataset/
├── aff_chennai.tar.gz
├── aff_index_urban_kar.tar.gz
├── aff_index_urban_tn.tar.gz
├── aff_kar.tar.gz
├── dataset_bangalore_test1.shx
├── dataset_bangalore_test.shx
├── dataset_chennai.csv
├── dataset_chennai.dbf
├── dataset_chennai.prj
├── dataset_chennai.shp
├── dataset_chennai.shx
├── dataset_chennai_v1.csv
├── dataset_data.csv
├── dataset_delhi.csv
├── dataset_delhi.dbf
├── dataset_delhi.prj
├── dataset_delhi.shp
├── dataset_delhi.shx
├── dataset_delhi_v1.dbf
├── dataset_delhi_v1.shp
├── dataset_delhi_v2.dbf
├── dataset_delhi_v2.prj
├── dataset_delhi_v2.shp
├── dataset_delhi_v2.shx
├── dataset_delhi_v3.csv
├── dataset_delhi_v3.dbf
├── dataset_delhi_v3.prj
├── dataset_delhi_v3.shp
├── dataset_delhi_v3.shx
├── dataset_delhi_v4.dbf
├── dataset_delhi_v4.prj
├── dataset_delhi_v4.shp
├── dataset_delhi_v4.shx
├── dataset_delhi_v5.dbf
├── dataset_delhi_v5.prj
├── dataset_delhi_v5.shp
├── dataset_delhi_v5.shx
├── dataset_delhi_v6.dbf
├── dataset_delhi_v6.prj
├── dataset_delhi_v6.shp
├── dataset_delhi_v6.shx
├── dataset_index_rural.dbf
├── dataset_index_rural.prj
├── dataset_index_rural.shp
├── dataset_index_rural.shx
├── dataset_index_rural_unilever.csv
├── dataset_index_rural_v1.dbf
├── dataset_index_rural_v1.prj
├── dataset_index_rural_v1.shp
├── dataset_index_rural_v1.shx
├── dataset_index_rural_v2.dbf
├── dataset_index_rural_v2.prj
├── dataset_index_rural_v2.shp
├── dataset_index_rural_v2.shx
├── dataset_index_urban.csv
├── dataset_index_urban.dbf
├── dataset_index_urban_kar.csv
├── dataset_index_urban_kar.dbf
├── dataset_index_urban_kar.prj
├── dataset_index_urban_kar.shp
├── dataset_index_urban_kar.shx
├── dataset_index_urban_kar_v1.csv
├── dataset_index_urban_kar_v1.dbf
├── dataset_index_urban_kar_v1.prj
├── dataset_index_urban_kar_v1.shp
├── dataset_index_urban_kar_v1.shx
├── dataset_index_urban_kar_v2.csv
├── dataset_index_urban_kar_v2.dbf
├── dataset_index_urban_kar_v2.prj
├── dataset_index_urban_kar_v2.shp
├── dataset_index_urban_kar_v2.shx
├── dataset_index_urban_kar_v4.dbf
├── dataset_index_urban_kar_v4.prj
├── dataset_index_urban_kar_v4.shp
├── dataset_index_urban_kar_v4.shx
├── dataset_index_urban.prj
├── dataset_index_urban.shp
├── dataset_index_urban.shx
├── dataset_index_urban_tn.csv
├── dataset_index_urban_tn.dbf
├── dataset_index_urban_tn.prj
├── dataset_index_urban_tn.shp
├── dataset_index_urban_tn.shx
├── dataset_index_urban_tn_v1.csv
├── dataset_index_urban_tn_v1.dbf
├── dataset_index_urban_tn_v1.prj
├── dataset_index_urban_tn_v1.shp
├── dataset_index_urban_tn_v1.shx
├── dataset_index_urban_tn_v2.csv
├── dataset_index_urban_tn_v2.dbf
├── dataset_index_urban_tn_v2.prj
├── dataset_index_urban_tn_v2.shp
├── dataset_index_urban_tn_v2.shx
├── dataset_index_urban_tn_v3.dbf
├── dataset_index_urban_tn_v3.prj
├── dataset_index_urban_tn_v3.shp
├── dataset_index_urban_tn_v3.shx
├── dataset_index_urban_tn_v4.dbf
├── dataset_index_urban_tn_v4.prj
├── dataset_index_urban_tn_v4.shp
├── dataset_index_urban_tn_v4.shx
├── dataset_index_urban_v1.dbf
├── dataset_index_urban_v1.prj
├── dataset_index_urban_v1.shp
├── dataset_index_urban_v1.shx
├── aff_urban.tar.gz
├── bangalore_dataset_income.csv
├── bangalore_dataset_rent.dbf
├── bangalore_dataset_rent.prj
├── bangalore_dataset_rent.shp
├── bangalore_dataset_rent.shx
├── delhi
│   ├── dataset_delhi_v7.dbf
│   ├── dataset_delhi_v7.prj
│   ├── dataset_delhi_v7.shp
│   └── dataset_delhi_v7.shx
├── delhi_ncr
│   ├── input
│   └── output
│       ├── delhi_ncr_data_v6.dbf
│       ├── delhi_ncr_data_v6.prj
│       ├── delhi_ncr_data_v6.shp
│       └── delhi_ncr_data_v6.shx
├── grid_bld_nlt.csv
├── grid_e9
│   └── bangalore
│       ├── building_indicators_grid_e8_bangalore.csv
│       ├── building_indicators_grid_e9_bangalore.csv
│       ├── feature_inputs
│       │   ├── docfee_blore_grid8.csv
│       │   ├── docfee_blore_grid9.csv
│       │   ├── feat_buildings_grid8_blore.csv
│       │   ├── feat_buildings_grid9_blore.csv
│       │   ├── feat_grid8_aff.csv
│       │   ├── feat_grid8.csv
│       │   ├── feat_grid9.csv
│       │   ├── feat_gride8_with_buildings.csv
│       │   ├── rent_blore_grid8.csv
│       │   ├── rent_blore_grid9.csv
│       │   ├── restcost_blore_grid8.csv
│       │   └── restcost_blore_grid9.csv
│       ├── inputs
│       │   ├── doctorfee_grid8.csv
│       │   ├── doctorfee_grid9.csv
│       │   ├── restcostfor2_grid8.csv
│       │   └── restcostfor2_grid9.csv
│       ├── out
│       │   ├── grid9_pred_allfeat_combined.csv
│       │   ├── grid9_pred_rent_build_LinearReg.csv
│       │   ├── grid9_pred_rent_build_rest_doc_LinearReg.csv
│       │   └── grid9_pred_rent_LinearReg.csv
│       └── regression_out
│           ├── grid9_pred_combined.cpg
│           ├── grid9_pred_combined.csv
│           ├── grid9_pred_combined.dbf
│           ├── grid9_pred_combined_DecisionTree.cpg
│           ├── grid9_pred_combined_DecisionTree.csv
│           ├── grid9_pred_combined_DecisionTree.dbf
│           ├── grid9_pred_combined_DecisionTree.prj
│           ├── grid9_pred_combined_DecisionTree.shp
│           ├── grid9_pred_combined_DecisionTree.shx
│           ├── grid9_pred_combined.prj
│           ├── grid9_pred_combined.shp
│           ├── grid9_pred_combined.shx
│           ├── grid9_pred_combined_weighted_e8.cpg
│           ├── grid9_pred_combined_weighted_e8.csv
│           ├── grid9_pred_combined_weighted_e8.dbf
│           ├── grid9_pred_combined_weighted_e8.prj
│           ├── grid9_pred_combined_weighted_e8.shp
│           ├── grid9_pred_combined_weighted_e8.shx
│           ├── grid9_pred_combined_weighted_e8_v1.cpg
│           ├── grid9_pred_combined_weighted_e8_v1.csv
│           ├── grid9_pred_combined_weighted_e8_v1.dbf
│           ├── grid9_pred_combined_weighted_e8_v1.prj
│           ├── grid9_pred_combined_weighted_e8_v1.shp
│           ├── grid9_pred_combined_weighted_e8_v1.shx
│           ├── grid9_pred_v1.cpg
│           ├── grid9_pred_v1.dbf
│           ├── grid9_pred_v1.prj
│           ├── grid9_pred_v1.shp
│           ├── grid9_pred_v1.shx
│           ├── grid9_pred_v2.cpg
│           ├── grid9_pred_v2.csv
│           ├── grid9_pred_v2.dbf
│           ├── grid9_pred_v2_DecisionTree.cpg
│           ├── grid9_pred_v2_DecisionTree.csv
│           ├── grid9_pred_v2_DecisionTree.dbf
│           ├── grid9_pred_v2_DecisionTree.prj
│           ├── grid9_pred_v2_DecisionTree.shp
│           ├── grid9_pred_v2_DecisionTree.shx
│           ├── grid9_pred_v2.prj
│           ├── grid9_pred_v2.shp
│           ├── grid9_pred_v2.shx
│           ├── grid9_pred_v3.cpg
│           ├── grid9_pred_v3.csv
│           ├── grid9_pred_v3.dbf
│           ├── grid9_pred_v3_DecisionTree.cpg
│           ├── grid9_pred_v3_DecisionTree.csv
│           ├── grid9_pred_v3_DecisionTree.dbf
│           ├── grid9_pred_v3_DecisionTree.prj
│           ├── grid9_pred_v3_DecisionTree.shp
│           ├── grid9_pred_v3_DecisionTree.shx
│           ├── grid9_pred_v3.prj
│           ├── grid9_pred_v3.shp
│           ├── grid9_pred_v3.shx
│           ├── grid9_pred_v4.cpg
│           ├── grid9_pred_v4.csv
│           ├── grid9_pred_v4.dbf
│           ├── grid9_pred_v4_DecisionTree.cpg
│           ├── grid9_pred_v4_DecisionTree.csv
│           ├── grid9_pred_v4_DecisionTree.dbf
│           ├── grid9_pred_v4_DecisionTree.prj
│           ├── grid9_pred_v4_DecisionTree.shp
│           ├── grid9_pred_v4_DecisionTree.shx
│           ├── grid9_pred_v4.prj
│           ├── grid9_pred_v4.shp
│           └── grid9_pred_v4.shx
├── grids_ntl.dbf
├── grids_ntl.prj
├── grids_ntl.shp
├── grids_ntl.shx
├── input
│   ├── dataset_bangalore_test1.dbf
│   ├── dataset_bangalore_test1.prj
│   ├── dataset_bangalore_test1.shp
│   ├── dataset_bangalore_test.dbf
│   ├── dataset_bangalore_test.prj
│   ├── dataset_bangalore_test.shp
│   ├── aff_sec.dbf
│   ├── aff_sec.prj
│   ├── aff_sec.shp
│   ├── aff_sec.shx
│   ├── grid_state_dist.csv
│   ├── metro_data_bangalore.csv
│   ├── metro_data.csv
│   ├── metro_data_hyderabad.csv
│   ├── metro_data_kolkata.csv
│   ├── metro_data_mumbai.csv
│   ├── test_metro_data_bangalore.csv
│   └── town_data.csv
└── village
    └── dataset_index_groupm_vill_v1.csv

12 directories, 230 files
```

multiple versions, shapefile dependancies, csv and vector files of the same data, slight changes goes into a new file with each having similar extensions.

Instead of keeping all attributes in all wip layers, have a data_master table and take primary keys in the subsequent wip layers,
can later create spatial/non-spatial views to fetch joined tables.

csv with all attributes are large and adding a geometry column and making a geojson would only increase the file size.

geojson/shapefile:

* no indexing with geojson, shapefile depending on how you export the data .shx may or may not be there.

    (example: `/filepath/to/dataset/input/dataset_bangalore_test1.shp`)

* QGIS, Python, R, Postgres

```bash
$ ogrinfo ./bangalore_poc_wip.gpkg

INFO: Open of './bangalore_poc_wip.gpkg' using driver 'GPKG' successful.

1: s0_poc_boundary (Polygon)
2: s1_osm_major_roads (Multi Line String)
3: s2_osm_major_roads_poly (Multi Polygon)
4: s3a_major_segments (Multi Polygon)
5: s3b_osm_major_roads_poly_lines (Multi Line String)
6: s4_qchainage_points (Point)
7: s5_qchainage_voronoi (Polygon)
8: s6_roads_angles_major_segments_vertices (Point)
9: s7_roads_minor_segments (Multi Polygon)
```

* `project_inputs.gpkg`
* `project_wip.gpkg`
* `project_outputs.gpkg`

____________________________________________________________________________________________________________________________________________

### `File imports for CartoDB`

```bash
$ ogrinfo ./Election.gpkg

INFO: Open of `Election.gpkg' using driver `GPKG' successful.

1: senate_p (Multi Polygon)
2: school_p (Multi Polygon)
3: regent_p (Multi Polygon)
4: precinct_p (Multi Polygon)
5: ward_p (Multi Polygon)
6: congress_p (Multi Polygon)
7: pollpnts_x (Point)
8: educat_p (Multi Polygon)
9: township_p (Multi Polygon)
10: commiss_p (Multi Polygon)
11: assembly_p (Multi Polygon)
```

after uploading to carto, it automatically detects datasets and added to dashboard with
`filename_layername` format.


![](./carto.png)

____________________________________________________________________________________________________________________________________________

### `Load only parts of vector data onto memory`

Read only part of data from layers on the geopackage file using an sql query.
It's possible to apply few functions as well on geometries.

[GeoPackage-py](https://github.com/nsh-764/GeoPackage-py)

```python
In [1]: con = sqlite3.connect('/Volumes/Samashti-MacOS/Users/nikhil/nikhil_sc/temp/india_villages_master_2011.gpkg')

In [2]: fiona.listlayers(file)
Out[2]:
['data_master',
 'village_points',
 'voronoi_polygons',
 'view_india_village_points',
 'view_india_village_voronoi',
 'village_codes_mapping']

In [3]: cursorObj = con.cursor()

In [4]: cursorObj.execute('SELECT count(*) FROM voronoi_polygons')
Out[4]: <pysqlite2.dbapi2.Cursor at 0x11bb0df10>

In [5]: cursorObj.fetchall()
Out[5]: [(640330,)]

In [6]: gdf = gpkg.read_gpkg('SELECT * FROM view_india_village_voronoi WHERE state_name = "Karnataka"', file)

In [7]: gdf.head()
Out[7]:
    index      id country_name  ...  year total_households                                           geometry
0  169177  607805        India  ...  2011              310  (POLYGON ((75.63495231662536 15.79339781235389...
1  169270  607806        India  ...  2011             1733  (POLYGON ((75.65266026393108 15.79250088599703...
2  169590  607856        India  ...  2011              955  (POLYGON ((75.84390554881334 15.71628267470884...
3  170048  607883        India  ...  2011              972  (POLYGON ((75.93568917228413 15.72163493546362...
4  170325  607884        India  ...  2011              129  (POLYGON ((75.94284328924927 15.71516393874463...

[5 rows x 17 columns]

In [8]: gdf.shape
Out[8]: (29340, 17)
```

____________________________________________________________________________________________________________________________________________

### `Samples, default colour styles and other attributes`

Save qgis colour style and othe layer attributes to database, so when loaded the layer style gets loaded by default.

for each layer, a default layer style can be saved, along with any other styles that can be used for the layers.

```bash
$ ogrinfo ./dataset_name_index.gpkg

INFO: Open of './dataset_name_index.gpkg' using driver 'GPKG' successful.

1: dataset_name_index_v0 (Point)
2: dataset_name_index_v1 (Point)
3: layer_styles (None)

```

(qgis)

____________________________________________________________________________________________________________________________________________

## `What needs to be done?`

* python, R module to help implement few non-existant features.

* having file.meta (json) file/layer along with file.gpkg (with python, R module)

    (dataset has a gpkg_contents table for meta.)
    ```bash
    ['gpkg_spatial_ref_sys',
     'gpkg_contents',
     'gpkg_ogr_contents',
     'gpkg_geometry_columns',
     'gpkg_tile_matrix_set',
     'gpkg_tile_matrix',
     'gpkg_extensions',
     'sqlite_sequence',

     'dataset_name_index_v0',
     'dataset_name_index_v1',
     'layer_styles',

     'rtree_dataset_name_index_v0_geom',
     'rtree_dataset_name_index_v0_geom_rowid',
     'rtree_dataset_name_index_v0_geom_node',
     'rtree_dataset_name_index_v0_geom_parent',
     'rtree_dataset_name_index_v1_geom',
     'rtree_dataset_name_index_v1_geom_rowid',
     'rtree_dataset_name_index_v1_geom_node',
     'rtree_dataset_name_index_v1_geom_parent']
    ```

    geopackagepy:

        * query datasets using sql to load spatial data

        (pymodule)

        * handle non-spatial data consistent with spatial layers

        * creating spatial views

        * standardizing using of file meta

    (table plus)


* testing usage of multi-layer format files in our workflows.


____________________________________________________________________________________________________________________________________________

### Conversions:

* convert a shapefile to geopackage

    ```$ ogr2ogr -f GPKG filename.gpkg abc.shp```

* all the files (shapefile/geopackage) will be added to one geopackage.

    ```$ ogr2ogr -f GPKG filename.gpkg ./path/to/dir```

* add geopackage to postgres database

    ```$ ogr2ogr -f PostgreSQL PG:"host=localhost user=user dbname=testdb password=pwd" filename.gpkg layer_name```


[ns3](https://github.com/nsh-764/ns3)
