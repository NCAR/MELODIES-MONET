Machine-specific Install
========================

NCAR HPC Derecho/Casper
------------------------

Below are specific recipes for getting started with MELODIES MONET
on the NCAR HPC, Derecho/Casper.

**Personal conda environment**

Use conda to create your own MELODIES MONET installation in a conda environment.
This creates a "stand-alone" instance 
of interdependent packages that will not interfere with your access to the main 
installation of Python on the system.
You can use the
`NCAR-maintained conda installation <https://arc.ucar.edu/knowledge_base/83853599>`__
to get access to ``conda`` by invoking::

    $ module load conda/latest

Or,
`install your own copy <https://docs.conda.io/projects/conda/en/latest/user-guide/install/linux.html>`__
of Miniconda or Anaconda.

If you plan to modify the MELODIES MONET or MONET/MONETIO
codebases, follow the :ref:`dev install instructions <dev-install-instructions>`.
Otherwise, follow the :ref:`user install instructions <user-install-instructions>`.

.. note::
   The easiest way of using MELODIES-MONET in Casper/Derecho is by using
   `NSF-NCAR's JupyterHub <https://jupyterhub.hpc.ucar.edu/>`__.
   Make sure to install `ipykernel`, which will let you select your newly installed MELODIES MONET
   environment in the JupyterHub
   
   If you are uncertain whether you have it, run::

       $ module load conda/latest
       $ conda activate melodies-monet
       $ conda install -c conda-forge ipykernel

   Now, when opening the JupyterHub, you should be able to select the melodies-monet kernel you created.


NOAA HPC Hera
-------------

Below is a specific recipe for how to set up all the necessary Python 
dependencies on the NOAA Hera machine. There are three steps to complete 
before you can use and develop MELODIES MONET on hera: **Step 1.** Install 
the conda package manager Anaconda/Miniconda, **Step 2.** Install MELODIES MONET,
and **Step 3.** link cartopy files.

We will use the conda package manager system to create a contained Python 
environment for running and developing MELODIES MONET. 

#. **Install Anaconda/Miniconda:** Follow the instructions
   `on the RDHPCS wiki <https://rdhpcs-common-docs.rdhpcs.noaa.gov/wiki/index.php/Anaconda>`__
   to download and run Anaconda/Miniconda on Hera. Tips for success:

   * You will need a NOAA HPC account to access the RDHPCS wiki link above.

   * Both Anaconda/Miniconda will work well for MELODIES MONET. See
     `conda instructions <https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html#installing-conda>`__
     to determine, which is the best option for you.
     
   * Pick a directory for your download and run the following wget command with 
     modifications if needed: ::
     
     $ wget -nH -m -nd https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh

   * Follow the instructions on `conda's website <https://conda.io/projects/conda/en/latest/user-guide/install/linux.html>`__,
     which is generally described below: ::
     
     $ bash Miniconda3-latest-Linux-x86_64.sh
     
     * Follow all prompts. Installing Anaconda/Miniconda on scratch is recommended 
       due to the limited space available on your home directory. Make sure you 
       change the default location.
     
     * Unless you want to initialize Anaconda/Miniconda yourself select "yes" 
       when asked "Do you wish the installer to initialize Miniconda3 by 
       running conda init?"

#. **Install MELODIES MONET:** If you plan to modify the MELODIES MONET or MONET/MONETIO
   codebases, follow the :ref:`dev install instructions <dev-install-instructions>`.
   Otherwise, follow the :ref:`user install instructions <user-install-instructions>`.

#. **Link the cartopy shapefiles:** Hera has download restrictions,
   so link the required cartopy shapefiles 
   for plotting by running the ``link_cartopy_files.sh`` script.

   If you have cloned the repo (e.g. following the dev install instructions)::
       
      $ cd MELODIES-MONET/python_env_ymls/hera
      $ ./link_cartopy_files.sh

   If you didn't clone the repo and don't want to::

      $ wget -O - https://raw.githubusercontent.com/NCAR/MELODIES-MONET/main/python_env_ymls/hera/link_cartopy_files.sh | bash


**You are ready to start using and developing MELODIES MONET!**


.. note::
   In the recent past [#hera_no_pypi]_, Hera did not allow downloading
   from PyPI. As a result, such ``pip install``\s commands failed since pip was not
   able to download setuptools from PyPI.
   As a (reluctant) workaround, ``python setup.py develop`` can be used instead
   for editable (development) installs of MELODIES MONET and MONET/MONETIO.


.. note::
   In the recent past, downloading a lot of dependent packages at once
   with conda on Hera led to stalling.
   To overcome this challenge, try installing packages individually::
  
        $ conda create --name melodies-monet python=3.11
        $ conda activate melodies-monet
        $ conda install -c conda-forge jupyterlab
        $ conda install -c conda-forge netcdf4
        $ conda install -c conda-forge wrf-python
        $ conda install -c conda-forge cartopy
        $ conda install -c conda-forge esmf
        $ conda install -c conda-forge monet
        $ conda install -c conda-forge monetio    

.. [#hera_no_pypi] Recent as of 12-Apr-2022. See :issue:`79`.
