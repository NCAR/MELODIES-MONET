Adding New Datasets
===================

Observations
------------

Surface
^^^^^^^

The MELODIES MONET tool has a :doc:`/cli` that can be used to download and create 
MELODIES MONET-ready datasets for: AirNow, AERONET, AQS, ISH, ISH-Lite, and OpenAQ. 
New surface observational datasets formally added to MELODIES MONET should be added 
to this Command Line Interface.

If you are interested in converting a new observational dataset to our netCDF format
on your own for testing within MELODIES MONET, please see the notes below.

* The dataset should have these dimensions (in this order):

  - ``time``
  - ``y`` (an optional singleton dimension, included for consistency with
    model surface datasets)
  - ``x`` (the site dimension)

* The dataset should have these coordinate variables:

  - ``time`` (UTC time, as timezone-naive ``datetime64`` format in xarray; ``time`` dim)
  - ``siteid`` (unique site identifier, as string; ``x`` dim)
  - ``latitude`` (site latitude, in degrees; ``x`` dim)
  - ``longitude`` (site longitude, in degrees; ``x`` dim)

* This variable is required for regulatory metrics,
  and can be optionally used for time series plots.
  Otherwise, you might omit it:

  - ``time_local`` (local time,
    usually local standard time, not including daylight savings,
    as timezone-naive ``datetime64`` format in xarray;
    note that this varies in both the ``time`` and ``x`` dimensions)

* It's good practice to include ``units`` attributes for your data variables,
  though this is not strictly required.
  Similarly, you may wish to include ``long_name``\ s.

* Site metadata variables (e.g. site name, site elevation, EPA region, etc.)
  should ideally be stored as varying only in the ``x`` dimension, to save space.

* If you have sub-hourly data, you may want to aggregate it to hourly,
  especially if different sites have different time resolutions.

Example abbreviated xarray representation for AirNow
demonstrating these qualities:

.. code-block:: text

   <xarray.Dataset>
   Dimensions:     (time: 289, y: 1, x: 2231)
   Coordinates:
     * time        (time) datetime64[ns] 2023-04-04 ... 2023-04-16
       siteid      (x) <U12 ...
       latitude    (x) float64 ...
       longitude   (x) float64 ...
   Dimensions without coordinates: y, x
   Data variables:
       NO2         (time, y, x) float64 ...
       time_local  (time, y, x) datetime64[ns] ...
       epa_region  (y, x) <U5 ...

You can examine the ``get_*`` functions in the :doc:`/cli`
(``melodies_monet/_cli.py``) for examples of converting observational datasets
in pandas DataFrame format to xarray Dataset format.

Aircraft, Sonde, Mobile, and Ground Campaign Data
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

New aircraft, sonde, mobile, and ground campaign datasets should work in the tool with no changes as long 
as the data format is NetCDF, ICARTT, or CSV. We are constantly working to generalize our code. If an issue 
arises, please post `on GitHub Issues <https://github.com/NCAR/MELODIES-MONET/issues>`__.

Satellite
^^^^^^^^^
Examples for reading satellite datasets can be
found in the ``monetio/sat`` folder in the MONETIO repository
`on GitHub <https://github.com/noaa-oar-arl/monetio>`__.
Not all MONETIO satellite readers have been incorporated into MELODIES MONET. Please see
:doc:`../users_guide/supported_datasets` to learn
which satellites have been incorporated and are available for each model.

Models
------
Examples for reading model datasets can be
found in the ``monetio/models`` folder in the MONETIO repository
`on GitHub <https://github.com/noaa-oar-arl/monetio>`__.
Not all MONETIO model readers have been incorporated into MELODIES MONET. Please see
:doc:`../users_guide/supported_datasets` to learn which models have been incorporated.

Support for additional models is also under developed.

Standard variables are required to be computed in each model reader for each capability including surface, aircraft, and satellite as specified in the table below.

.. list-table:: Required Variables for Model Readers
   :widths: 10 30 30 30
   :header-rows: 1

   * - Capability
     - | Variable Name 
       | in Code
     - Description
     - Additional Requirements
   * - Surface
     - | ``time``
       | ``latitude``
       | ``longitude``
     - | Time in ``datetime64[ns]`` format
       | Latitude in degrees
       | Longitude in degrees
     - | Provide only surface model data 
       | or if provide vertical model data, 
       | first level must be the level 
       | nearest to the surface.
       | All gases are in ppb and 
       | all aerosols are in µg/m3.
   * - Aircraft
     - | ``time``
       | ``latitude``
       | ``longitude``
       | ``pres_pa_mid``
       | ``temperature_k``
     - | Time in ``datetime64[ns]`` format
       | Latitude in degrees
       | Longitude in degrees
       | Mid-level pressure in pascals (Pa)
       | Mid-level temperature in kelvin (K)
     - | Provide vertical model data. 
       | All gases are in ppb and 
       | all aerosols are in µg/m3.
   * - Satellites
     - | ``time``
       | ``latitude``
       | ``longitude``
       | ``pres_pa_mid``
       | ``temperature_k``
       | ``dz_m``
       | ``surfpres_pa``
     - | Time in ``datetime64[ns]`` format
       | Latitude in degrees
       | Longitude in degrees
       | Mid-level pressure in pascals (Pa)
       | Mid-level temperature in kelvin (K)
       | Layer thickness in meters (m)
       | Surface pressure in pascals (Pa)
     - | Provide vertical model data.
