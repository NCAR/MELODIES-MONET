MODIS Satellite Data
====================

This guide describes how to process MODIS (Moderate Resolution Imaging Spectroradiometer)
Level 2 aerosol data in MELODIES MONET. MODIS provides global aerosol optical depth (AOD)
observations from both the Terra and Aqua satellites.

Overview
--------

MELODIES MONET supports MODIS Level 2 Collection 6.1 aerosol products:

* **MOD04_L2** - Terra MODIS Aerosol Product (10:30 AM local equatorial crossing time)
* **MYD04_L2** - Aqua MODIS Aerosol Product (1:30 PM local equatorial crossing time)

These products contain aerosol optical depth retrieved using the Dark Target and
Deep Blue algorithms, providing near-global coverage at 10 km resolution.

Data Access
-----------

MODIS aerosol data can be obtained from NASA Earthdata:

* `NASA Earthdata Search <https://search.earthdata.nasa.gov/>`_
* `LAADS DAAC <https://ladsweb.modaps.eosdis.nasa.gov/>`_

File Naming Convention
^^^^^^^^^^^^^^^^^^^^^^

MODIS L2 files follow this naming pattern::

    M?D04_L2.AYYYYDDD.HHMM.0CC.timestamp.hdf

Where:

* ``M?D04_L2`` - Product identifier (MOD04_L2 for Terra, MYD04_L2 for Aqua)
* ``AYYYYDDD`` - Acquisition date (A = Aqua/Terra, YYYY = year, DDD = day of year)
* ``HHMM`` - Acquisition time (UTC)
* ``0CC`` - Collection version (e.g., 061 for Collection 6.1)
* ``timestamp`` - Production timestamp
* ``.hdf`` - HDF4 file format

Example: ``MOD04_L2.A2020253.1830.061.2020254021156.hdf``

Recommended Directory Structure
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Organize MODIS files by satellite and year for efficient processing::

    $HOME/Data/MODIS/
    ├── Terra/
    │   └── C61/
    │       └── 2020/
    │           ├── 253/
    │           │   ├── MOD04_L2.A2020253.*.hdf
    │           │   └── ...
    │           └── 254/
    │               └── ...
    └── Aqua/
        └── C61/
            └── 2020/
                └── ...

Quick Start
-----------

1. **Create a YAML control file** specifying your analysis parameters
2. **Run the processing script** to grid MODIS swath data
3. **Output gridded NetCDF** for analysis or model comparison

