Supported Plots
===============

Model to Model Comparisons
--------------------------
Under development. 

Please refer to the
`MELODIES MONET project board <https://github.com/orgs/NCAR/projects/150/>`__ 
to learn more about current and future development plans.

Model to Observation Comparisons
---------------------------------

Surface Evaluation
^^^^^^^^^^^^^^^^^^
.. figure:: /_static/figures/plot_grp1.timeseries.PM2.5.2019-08-01_12.2019-08-11_12.all.CONUS.png

   **Timeseries** - Plot comparing one or more model results with one
   observation (y-axis) versus time (x-axis) over the analysis window with
   options to specify the domain, time (local or UTC), and averaging window.

.. figure:: /_static/figures/diurnal_ufschem_airnow_example.png
   :scale: 25 %
   :alt: Diurnal cycle of surface ozone (UFS-Chem v. AirNow)

   **Diurnal plot** - Plot comparing average daily cycle of one or more model
   results with an observation. X-axis shows the hour of the day (0--24) in local 
   time or UTC. The y-axis is the variable value. Data from all days within the 
   selected analysis window are grouped by hour and averaged, producing a single 
   representative 24-hour cycle rather than a continuous chronological time series. 

.. figure:: /_static/figures/plot_grp2.taylor.OZONE.2019-08-01_12.2019-08-11_12.all.CONUS.png
   :scale: 25 %

   **Taylor** - Taylor plot comparing one or more model results with one
   observation over the analysis window with options to specify the domain.      
     
.. figure:: /_static/figures/plot_grp3.spatial_bias.OZONE.2019-08-01_12.2019-08-11_12.all.CONUS.airnow_rrfs_diurnal_fires.png

   **Spatial Bias** - Difference plot of model - observations averaged over
   the analysis window with options to specify the domain. Defaults to average,
   but users can also optionally plot percentiles.

.. figure:: /_static/figures/plot_grp6.spatial_bias_exceedance.OZONE_reg.2019-08-01_13.2019-08-31_12.all.CONUS.airnow_cmaq_oper_exceedance.png

   **Spatial Bias Exceedance** - Difference plot of model - observations for the number of
   exceedances greater than the regulatory standard within the analysis window with options to specify
   the domain. This only works for regulatory calculations (regulatory = True) for variables "OZONE" and "PM2.5" and units must be in ppbv or μg m\ :sup:`-3`\, respectively, after the ``unit_scale`` option in the control file is applied.
   An exceedance occurs when MDA8 ozone is greater than 70 ppbv or 24 hour averaged PM\ :sub:`2.5` \ is
   greater than 35 ug m\ :sup:`-3`\.
     
.. figure:: /_static/figures/plot_grp4.spatial_overlay.OZONE.2019-08-01_12.2019-08-11_12.all.CONUS.airnow_rrfs_diurnal_fires.png

   **Spatial Overlay** - Model results in contours with observational
   results overlaid in markers averaged over the analysis window with
   options to specify the domain.  
  
.. note::
   For "spatial_bias", "spatial_overlay", and "spatial_bias_exceedance" plots, if ``domain_type`` is 'all' 
   and ``domain_name`` is 'CONUS' the following extent will be used for visual effect only: 
   ``[-130.0, -60.0, 25.0, 50.0]``. This extent will not impact any calculations like spatial 
   averages or statistics.

.. figure:: /_static/figures/plot_grp5.boxplot.OZONE.2019-08-01_12.2019-08-11_12.all.CONUS.png
   :scale: 25 %

   **BOX-plot** - BOX-plot comparing one or more model results with one
   observation over the analysis window with options to specify the domain.

.. figure:: /_static/figures/plot_grp7.multi_boxplot.OZONE.2019-09-05_06.2019-09-06_06.all.CONUS.png
   :scale: 35 %

   **Multi-BOX-plot** - Like BOX-plot, but bin data into multiple EPA regions.

.. figure:: /_static/figures/plot_grp5.multi_boxplot.t.2017-07-01_00.2017-07-03_00.state.MI.png
   :scale: 35 %

   **Multi-BOX-plot** - Like BOX-plot, but bin data into intervals based on a provided variable like observed temperature.

