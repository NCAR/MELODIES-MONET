How To Begin
============

These instructions are for complete beginners to MELODIES MONET to help you get started.
We will go over the following concepts:

* `Python, GitHub, and Conda`_
* `User Guide`_
* `Installation`_
* `Running Tutorial Examples`_
* `Downloading Observations`_
* `Running Other Examples`_
* `Where To Get More Help`_
* `How to Contribute`_

Python, GitHub, and Conda
-------------------------

The source code for MELODIES MONET is stored and managed on GitHub: `<https://github.com/NCAR/MELODIES-MONET>`__.
MELODIES MONET uses MONET for pairing, plotting, and statistical calculations, which is also on on GitHub: 
`<https://github.com/NOAA-OAR-ARL/MONET>`__ and uses MONETIO for reading in model and observational datasets 
into a standard format, which is also on GitHub: `<https://github.com/NOAA-OAR-ARL/MONETIO>`__.

MELODIES MONET is primarily written in Python and as such uses a number of Python packages, which are described here:
:doc:`installation`. It is recommended to use Conda, Pip, or another Python package management system to handle these dependencies.
All of our instructions are for Conda, but you are welcome to adapt these instructions for other Python package management systems.

It is highly recommended that you have a general understanding of GitHub, Python, and Conda to use and especially develop 
MELODIES MONET. If these tools are new to you, we highly recommend you follow the tutorials described on :doc:`new_to_python` 
before going further in these instructions.

User Guide
----------

Please read through our "User's Guide" section, prior to using our tool. This guide provides lots of useful information on a
basic :doc:`../users_guide/introduction` and :doc:`../users_guide/description` including how we connect with MONET and MONETIO.
Supported models and observations are described in the :doc:`../users_guide/supported_datasets` section. Supported diagnostics
like calculating regulatory metrics are described in the :doc:`../users_guide/supported_diagnostics` section. Supported plots
and statistics available in MELODIES MONET are described in :doc:`../users_guide/supported_plots` and
:doc:`../users_guide/supported_stats` sections. Also more complex capabilities are described in the 
:doc:`../users_guide/time_chunking`, :doc:`../users_guide/gridded_datasets`, and :doc:`../users_guide/region_selection` sections.

Installation
------------

The general installation and requirements are explained in the :doc:`installation` section. There are also machine specific 
installation instructions in the "Help and Reference" section under :doc:`../appendix/machine-specific-install` for the NCAR 
HPC Derecho/Casper and the NOAA HPC Hera machines, which describe unique considerations for these systems. Occasionally, our
package dependencies become outdated. We do our best to keep these packages updated. If you run into errors using a Python 
package, please refer to 
`the Installation/Requirements section on our develop version of ReadTheDocs  <https://melodies-monet.readthedocs.io/en/develop/getting_started/installation.html>`__ 
to check for updates.

Running Tutorial Examples
-------------------------

The best way to get started with MELODIES MONET is to run our tutorial examples. Please refer to our
:doc:`../examples/intro_examples` page to learn about these examples and how to run them on your own system. 
These examples will automatically download observation and model datasets for you, so you do not need to do this as an 
initial step. It is strongly recommended that users test and run these tutorial examples prior to using MELODIES MONET 
to evaluate their own datasets, so that they can better understand the YAML input format, how to run MELODIES MONET, 
and the various capabilities available. We are working on adding more tutorial examples for later versions of
MELODIES MONET.

Downloading Observations
------------------------

Prior to running MELODIES MONET to evaluate your own model data, you must download the observations relevant for your use case.
Please refer to :doc:`downloading_obs` to learn how to download observations for your observation type. To learn which observations
are available in MELODIES MONET, please refer to :doc:`../users_guide/supported_datasets` in our "User's Guide" Section.

Running Other Examples
----------------------

Now that you have observation datasets and your own model results, you can test using MELODIES MONET to evaluate your own model
output. It is strongly recommended to copy an example for a similar type of analysis either from our tutorial examples described
above or our more general examples on our GitHub repository under the folder called 
`examples <https://github.com/NCAR/MELODIES-MONET/tree/main/examples>`__. Note that these examples unlike our tutorial examples, 
do not have archived model and observation datasets for you to automatically download and instead are just examples for how to run
different capabilities of the tool for you to adapt for use with your own datasets.

You can learn more about how to adapt these examples for your needs by referring to our very comprehensive :doc:`../appendix/yaml`
in the "Help and Reference" section and you can learn how MELODIES MONET works in connection with the YAML file format in the 
:doc:`software_architecture` section.

Then follow instructions in :doc:`how_to_run` for first testing your model evaluation for a subset of the data by running in a
Jupyter Notebook and then submitting a job for longer analysis periods.

Where To Get More Help
----------------------

Recent tutorials and workshops are listed in the :doc:`tutorials` section. In particular, the 
`MELODIES MONET hybrid Tutorial <https://www2.acom.ucar.edu/events/melodies-tutorial-2024>`__ on 
October 15-16, 2024, provided lectures on MELODIES MONET capabilities, hands on exercises for users to 
learn the tool, and break out sessions with the MELODIES MONET development team 
to learn how to add new features into the tool. The slides and recordings are all on the public
`Tutorial Agenda Website <https://www2.acom.ucar.edu/events/414344/agenda>`__. 
Please refer to these comprehensive slides for greater understanding about MELODIES MONET.

Please refer to the :doc:`../api`, to learn more about each submodule. You can use any of the submodules in 
MELODIES MONET, MONET, or MONETIO directly in your own Python routines if you wish.

How to Contribute
-----------------

Now that you know how to use MELODIES MONET, you may wish to add new features. For a summary of how to get involved
refer to our :doc:`../develop/contribute` section. If you would like to learn how to add new datasets, please refer
to our :doc:`../develop/datasets` section and if you would like to contribute to the code or docs development, please
refer to our :doc:`../develop/developers_guide` section. Please learn about our current developers by visiting our 
:doc:`../develop/development_team` section and let us know if you would like to join our development team!