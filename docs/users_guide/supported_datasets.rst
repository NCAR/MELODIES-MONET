Supported Datasets
==================

Supported models and observations are below. Please see
:ref:`Adding New Datasets <develop/datasets:Adding New Datasets>`
for advice on how to add new model and observational datasets to MELODIES MONET.

Supported Models
----------------

.. list-table:: Currently Connected Capabilities for Model Readers
   :widths: 20 20 30 30
   :header-rows: 1

   * - Model
     - Surface
     - Aircraft
     - Satellite
   * - `MERRA2 <https://gmao.gsfc.nasa.gov/reanalysis/MERRA-2/>`_
     - Yes
     - Needs testing
     - MODIS
   * - `WRF-Chem <https://www2.acom.ucar.edu/wrf-chem>`_
     - Yes
     - Yes
     - TEMPO, MOPITT, TROPOMI
   * - `CESM/CAM-chem FV <https://www2.acom.ucar.edu/gcm/cam-chem>`_
     - Yes
     - Needs testing
     - MOPITT, MODIS, TEMPO
   * - `CESM/CAM-chem SE <https://www2.acom.ucar.edu/gcm/cam-chem>`_
     - Yes
     - | Not functional. Regrid to
       | structured grid first.
     - | Not functional. Regrid to
       | structured grid first.
   * - `CMAQ <https://www.epa.gov/cmaq/>`_
     - Yes
     - Needs testing
     - Needs testing
   * - `UFS-AQM <https://github.com/ufs-community/ufs-srweather-app/wiki/Air-Quality-Modeling>`_
     - Yes
     - Yes
     - MOPITT
   * - `CAMx <https://www.camx.com/>`_
     - Yes
     - Needs testing
     - TEMPO, MOPITT
   * - `RAQMS <https://raqms-ops.ssec.wisc.edu/>`_
     - Yes
     - Needs testing
     - MOPITT, OMPS

In general, processing requires input to be in netCDF format. For the above 
models, scripts to configure the model data into a standard format for 
MELODIES MONET are available. If input datasets are in netCDF format and  
define latitude, longitude, pressure, and a datetime object, MELODIES MONET may be able 
to directly read the input files.

Please refer to the
`MELODIES MONET project board <https://github.com/orgs/NCAR/projects/150/>`__ 
to learn more about our current and future development plans.

Supported Observations
----------------------

Surface
^^^^^^^
To use these surface datasets in MELODIES MONET specify "obs_type" equal to "pt_sfc" in your YAML file. Currently, 
surface data in MELODIES MONET is paired horizontally using the nearest neighbor approach and temporally with 
exact time matching (e.g., if model data is provided hourly and observational data is provided 
hourly, these will pair together). More time interpolation options will be added in the future.

Available now:
   * `AirNow <https://www.airnow.gov/>`_ - Air quality data aggregated by AirNow
   * `AERONET <https://aeronet.gsfc.nasa.gov/>`_ - NASA AErosol RObotic NETwork

   * `AQS <https://www.epa.gov/aqs/>`_ - US EPA Air Quality System
   * `ISH and ISH-Lite <https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database>`_ - NOAA National Centers for Environmental Information (NCEI) Global Hourly - Integrated Surface Database
   * `OpenAQ <https://openaq.org/>`_ - Global, aggregated, harmonized public air quality data hosted by OpenAQ

Under Development:
   * `IMPROVE <https://vista.cira.colostate.edu/Improve/>`_ - Interagency Monitoring of Protected Visual Environments
   * `CRN <https://www.ncdc.noaa.gov/crn/>`_  - U.S. Climate Reference Network 
   * `TOLNet <https://www-air.larc.nasa.gov/missions/TOLNet/>`_ - Tropospheric Ozone Lidar Network
   * `CEMS <https://www.epa.gov/emc/emc-continuous-emission-monitoring-systems/>`_ - Air Emission Measurement Center (EMC) Continuous Emission Monitoring System
   * `Pandora <https://pandora.gsfc.nasa.gov/>`_ (`Pandonia Global Network <https://www.pandonia-global-network.org/>`_)

Please refer to the
`MELODIES MONET project board <https://github.com/orgs/NCAR/projects/150/>`__ 
under milestone "Surface and Aircraft Evaluation Version 2" to learn more about our current and future development plans.

