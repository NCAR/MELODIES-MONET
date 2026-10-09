Aircraft Pairing
================

Requirements for Using Aircraft Data for Model Evaluation
---------------------------------------------------------

Using aircraft or other field campaign data requires users to follow the 
data policy provided for each dataset. Please review this data policy 
carefully for each dataset you use for model evaluation. Generally, this 
means that you are expected to contact all instrument PI and co-PIs for all 
individual observations that you use prior to using their data in a 
publication, presentation, or other public facing document, alert them you 
are using their data, confirm your analysis approach with them, and offer 
co-authorship on any publications. These scripts demonstrate how to use the 
merge for model evaluation, but be sure to also download the original raw 
data files and review the header. This header info contains useful 
information like the instrument PIs and co-PIs, units, uncertainty, and 
other pertinent information about the instrument and dataset. Many of these 
datasets use letters to denote preliminary data (e.g., RA, RB) and numbers 
to denote final data (e.g., R0, R1). Be cautious when using preliminary 
data and always use the latest data available. 

We thank the following instrument teams for use of their 
`AEROMMA <https://csl.noaa.gov/projects/aeromma/>`_ data in 
this example. We also thank Youhua Tang (NOAA ARL, GMU) for providing 
UFS-AQM model data.

.. list-table:: AEROMMA Observations Used in This Example
   :widths: 20 40 20 20
   :header-rows: 1

   * - Observations
     - | Instrument  PI and co-PIs
       | (Affiliation)
     - Instrument
     - Reference
   * - | Meteorological
       | data for
       | pairing
     - | PI Charles Gatebe (NASA 
       | Ames Research Center) and
       | the MMS team (Paul Bui,
       | Jonathan Dean-Day, Rajesh
       | Poudyal, Cecilia Chang,
       | and Richard Kolyer)
     - | MMS - Meteorological
       | Measurement System
     - | `MMS Description <https://airbornescience.nasa.gov/mms>`_
   * - | NO, NO\ :sub:`2`\  
       | (Nitrogen oxides)
     - | Andrew Rollins (NOAA CSL),
       | Eleanor Waxman (NOAA CSL /
       | CIRES), & Kristen Zuraski
       | (NOAA CSL / CIRES)
     - | LIF - Laser Induced
       | Fluorescence
     - `Rollins et al., 2020 <https://doi.org/10.5194/amt-13-2425-2020>`_
   * - O\ :sub:`3`\  (Ozone)
     - | Kristen Zuraski (NOAA CSL /
       | CIRES) & Jeff Peischl
       | (NOAA GML / CIRES)
     - | Chemiluminescence 
       | (CL)
     - `CL Description <https://csl.noaa.gov/groups/csl7/instruments/noy_o3.html>`_
   * - | CO (Carbon 
       | Monoxide)
     - | Nell Schafer (NOAA CSL /
       | CIRES) & Jeff Peischl 
       | (NOAA GML / CIRES)
     - | Los Gatos Research  
       | (LGR) CO/N2O 
       | Analyzer
     - `LGR Description <https://csl.noaa.gov/groups/csl7/instruments/n2o_co.html>`_


General Procedure
-----------------

Users can use MELODIES MONET to pair aircraft observations to model output
and save the paired data for each flight as a netCDF. Users can then read 
these files back into MELODIES MONET to create plots and calculate statistics 
or use this paired data output file to do their own analysis. Pairing aircraft 
data takes time and memory, so it is recommended that users first pair the data 
and then produce the plots and statistics, so that you are not repairing every time 
you want to change something small during your analysis. Currently, we apply the 
following interpolation techniques and we aim to add more flexibility in future 
releases. We interpolate linearly in time, use the nearest neighbor approach in 
horizontal space, and use linear interpolation on pressure for the vertical space. 

All of the examples referred to below can be found in the 
``examples`` folder in the MELODIES MONET repository 
`on GitHub <https://github.com/NCAR/MELODIES-MONET>`__.

You can select the resampling time window. For testing purposes you can choose 
600 s and only pair 1--2 flight days to reduce memory constraints and run a 
Jupyter notebook. This Jupyter notebook 
``examples/jupyter_notebooks/AEROMMA_UFS-AQM_Aircraft_Pairing.ipynb``
pairs `AEROMMA <https://csl.noaa.gov/projects/aeromma/>`_ observational data with 
the UFS-AQM model with a long resampling window of 600 s for testing purposes. This 
Jupyter notebook calls this YAML file ``examples/yaml/control_aircraft_looping_AEROMMA_UFSAQM.yaml``,
which describes how to perform the analysis. This supplementary YAML file 
``examples/yaml/supplementary_yaml/supplementary_aircraft_looping_file_pairs_AEROMMA_UFSAQM.yaml``,
is also optionally called to describe which observations and model data files should be combined.

When you are ready for full analysis, you can reduce this resampling window (e.g., 30 s), 
update to pair over all days of a campaign, and submit a job on your linux machine like 
the example below, which will pair `AEROMMA <https://csl.noaa.gov/projects/aeromma/>`_ 
observational data with the UFS-AQM model and runs on the NOAA Hera HPC system. Submitting a job 
for pairing aircraft data is much faster, so this is the recommended approach except for testing 
or debugging.

This Python script ``examples/submit_jobs/run_aircraft_pairing_loop_AEROMMA.py`` 
pairs `AEROMMA <https://csl.noaa.gov/projects/aeromma/>`_ observational data with 
the UFS-AQM model with a short resampling window of 30 s for full analysis. This 
python script calls this YAML file ``examples/yaml/control_aircraft_looping_AEROMMA_UFSAQM-submit.yaml``,
which describes how to perform the analysis. This supplementary YAML file 
``examples/yaml/supplementary_yaml/supplementary_aircraft_looping_file_pairs_AEROMMA_UFSAQM-submit.yaml``,
is called to describe which observations and model data files should be combined.
This Bash script ``examples/submit_jobs/submit_hera_aircraft_AEROMMA.sh`` is an example for 
how to run this Python script on Hera (NOAA's HPC) and can be easily adapted to other computers as well.


Steps for Pairing Procedure
---------------------------

Submitting a python script job or using jupyter notebook processes the data in the same way 
with the following steps.

1) We import the ``loop_pairing`` function from ``melodies_monet.util.tools``

2) We read in a control file that explains all the pairing parameters

3) There are two options for providing the model and observation data for pairing

	* Option 1) Provides the info in a dictionary

	* Option 2) Provide the info in a supplementary yaml file. This option is 
	  specifically useful when submitting a job for the analysis as then you do not 
	  have to update the python script.

To support creating a dictionary or supplementary yaml file to determine the pairing, 
we have also created a function to find the time bounds in the observation file. To use 
this, first import the ``find_obs_time_bounds`` function from ``melodies_monet.util.tools``. 
Then specify the observational files and time variable name, call the ``find_obs_time_bounds`` 
function, and print bounds.