.. figure:: /_static/figures/plot_grp6.scorecard.OZONE.2019-09-05_06.2019-09-06_06.all.CONUS.png

   **Scorecard** - Compares two model outputs, evaluated against observations.
   The evaluation statistical parameters can be the Root Mean Square (RMSE),
   the Normalized Mean Bias (NMB) or the Index Of Agreement (IOA).

.. figure:: /_static/figures/plot_grp8.csi.OZONE.2019-09-05_06.2019-09-06_06.all.CONUS.Critical\ Success\ Index.png

   **Critical Success Index** Plot of the Critical Success Index, as commonly used in Forecast evaluation.

.. figure:: /_static/figures/plot_grp6.scatter_density.temp.2017-07-01_00.2017-07-03_00.state.MI_ish_lite_vs_ufschem_v1.png
   :scale: 25 %

   **Scatter Density** - Scatter density plot comparing one model results with one
   observation over the analysis window. This plot type has two options: a) scatter plot: model and observation values as scatter dots or markers, b) kernel density estimate (KDE) plot which visually represents the probability density of observation and model values as continuous variable (shown in the example figure above). Note: for multiple models being compared to one observation, each model-observation set would have a separate scatter plot.

.. figure:: /_static/figures/plot_grp6.rose_plot.ws.2017-07-01_00.2017-07-03_00.siteid.72539614815.png
   :scale: 20 %

   **Rose plot** - Wind rose if provide wind speed or polution rose if you provide another variable. In the wind rose plots, calm winds are plotted as an inner circle for wind direction and data is removed for pollution rose plots based on the threshold set in your yaml file.

   **Diurnal plot** - Plot comparing one or more model results with one observation (y-axis) versus time (x-axis) from 0--24 over the analysis window with options to specify the domain, time (local or UTC), and averaging window.

Please refer to the
`MELODIES MONET project board <https://github.com/orgs/NCAR/projects/150/>`__ 
under milestone "Surface and Aircraft Evaluation Version 2" to learn more about our current and future development plans.

Aircraft Evaluation 
^^^^^^^^^^^^^^^^^^^
Timeseries, Taylor, BOX-plots, and Scatter Density plots described above in Surface Evaluation can also be created for aircraft evaluation. 
Aircraft specific plots are described below:

.. figure:: /_static/figures/plot_grp1.timeseries.CO_LGR.2023-06-27_00.2023-06-28_23.all.LosAngeles.png

   **Timeseries with Altitude** - Identical to the Timeseries plot described above for surface evaluation. For aircraft evaluation,
   users can optionally plot altitude on the secondary right y-axis.

.. figure:: /_static/figures/plot_grp2.vertprofile.NO2_LIF.2023-06-27_00.2023-06-28_23.all.LosAngeles.png

   **Vertical Profile** - Plot comparing one or more model results with altitude (y-axis)
   versus  one observation (x-axis) over the analysis window.

.. figure:: /_static/figures/plot_grp3.violin.O3_CL.2023-06-27_00.2023-06-28_23.all.LosAngeles.png
   :scale: 15 %

   **Violin** - Violin plot comparing one or more model results with one
   observation over the analysis window.

.. figure:: /_static/figures/plot_grp5.curtain.O3_CL_RYERSON.2019-09-05_12.2019-09-06_00.all.CONUS_firexaq_vs_wrfchem_v4.2.png

   **Curtain** - Curtain plot comparing one model results with one
   observation over the analysis window. Note: for multiple models being compared to one observation, each model-observation set would have a separate curtain plot.

Please refer to the
`MELODIES MONET project board <https://github.com/orgs/NCAR/projects/150/>`__ 
under milestone "Surface and Aircraft Evaluation Version 2" to learn more about our current and future development plans.

Satellite Evaluation 
^^^^^^^^^^^^^^^^^^^^
Under development.

Please refer to the
`MELODIES MONET project board <https://github.com/orgs/NCAR/projects/150/>`__ 
under milestone "Satellite Evaluation Version 2" to learn more about our current and future development plans.