Example YAML Configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: yaml

    analysis:
      start_time: '2020-09-09'
      end_time: '2020-09-12'
      time_interval: '24h'
      output_dir: $HOME/Plots
      debug: True
      regrid: True
      target_grid: obs_grid

    obs_grid:
      start_time: '2020-09-09'
      end_time: '2020-09-12'
      ntime: 72
      nlat: 180
      nlon: 360

    obs:
      Terra_MODIS:
        obs_type: 'sat_swath_clm'
        sat_type: 'modis_l2'
        filename: $HOME/Data/MODIS/Terra/C61/2020/*/MOD04_L2.*.hdf
        variables:
          AOD_550_Dark_Target_Deep_Blue_Combined:
            minimum: 0.0
            maximum: 10.0
            scale: 0.001
            units: none

Example Processing Script
^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    from melodies_monet import driver

    # Initialize analysis
    an = driver.analysis()
    an.control = 'control_modis_l2.yaml'
    an.read_control()

    # Open model data (if pairing with model)
    an.open_models()

    # Setup observation grid
    an.setup_obs_grid()

    # Setup regridders for model-obs pairing
    an.setup_regridders()

    # Process each time interval
    for time_interval in an.time_intervals:
        print(f'Processing: {time_interval}')
        an.open_obs(time_interval=time_interval)
        an.update_obs_gridded_data()

    # Normalize gridded data
    an.normalize_obs_gridded_data()

    # Save to NetCDF
    an.obs_gridded_dataset.to_netcdf('MODIS_gridded.nc')

Processing Workflow
-------------------

The MODIS processing workflow consists of these steps:

1. File Discovery and Time Subsetting
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

MELODIES MONET uses the ``subset_MODIS_l2()`` function to filter MODIS files
by time interval based on the filename timestamp. This enables efficient
processing of large data archives.

2. Data Loading
^^^^^^^^^^^^^^^

The MONETIO library (``mio.sat._modis_l2_mm``) reads MODIS HDF files and extracts:

* **Latitude/Longitude** - Geolocation arrays
* **Scan_Start_Time** - Observation timestamps
* **AOD variables** - Aerosol optical depth retrievals

The data is returned as an ``OrderedDict`` of xarray Datasets, keyed by datetime strings.

3. Quality Filtering (Optional)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Apply quality filters using the ``filter_dict`` option:

.. code-block:: yaml

    obs:
      Terra_MODIS:
        data_proc:
          filter_dict:
            Quality_Assurance_Land:
              oper: '>='
              value: 3

4. Gridding
^^^^^^^^^^^

Swath observations are accumulated onto a uniform latitude-longitude-time grid:

* Grid cells are defined by ``obs_grid`` parameters (ntime, nlat, nlon)
* Multiple observations within a grid cell are averaged
* Observation counts per grid cell are tracked

5. Output
^^^^^^^^^

The gridded dataset contains:

* ``{obs}_{variable}_data`` - Gridded AOD values
* ``{obs}_{variable}_count`` - Number of observations per grid cell

Available MODIS Variables
-------------------------

The primary aerosol variable is:

**AOD_550_Dark_Target_Deep_Blue_Combined**
    Combined Dark Target and Deep Blue AOD at 550 nm. This merged product
    provides the best spatial coverage by using Dark Target over vegetated
    and dark surfaces and Deep Blue over bright surfaces (deserts, urban areas).

Additional variables available in MOD04_L2/MYD04_L2 include:

* ``Optical_Depth_Land_And_Ocean`` - Dark Target AOD
* ``Deep_Blue_Aerosol_Optical_Depth_550_Land`` - Deep Blue AOD over land
* ``Angstrom_Exponent_1_Ocean`` - Angstrom exponent (ocean)
* ``AOD_550_Dark_Target_Deep_Blue_Combined_QA_Flag`` - Quality assurance flags

Model Pairing
-------------

To compare MODIS observations with model output, add a model section with mapping:

.. code-block:: yaml

    model:
      MERRA2:
        mod_type: reanalysis
        files: $HOME/Data/MERRA2/tavg1_2d_aer_Nx/*nc4
        regrid:
          base_grid: $HOME/Data/Grids/merra2_grid.nc
          method: bilinear
        mapping:
          Terra_MODIS:
            TOTEXTTAU: AOD_550_Dark_Target_Deep_Blue_Combined
          Aqua_MODIS:
            TOTEXTTAU: AOD_550_Dark_Target_Deep_Blue_Combined

Models tested with MODIS:

* **MERRA2** - NASA reanalysis (TOTEXTTAU variable)
* **CAM-chem FV** - CESM atmospheric chemistry model
* **WRF-Chem** - Regional weather/chemistry model

Best Practices
--------------

Time Interval Selection
^^^^^^^^^^^^^^^^^^^^^^^

* Use ``time_interval: '24h'`` for daily processing to manage memory
* Shorter intervals (e.g., ``'6h'``) may be needed for very large domains

Grid Resolution
^^^^^^^^^^^^^^^

* ``nlat: 180, nlon: 360`` gives 1-degree resolution (global)
* ``nlat: 720, nlon: 1440`` gives 0.25-degree resolution (higher detail)
* Balance resolution with available memory and processing time

Quality Control
^^^^^^^^^^^^^^^

* Apply minimum/maximum bounds to filter unrealistic values
* The ``scale: 0.001`` factor converts integer-stored AOD to physical units
* Consider filtering by quality flags for research applications

Example: Processing Both Terra and Aqua
---------------------------------------

Process both MODIS sensors for maximum temporal coverage:

.. code-block:: yaml

    obs:
      Terra_MODIS:
        obs_type: 'sat_swath_clm'
        sat_type: 'modis_l2'
        filename: $HOME/Data/MODIS/Terra/C61/2020/*/MOD04_L2.*.hdf
        variables:
          AOD_550_Dark_Target_Deep_Blue_Combined:
            minimum: 0.0
            maximum: 10.0
            scale: 0.001
            units: none

      Aqua_MODIS:
        obs_type: 'sat_swath_clm'
        sat_type: 'modis_l2'
        filename: $HOME/Data/MODIS/Aqua/C61/2020/*/MYD04_L2.*.hdf
        variables:
          AOD_550_Dark_Target_Deep_Blue_Combined:
            minimum: 0.0
            maximum: 10.0
            scale: 0.001
            units: none

Troubleshooting
---------------

No files found
^^^^^^^^^^^^^^

* Verify the filename glob pattern matches your file naming
* Check that files exist in the specified directories
* Ensure time interval covers the file timestamps

Memory errors
^^^^^^^^^^^^^

* Reduce the time interval (e.g., from ``'24h'`` to ``'6h'``)
* Process a smaller spatial domain
* Reduce grid resolution

Empty output
^^^^^^^^^^^^

* Check that MODIS files contain data for your region of interest
* Verify variable names match those in the HDF files
* Enable ``debug: True`` for additional output

See Also
--------

* :doc:`/users_guide/supported_datasets` - Full list of supported observations and models
* :doc:`/appendix/modis_yaml` - MODIS YAML configuration reference
* :doc:`/appendix/yaml` - Complete YAML configuration reference
* :doc:`/examples/intro_examples` - Additional examples
