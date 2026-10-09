Description of Tutorial Examples
================================

We have developed many examples to show case the flexibility 
and ease of MELODIES MONET that are described in this section. 
The model and observation datasets used to create these examples 
have been uploaded to a public archive and can be easily downloaded 
by users as described in the :doc:`tutorial-data` section. Users can 
refer to these examples to learn more about MELODIES MONET 
capabilities. Users can also test running these examples as described 
below in the section `How to Run These Examples On Your Own`_.

Four examples compare AirNow surface observations to model data:

* :doc:`airnow_wrfchem`
* :doc:`camchem`
* :doc:`airnow_camchem_se`
* :doc:`airnow_ufschem`

This example compares AirNow surface observations to model data for the regulatory metrics of MDA8 ozone and 24 hour PM\ :sub:`2.5`\:

* :doc:`airnow_wrfchem_reg`

Two examples compare ISH and ISH-lite surface observations to model data:

* :doc:`ish_ufschem`
* :doc:`ish_lite_ufschem`

These examples describe how to save paired data and read it back in:

* :doc:`save_paired_data`
* :doc:`read_paired_data`

Aircraft and sonde evaluation examples include the following:

* :doc:`aircraft_pairing`
* :doc:`AEROMMA_UFS-AQM_Plots`
* :doc:`UWyoming_UFS-CHEM_Pairing`
* :doc:`UWyoming_UFS-CHEM_pairing_loop_read`
* :doc:`ufs-aqm-gml-ozonesonde`

Idealized examples that are run as tests include those below:

* :doc:`idealized`

How to Run These Examples On Your Own
-------------------------------------

Users can also download the YAML input files and Jupyter notebooks and run 
them on their own system. This is an excellent method to test your set up and
get familiar with running MELODIES MONET scripts. The YAML input files for 
these examples will automatically download observation and model data as 
described in the :doc:`tutorial-data` section. Instructions for running 
these examples are shown below:

1) Follow the :ref:`Installation Instructions <getting_started/installation:Installation/Requirements>` 
   to install MELODIES MONET and activate your Conda environment.

2) Make a directory on your machine for these tutorial examples and go there::

    $ mkdir MM_tutorial
    $ cd MM_tutorial

3) Create a folder called code and clone the MELODIES MONET GitHub
   repository to this folder. This is just a reference folder of the code and 
   is not the code you are using to run MELODIES MONET::
   
    $ mkdir code
    $ cd code
    $ git clone https://github.com/NCAR/MELODIES-MONET
    $ cd .. [Now you are back in your tutorial folder]

4) Refer to the table below and copy the YAML input file and Jupyter Notebook File that
   you wish to test. For example, we copy the files for the AirNow and WRF-Chem example::

    $ cp code/MELODIES-MONET/docs/examples/airnow_wrfchem.ipynb .
    $ cp code/MELODIES-MONET/docs/examples/control_wrfchem_mech-0905_2.yaml .

5) Make a plots folder for each example you want to test::

    $ mkdir plots_airnow_wrfchem

6) Update the YAML file under "analysis" and "output_dir" to your own directory 
   (This is the directory the plots will be saved in)::

    $ {your user_directory}/MM_tutorial/plots_airnow_wrfchem

7) Make sure you have activated your Conda environment and run the Jupyter notebook.

.. list-table:: Current Examples And Their Corresponding YAML and Jupyter Notebook Files
   :widths: 20 40 40
   :header-rows: 1

   * - Example Name
     - YAML File Name
     - Jupyter Notebook Name
   * - AirNow and WRF-Chem
     - control_wrfchem_mech-0905_2.yaml
     - airnow_wrfchem.ipynb
   * - | AirNow and WRF-Chem 
       | Regulatory Calculations
     - control_wrfchem_mech-0905_2_reg.yaml
     - airnow_wrfchem_reg.ipynb
   * - AirNow and CAM-chem
     - control_camchem.yaml
     - camchem.ipynb
   * - | AirNow and CAM-chem SE 
       | (unstructured grid)
     - control_camchem_se.yaml
     - airnow_camchem_se.ipynb
   * - AirNow and UFS-CHEM
     - control_ufschem-example.yaml
     - airnow_ufschem.ipynb
   * - ISH and UFS-CHEM
     - control_ish_ufschem-example.yaml
     - ish_ufschem.ipynb
   * - ISH-LITE and UFS-CHEM
     - control_ish_lite_ufschem-example.yaml
     - ish_lite_ufschem.ipynb
   * - Saving Paired Data
     - control_wrfchem_saveandread.yaml
     - save_paired_data.ipynb
   * - Reading Paired Data
     - control_wrfchem_saveandread.yaml
     - read_paired_data.ipynb
   * - | AEROMMA and UFS-AQM: 
       | Read Paired Data and 
       | Create Plots
     - control_read_looped_aircraft_AEROMMA_UFS_AQM.yaml
     - AEROMMA_UFS-AQM_Plots.ipynb
   * - | Example for Pairing
       | University of Wyoming
       | data with UFS-Chem
     - control_looping_UWY_UFS_CHEM.yaml
     - UWyoming_UFS-CHEM_Pairing.ipynb
   * - | University of Wyoming
       | and UFS-Chem: Read Paired
       | Data and Create Plots
     - control_read_looped_aircraft_UWY_UFS_CHEM.yaml
     - UWyoming_UFS-CHEM_pairing_loop_read.ipynb
   * - | GML ozonesonde and 
       | UFS-AQM
     - control_ufsaqm_ozonesonde.yaml
     - N/A
   * - Idealized Synthetic Data
     - control_idealized.yaml
     - idealized.ipynb

Note: For the :doc:`ufs-aqm-gml-ozonesonde` example, there is no corresponding jupyter notebook. 
This example shows users how to run MELODIES MONET using the :doc:`the CLI </cli>`. (``melodies-monet run``).

Execution statistics
--------------------

.. nb-exec-table::
