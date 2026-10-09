MODIS YAML Configuration Reference
===================================

This document provides a complete reference for YAML configuration options
specific to MODIS satellite data processing in MELODIES MONET.

Complete Example
----------------

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
        debug: False
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
        debug: False
        obs_type: 'sat_swath_clm'
        sat_type: 'modis_l2'
        filename: $HOME/Data/MODIS/Aqua/C61/2020/*/MYD04_L2.*.hdf
        variables:
          AOD_550_Dark_Target_Deep_Blue_Combined:
            minimum: 0.0
            maximum: 10.0
            scale: 0.001
            units: none

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

Analysis Section
----------------

Controls the overall analysis workflow.

.. list-table::
   :widths: 25 15 60
   :header-rows: 1

   * - Option
     - Required
     - Description
   * - ``start_time``
     - Yes
     - Analysis start time in ISO format (e.g., ``'2020-09-09'`` or ``'2020-09-09-00:00:00'``)
   * - ``end_time``
     - Yes
     - Analysis end time in ISO format
   * - ``time_interval``
     - Yes
     - Processing chunk size (e.g., ``'24h'``, ``'6h'``, ``'1h'``). Determines how many files are loaded at once.
   * - ``output_dir``
     - Yes
     - Output directory for plots and files. Shell variables (``$HOME``) are expanded.
   * - ``debug``
     - No
     - Enable debug output (default: ``False``)
   * - ``regrid``
     - No
     - Enable regridding for model-obs comparison (default: ``False``)
   * - ``target_grid``
     - No
     - Target grid for regridding. Use ``obs_grid`` to regrid model to observation grid.

Observation Grid Section
------------------------

Defines the uniform grid for accumulating swath observations.

.. list-table::
   :widths: 25 15 60
   :header-rows: 1

   * - Option
     - Required
     - Description
   * - ``start_time``
     - Yes
     - Grid start time (usually matches analysis start_time)
   * - ``end_time``
     - Yes
     - Grid end time (usually matches analysis end_time)
   * - ``ntime``
     - Yes
     - Number of time bins. For example: 72 bins over 3 days = 1-hour resolution.
   * - ``nlat``
     - Yes
     - Number of latitude bins. Coverage: -90 to 90 degrees. Examples: 180 = 1-degree, 720 = 0.25-degree
   * - ``nlon``
     - Yes
     - Number of longitude bins. Coverage: -180 to 180 degrees. Examples: 360 = 1-degree, 1440 = 0.25-degree

**Grid Resolution Examples:**

.. list-table::
   :widths: 20 20 30
   :header-rows: 1

   * - nlat/nlon
     - Resolution
     - Use Case
   * - 180/360
     - 1.0 degree
     - Global overview, fast processing
   * - 360/720
     - 0.5 degree
     - Moderate detail
   * - 720/1440
     - 0.25 degree
     - High detail, more memory required
   * - 1800/3600
     - 0.1 degree
     - Very high detail, regional studies

Observation Section
-------------------

Configuration for MODIS observation datasets.

Basic Options
^^^^^^^^^^^^^

.. list-table::
   :widths: 25 15 60
   :header-rows: 1

   * - Option
     - Required
     - Description
   * - ``obs_type``
     - Yes
     - Observation type. Use ``'sat_swath_clm'`` for MODIS L2 swath data.
   * - ``sat_type``
     - Yes
     - Satellite identifier. Must be ``'modis_l2'`` for MODIS Level 2 data.
   * - ``filename``
     - Yes
     - File path pattern with glob wildcards. Shell variables are expanded.
   * - ``debug``
     - No
     - Enable debug output for this observation (default: ``False``)

**obs_type Values for Satellite Data:**

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Value
     - Description
   * - ``sat_swath_clm``
     - Satellite swath data for column-integrated quantities (e.g., AOD)
   * - ``sat_swath_sfc``
     - Satellite swath data for surface quantities
   * - ``sat_swath_prof``
     - Satellite swath data with vertical profiles
   * - ``sat_grid_clm``
     - Gridded satellite data (Level 3)
   * - ``sat_grid_sfc``
     - Gridded satellite surface data

Variable Configuration
^^^^^^^^^^^^^^^^^^^^^^

Configure each variable under the ``variables`` key:

.. code-block:: yaml

    variables:
      AOD_550_Dark_Target_Deep_Blue_Combined:
        minimum: 0.0
        maximum: 10.0
        scale: 0.001
        units: none

.. list-table::
   :widths: 25 15 60
   :header-rows: 1

   * - Option
     - Required
     - Description
   * - ``minimum``
     - No
     - Minimum valid value. Values below are set to NaN.
   * - ``maximum``
     - No
     - Maximum valid value. Values above are set to NaN.
   * - ``scale``
     - No
     - Scale factor applied after min/max filtering. MODIS AOD uses ``0.001``.
   * - ``units``
     - No
     - Unit label for the variable (for documentation/plotting).
   * - ``obs_min``
     - No
     - Alternative to ``minimum`` for setting lower bound.
   * - ``obs_max``
     - No
     - Alternative to ``maximum`` for setting upper bound.
   * - ``nan_value``
     - No
     - Specific value to treat as NaN (e.g., ``-9999``).
   * - ``unit_scale``
     - No
     - Scale factor for unit conversion.
   * - ``unit_scale_method``
     - No
     - Method for unit conversion: ``'*'``, ``'/'``, ``'+'``, ``'-'``

**Common MODIS Variables:**

.. list-table::
   :widths: 40 60
   :header-rows: 1

   * - Variable Name
     - Description
   * - ``AOD_550_Dark_Target_Deep_Blue_Combined``
     - Combined Dark Target + Deep Blue AOD at 550 nm (recommended)
   * - ``Optical_Depth_Land_And_Ocean``
     - Dark Target AOD over land and ocean
   * - ``Deep_Blue_Aerosol_Optical_Depth_550_Land``
     - Deep Blue AOD over land (bright surfaces)

Data Processing Options
^^^^^^^^^^^^^^^^^^^^^^^

Optional filtering applied before gridding:

.. code-block:: yaml

    obs:
      Terra_MODIS:
        data_proc:
          filter_dict:
            Land_Ocean_Quality_Flag:
              oper: '>='
              value: 1

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Operator
     - Description
   * - ``==``
     - Equal to value
   * - ``!=``
     - Not equal to value
   * - ``>``
     - Greater than value
   * - ``<``
     - Less than value
   * - ``>=``
     - Greater than or equal to value
   * - ``<=``
     - Less than or equal to value
   * - ``isin``
     - Value is in list
   * - ``isnotin``
     - Value is not in list

Model Section
-------------

Configuration for model data to pair with MODIS observations.

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

.. list-table::
   :widths: 25 15 60
   :header-rows: 1

   * - Option
     - Required
     - Description
   * - ``mod_type``
     - Yes
     - Model type identifier (e.g., ``reanalysis``, ``cesm_fv``, ``wrfchem``)
   * - ``files``
     - Yes
     - File path pattern with glob wildcards
   * - ``regrid``
     - No
     - Regridding configuration (see below)
   * - ``mapping``
     - Yes
     - Variable mapping between model and observations

Regrid Options
^^^^^^^^^^^^^^

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Option
     - Description
   * - ``base_grid``
     - Path to NetCDF file defining the source grid
   * - ``method``
     - Regridding method: ``bilinear``, ``conservative``, ``nearest_s2d``

Mapping Configuration
^^^^^^^^^^^^^^^^^^^^^

Maps model variables to observation variables:

.. code-block:: yaml

    mapping:
      Terra_MODIS:                              # Observation label
        TOTEXTTAU: AOD_550_Dark_Target_Deep_Blue_Combined  # model_var: obs_var

File Path Patterns
------------------

MODIS files use a specific naming convention. Configure ``filename`` with appropriate wildcards:

**Terra MODIS (MOD04_L2):**

.. code-block:: yaml

    filename: $HOME/Data/MODIS/Terra/C61/2020/*/MOD04_L2.*.hdf