.. note::

   The :doc:`/cli` can be used to download and create MELODIES MONET-ready datasets for:
   AirNow, AERONET, AQS, ISH, ISH-Lite, and OpenAQ.

Aircraft, Sonde, Mobile, and Ground Campaign Data
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Pairing capabilities include time, horizontal, and vertical interpolation. Horizontal interpolation uses the 
nearest neighbor approach. Vertical interpolation uses linear interpolation and nearest neighbor for extrapolation 
with a warning if users are pairing points above the model top, which is not recommended. Users can evaluate aircraft data, 
ozonesonde data, mobile or walking data, and single ground site data. To use these options in MELODIES MONET 
specify "obs_type" equal to "aircraft", "sonde", "mobile", or "ground" in your YAML file. The table 
below describes these options in more detail. Available datafile formats include NetCDF, ICARTT, and CSV.

.. list-table:: Description of YAML File Options for "obs_type" For Campaign Data
   :widths: 70 30
   :header-rows: 1

   * - "obs_type"
     - Description of Pairing
   * - "aircraft"
     - Aircraft - Time, horizontal, and vertical interpolation across the entire dataset.
   * - "sonde"
     - | Sonde - Vertical interpolation across the entire dataset. Time and 
       | horizontal interpolation at a fixed release time and location.
   * - "mobile"
     - Mobile - Time and horizontal interpolation across the entire dataset at the surface.
   * - "ground"
     - | Ground - Time interpolation across the entire dataset. Horizontal interpolation 
       | at a fixed location at the surface.

Tested datasets include the following: 
   * `FIREX-AQ <https://csl.noaa.gov/projects/firex-aq/>`_ - Fire Influence on Regional to Global Environments and Air Quality
   * `ATom <https://espo.nasa.gov/atom/content/ATom>`_ - ATmospheric Tomography Mission
   * `SUNVEx <https://csl.noaa.gov/projects/sunvex/>`_ - Southwest Urban NOx and VOC Experiment
   * `AEROMMA <https://csl.noaa.gov/projects/aeromma/>`_ - Atmospheric Emissions and Reactions Observed from Megacities to Marine Areas
   * `ASIA-AQ <https://espo.nasa.gov/asia-aq>`_ - Airborne and Satellite Investigation of Asian Air Quality 
   * `GML ozonesondes <https://gml.noaa.gov/ozwv/ozsondes/>`_ - NOAA Global Monitoring Laboratory (GML) ozonesondes 

MELODIES MONET is written generally enough that other field campaign datasets should work well in the tool with 
minimal adjustments.

Please refer to the
`MELODIES MONET project board <https://github.com/orgs/NCAR/projects/150/>`__ 
under milestone "Surface and Aircraft Evaluation Version 2" to learn more about our current and future development plans.

Satellite
^^^^^^^^^

MELODIES MONET supports evaluation against satellite observations for column-integrated
and profile retrievals. Satellite data processing includes swath-to-grid regridding,
quality filtering, and model pairing.

Available now:
   * `MODIS <https://modis.gsfc.nasa.gov/>`_ - Moderate Resolution Imaging Spectroradiometer aerosol products (MOD04_L2, MYD04_L2). See :doc:`satellites/modis` for detailed documentation.
   * `MOPITT <https://www2.acom.ucar.edu/facility/mopitt>`_ - Measurements of Pollution in the Troposphere (CO profiles)
   * `OMPS <https://ozoneaq.gsfc.nasa.gov/omps/>`_ - Ozone Mapping and Profiler Suite
   * `TROPOMI <http://www.tropomi.eu/>`_ - TROPOspheric Monitoring Instrument (NO2)
   * `TEMPO <https://tempo.si.edu/>`_ - Tropospheric Emissions: Monitoring of Pollution (NO2, HCHO)

To use satellite datasets in MELODIES MONET, specify ``obs_type`` as one of:
``sat_swath_clm``, ``sat_swath_sfc``, ``sat_swath_prof``, ``sat_grid_clm``, or ``sat_grid_sfc``
in your YAML file.

Please refer to the
`MELODIES MONET project board <https://github.com/orgs/NCAR/projects/150/>`__
under milestone "Remote Sensing Evaluation Version 2" to learn more about our current and future development plans.
