MELODIES MONET
==============

**MELODIES MONET** is a joint project between NSF NCAR and NOAA to develop a 
modular framework that integrates existing and future diverse atmospheric 
chemistry observational datasets with chemistry model results for the 
evaluation of air quality and atmospheric composition. MELODIES MONET combines 
the Model EvaLuation using Observations, DIagnostics and Experiments Software 
(MELODIES) project at NSF NCAR with the Model and ObservatioN Evaluation Toolkit 
(MONET) project at NOAA to develop a python diagnostic package that is open 
source, generic, portable, and model-agnostic. Overall, the project provides a 
framework for evaluating a wide range of models in a more consistent manner. 
The tool is accessible to everyone including university and national 
laboratory researchers, as well as graduate students and postdocs.

The goal is to evaluate research, operational, and regulatory models against 
a variety of observations including surface, aircraft, and satellite data all 
within a common framework. MELODIES MONET uses the functionality already 
developed by MONETIO to read in multiple observational and model datasets and 
MONET to do pairing/analysis/plotting. For more information on MONET and 
MONETIO please refer to:
 
- https://monet-arl.readthedocs.io
- https://monetio.readthedocs.io

.. note::
   Please cite the following to acknowledge use of MELODIES MONET

   - Baker, B. and Pan, L.: Overview of the Model and Observation Evaluation 
     Toolkit (MONET) Version 1.0 for Evaluating Atmospheric Transport Models, Atmosphere, 8, 
     no. 11, 210, https://doi.org/10.3390/atmos8110210, 2017.

   - Two MELODIES MONET development papers are currently in preparation. We will 
     update this list when they are available.

Funding
-------

Funding for MELODIES MONET has been provided by NSF NCAR, NOAA ARL, NOAA CSL, 
NOAA GSL, and the following:

* This material is also based upon work supported by the NSF National Center
  for Atmospheric Research, which is a major facility sponsored by the U.S.
  National Science Foundation under Cooperative Agreement No. 1852977

* This work has been partly supported by the NOAA Cooperative Agreement with
  CIRES (grant nos. NA17OAR4320101 and NA22OAR4320151)

* NSF Earthcube Award Number 2026924 (2020-2024)

* Public Law 117-43 Disaster Relief Supplemental Appropriations Act 
  signed 30 September 2021 including $55M (ORF) related to the consequences 
  of hurricanes and wildfires in calendar years 2020 and 2021

* Funding for this project was partially provided by the Bi-Partisan
  Infrastructure Law (BIL)

* Colorado Air Quality Enterprise (AQE) grant #FEDA 2025*0171


Table of Contents
=================

.. toctree::
   :maxdepth: 4
   :caption: User's Guide

   users_guide/introduction
   users_guide/description
   users_guide/supported_datasets
   users_guide/supported_diagnostics
   users_guide/supported_plots
   users_guide/supported_stats
   users_guide/time_chunking
   users_guide/satellites/index
   users_guide/gridded_datasets
   users_guide/region_selection

.. toctree::
   :maxdepth: 4
   :caption: Getting Started

   getting_started/how_to_begin
   getting_started/new_to_python
   getting_started/installation
   getting_started/downloading_obs
   getting_started/software_architecture
   getting_started/how_to_run
   getting_started/tutorials


.. toctree::
   :maxdepth: 4
   :caption: Contribute
   
   develop/contribute
   develop/development_team
   develop/developers_guide
   develop/datasets

.. toctree::
   :maxdepth: 4
   :caption: Tutorial Examples

   examples/intro_examples
   examples/tutorial-data
   examples/airnow_wrfchem
   examples/airnow_wrfchem_reg
   examples/camchem
   examples/airnow_camchem_se
   examples/airnow_ufschem
   examples/ish_ufschem
   examples/ish_lite_ufschem
   examples/save_paired_data
   examples/read_paired_data
   examples/aircraft_pairing
   examples/AEROMMA_UFS-AQM_Plots
   examples/UWyoming_UFS-CHEM_Pairing
   examples/UWyoming_UFS-CHEM_pairing_loop_read
   examples/ufs-aqm-gml-ozonesonde
   examples/idealized

.. toctree::
   :maxdepth: 4
   :caption: Current Applications

   applications/publications
   applications/forecasts
   applications/other_tools

.. toctree::
   :maxdepth: 4
   :caption: Help and Reference

   api
   cli
   appendix/machine-specific-install
   appendix/yaml
   appendix/modis_yaml
   appendix/troubleshooting