**Aqua MODIS (MYD04_L2):**

.. code-block:: yaml

    filename: $HOME/Data/MODIS/Aqua/C61/2020/*/MYD04_L2.*.hdf

**Pattern Elements:**

- ``$HOME`` - Expands to home directory
- ``*/`` - Matches any subdirectory (e.g., day-of-year folders)
- ``*.hdf`` - Matches any HDF file

Configuration Templates
-----------------------

Global 1-Degree Grid
^^^^^^^^^^^^^^^^^^^^

.. code-block:: yaml

    obs_grid:
      start_time: '2020-09-01'
      end_time: '2020-09-30'
      ntime: 720          # Hourly for 30 days
      nlat: 180           # 1-degree latitude
      nlon: 360           # 1-degree longitude

Regional High-Resolution
^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: yaml

    obs_grid:
      start_time: '2020-09-09'
      end_time: '2020-09-12'
      ntime: 72           # Hourly for 3 days
      nlat: 720           # 0.25-degree latitude
      nlon: 1440          # 0.25-degree longitude

Daily Aggregation
^^^^^^^^^^^^^^^^^

.. code-block:: yaml

    obs_grid:
      start_time: '2020-09-01'
      end_time: '2020-09-30'
      ntime: 30           # Daily for 30 days
      nlat: 180           # 1-degree latitude
      nlon: 360           # 1-degree longitude

Both Terra and Aqua
^^^^^^^^^^^^^^^^^^^

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

Validation
----------

Common configuration errors and solutions:

**Error: No files found**

- Check that ``filename`` pattern matches actual file paths
- Verify directory structure and file naming
- Test glob pattern: ``ls $HOME/Data/MODIS/Terra/C61/2020/*/MOD04_L2.*.hdf``

**Error: sat_type not recognized**

- Ensure ``sat_type: 'modis_l2'`` (with quotes)
- Check for typos in the satellite type string

**Error: Variable not found**

- Verify variable name exactly matches HDF file contents
- Use ``ncdump -h`` or HDFView to inspect file variables

**Memory issues**

- Reduce ``time_interval`` in analysis section (e.g., ``'6h'`` instead of ``'24h'``)
- Reduce grid resolution (smaller ``nlat``/``nlon`` values)
- Process shorter time periods

See Also
--------

* :doc:`/users_guide/satellites/modis` - MODIS user guide
* :doc:`/appendix/yaml` - Complete YAML reference for all options
