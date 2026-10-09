Development Team
================

MELODIES MONET development is a collaboration between NOAA Chemical Sciences 
Laboratory (CSL), NOAA Air Resources Laboratory (ARL), NOAA National Weather 
Service Environmental Modeling Center (NWS EMC), NOAA Global Systems 
Laboratory (GSL), and NSF NCAR Atmospheric Chemistry Observations and Modeling 
(ACOM) Laboratory. The representative leads for each organization are below.

===============  =============================
Organization     Representative(s)
===============  =============================
NOAA CSL         Rebecca Schwantes
NOAA ARL         Zachary Moon
NOAA NWS EMC     Barry Baker
NOAA GSL         Jordan Schnell
NSF NCAR/ACOM    Louisa Emmons, David Fillmore
===============  =============================

Code Reviewers
--------------

================== =============== ========================================================
Reviewer           GitHub Username Expertise
================== =============== ========================================================
Zachary Moon       zmoon           Docs, Connections to MONET and MONETIO, CI tests
David Fillmore     dwfncar         Satellite obs, Plots, Stats, Connection to METplus
Colin Harkins      colin-harkins   Docs, Aircraft obs, Plots, Stats
Louisa Emmons      lkemmons        Docs, Aircraft obs, Plots, Stats
Rebecca Schwantes  rschwant        Docs, Surface and aircraft obs, Plots, Stats
Maggie Bruckner    mbruckner-work  Docs, Satellite obs, Plots, Stats
Rebecca Buchholz   rrbuchholz      Docs, Satellite obs, Plots, Stats
Pablo Lichtig      blychs          Docs, Satellite and surface obs, Plots, Stats
Quazi Ziaur Rasool quaz115         Docs, Aircraft obs, Plots, Stats
Beiming Tang       btang1          Docs, Surface and sonde obs, Plots, Stats
================== =============== ========================================================

Development Team Members
------------------------

Below is a list of people who have contributed to MELODIES MONET along with 
their current and future development goals.

**Mackenzie Arnold:**
I’m a summer intern at CIRES/NOAA GSL working on model verification of smoke-forecast
models. I plan to help review the code, work to improve the site-specific analysis, add
in a new capability to interactively view plots for individual surface sites online,
and help with various other aspects of development. 

**Megan Bela:**
I am a research scientist at CIRES/NOAA CSL working to improve process-level
understanding and representations of fire emissions, plume rise, and chemistry
in regional coupled chemistry-meteorology models. My plans include testing and
expanding the capability of MELODIES MONET for evaluating simulations with
research and operational models of fire impacts on air quality and weather.

**Maggie Bruckner:**
I am an NRC postdoc associated with NOAA CSL. My development plans
primarily focus on adding capabilities for comparison of satellite observations to model
output and expanding data processing options. 

**Rebecca Buchholz:**
I am a Project Scientist at NSF NCAR/ACOM helping with the development of MELODIES MONET.
My development plans include incorporating satellite datasets such as MOPITT CO and
ground-based remote sensing observations such as from NDACC or TCCON; incorporating
model output from CESM2; and expanding the analysis of model comparisons with remote
sensing data.

**Patrick C. Campbell:**
I am a research assistant professor at George Mason University and a NOAA-Air
Resources Laboratory affiliate.  I have contributed to the base Community Multiscale
Air Quality (CMAQ) model analysis scripts used in MONET, used in support of development
of MELODIES MONET and for the evaluation of the NWS/NOAA National Air Quality
Forecasting Capability (NAQFC) at NOAA-ARL. My development plans include advanced
development of model evaluation and statistical analysis techniques, adding more surface
observational datasets, and adding the capability of pairing to 3D aircraft observations
(e.g., CMAQ-ICARTT) to MELODIES MONET.

**Louisa Emmons:**
I am a Scientist at NSF NCAR/ACOM and PI of the NSF Earthcube MELODIES grant.  I have been
working on comparisons of model results and observations for over 20 years and hope to
contribute to many aspects of the development. 

**David Fillmore:**
I am a software developer at NSF NCAR/ACOM and work on MELODIES MONET and the NASA CERES project.
My primary focus is adding functionality for satellite dataset analysis within MELODIES MONET,
in particular ungridded satellite observations on an orbital swath or geostationary disc view.
I will also be adding and maintaining a tests suite for unit/regression tests and tutorial
examples.

**Duseong Jo:**
I am a postdoc at NSF NCAR/ACOM. My development plans include expanding MELODIES-MONET to deal
with unstructured grids and related plotting tools, adding custom options for more flexibility,
and bringing in new regridding capabilities.

**Meng Li:**
I am a research scientist at CIRES/NOAA CSL developing the processing package of TROPOMI
NO2 L2 product. My development plans include adding the capabilities of reading the standard
TROPOMI NO2 L2 product released by KNMI, paring the satellite pixels to WRF-Chem, and expanding
the plotting and statistical analyses in satellite-model comparisons.

**Rebecca Schwantes:**
I am a research chemist at NOAA CSL coordinating the 
development of MELODIES MONET. My development plans include incorporating 
additional surface observational datasets, adding the capability of pairing 
to aircraft observations, and expanding plotting and statistics for analysis 
of aircraft data.

**Jun Zhang:**
I am a postdoc at NSF NCAR/ACOM. My research interests are at the UTLS region.
I am hoping to add cross-section plots (lat vs height) and also to incorporate MLS data
for comparison.

**Pablo Lichtig:**
I am a postdoc at NSF NCAR/ACOM. My development plans include adding TEMPO support,
working with remote sensing instruments from the surface and adding support for BoulderAir
and other surface networks, and expanding MELODIES-MONET to other regional and global
models.

**Quazi Ziaur Rasool**
I am a research scientist at CIRES/NOAA CSL helping with MELODIES-MONET development.
My development plans include incorporating new comparisons (already tested) for aircraft
observation datasets such as FIREX, ASIA-AQ, and AEROMMA with model output from WRF-Chem
(regional), UFS-AQM (global); and expanding the analysis of model-aircraft comparisons
with new visualizations (for e.g., curtain plots, spatial plots along aircraft tracks,
vertical profiles, time series with altitude) and new observations or model data pairing of
interest.

**Beiming Tang**
Dr. Beiming Tang is a postdoc at NOAA Air Resources Laboratory.
His research focuses on developing NOAA's Atmospheric Composition forecast model by advancing AI techniques, MELODIES MONET development, and supporting UFS-AQM evaluations.
For the development of MELODIES MONET, Beiming created surface multi-box plot, scorecard, and CSI plots, and ozonesonde plots and TOLNet plots.
