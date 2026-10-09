Selecting regions
=================

MELODIES-MONET has different ways to mask/select a specific region.

The easiest, and often most precise, is to have that region defined in the observations/paired data.
In this case, the variable/column that defines the region of interest should be selected as 
`domain_type` in the YAML file, and the name of the region to select should be provided as `domain_name`.

If the regional metadata are not available in the observations, another option is to provide a lonlat box, which
can be defined by setting `domain_type: auto-region:xxxxx`, where `xxxxx` can be `epa` or `giorgi`, or setting
as `custom:box`.
`Giorgi` regions and a rough, rectangular approximation to `EPA` regions have already been hardcoded into
MELODIES-MONET.
In the case of `EPA` regions, be aware that the approximation is quite rough to force it into a rectangular lonlat box, and although it is probably sufficient for plotting maps, it can lead to errors if used for anything else.
If `custom:box` is selected a lonlat box in the form of `bounds: [minlon, maxlon, minlat, maxlat]` needs to be provided in `domain_info` (see example below).
`custom:box` has, however, some limitations: `minlon` and `maxlon` need to be in the range of `[-180, 180]`, and the box cannot cross the antimeridian.

A third, and more sophisticated option, consists in utilizing the optional dependency `regionmask <https://regionmask.readthedocs.io/en/stable/>`__.
This is selected by defining `domain_type: custom:xxxxx`, where `xxxxx` can be `polygon`, `region` or `file`. 
All of these options require extra data provided in a `domain_info` keyword in the YAML file.
This option includes a multiplicity of capabilities:
* If `polygon` is selected, the vertices of one or more arbitrary polygons need to be provided (anti clockwise).
Currently no holes inside the polygon are supported.
* If `region` is selected, any defined region supported by `regionmask` can be provided in `domain_info`.
* If `file` is provided, the path to a shapefile/geojson file has to be provided. There is no need to decompress `.zip` shapefiles. Alternatively, the download URL can be provided, and the code will download the file automatically. Be aware that if a file with the same name is already in the working directory, it will be silently overwritten.


An example of the plotting part of an arbitrary plot for eact type of region is shown below:

.. code-block:: yaml

  domain_type: ["all",   "all",   "state_name", "epa_region", "auto-region:giorgi", "custom:box", "custom:polygon", "custom:polygon", "custom:defined-region", "custom:file", "custom:file"]
  domain_name: ["CONUS", "model", "CO",          "R8",        "CNA",                "R8box",      "onepoly",        "twopolys",       "colorado",      "denverfile",  "denverurl"]
  domain_info:
    R8box: 
      bounds: [-105.30, -105.1, 39.8, 40.2]
    onepoly:
      mask_info: [[-104.968, 39.47], [-104.618, 39.75], [-104.968, 40.06], [-105.32, 39.75]]
    twopolys: 
      mask_info: [[[-104.968, 39.47], [-104.618, 39.75], [-104.968, 40.06], [-105.32, 39.75]], [[-107.474, 37.693], [-108.037, 37.659], [-108.423, 36.97], [-106.444, 36.97], [-106.497, 37.473], [-107.4597, 37.4693]]]
    colorado:
      name_regiontype: natural_earth_v5_1_2.us_states_10
      region: CO
    denverfile:
      mask_path: "Colorado_County_Boundaries.zip"
      abbrevs: COUNTY
      name: Counties
      region_name: DENVER
    denverurl:
      mask_url: "https://hub.arcgis.com/api/v3/datasets/66c2642209684b90af84afcc559a5a02_5/downloads/data?format=shp&spatialRefId=4269&where=1%3D1"
      abbrevs: "COUNTY"
      name: "Counties"
      region_name: "DENVER"
