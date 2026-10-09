Installation/Requirements
=========================

Required dependencies [#yaml]_
------------------------------

- Python 3.6+ (3.9 -- 3.11 recommended)
- ``pandas`` 1 (most of the system works with pandas 2 as well, but some of the :doc:`/cli` commands for downloading observational datasets using MONETIO might fail)
- ``pyyaml`` (to read control files)
- ``monet``, which brings `many dependencies <https://monet-arl.readthedocs.io/en/stable/installing.html>`__
- ``monetio``, which brings `a few dependencies <https://monetio.readthedocs.io/en/stable/installing.html>`__

Optional dependencies
---------------------

- ``netcdf4`` (`from Unidata <https://unidata.github.io/netcdf4-python/>`__; most likely needed for reading model/obs datasets)
- ``wrf-python`` (needed in order to use the WRF-Chem reader; note that the version of ``wrf-python`` compatible with python=3.11 has known incompatibilities with newer ``netCDF4`` and ``setuptools`` versions — see *Incompatibilities* below)
- ``typer`` (to use the :doc:`/cli`)
- ``pooch`` (to enable automatic downloading of :doc:`tutorial datasets </examples/tutorial-data>`)
- ``regionmask`` (`for complex region masking support <https://regionmask.readthedocs.io/en/stable/>`__; can read shapefiles, geojson, arbitrary polygons and predefined regions.)
- ``metpy`` (for meteorological calculations)
- ``windrose`` (for windrose plots)
- ``statannotations`` (for statistical significance annotations on box and violin plots)


Incompatibilities
-----------------
- ``pandas=1`` is incompatible with ``matplotlib`` 3.9+.
- ``wrf-python``, at least in the official conda-forge package, is not available for Python 3.12+, until `this build issue <https://github.com/conda-forge/wrf-python-feedstock/pull/70>`__ is resolved.
- The version of ``wrf-python`` compatible with python=3.11 has known incompatibilities with newer ``netCDF4`` and ``setuptools`` versions. Note that currently, MELODIES MONET installs by default with Python 3.11 in conda. We have done some testing installing it from source with Python 3.14 (using the pip comand referred to in the :doc:`/develop/developers_guide`, which would avoid those issues, but note that testing this is still work in progress.
  This is an upstream issue. WRF-Chem users are strongly encouraged to use a pinned environment (see below).

.. _user-install-instructions:

General instructions
--------------------

.. note::
   If you are installing MELODIES MONET on NCAR Casper or NOAA Hera
   please refer to these machine specific instructions.

   - :ref:`NCAR Casper <appendix/machine-specific-install:NCAR HPC Derecho/Casper>`
   - :ref:`NOAA Hera <appendix/machine-specific-install:NOAA HPC Hera>`

If you are a user and are not planning to modify MELODIES MONET itself,
installing it is relatively simple. There are two methods available.

Option 1) Using Conda
^^^^^^^^^^^^^^^^^^^^^
We have recently created a conda-forge release of MELODIES MONET to make installation very simple 
with just 1 line of code below::

    $ conda create --name melodies-monet -y -c conda-forge \
      python=3.11 "netcdf4<1.7" "setuptools<70" "dask>=2024.2.1" wrf-python melodies-monet \
      "cartopy=0.24" metpy windrose statannotations jupyterlab

.. note::
   WRF-Chem users may experience failures with newer ``netCDF4`` or ``setuptools`` versions due to upstream
   ``wrf-python`` incompatibilities. If you encounter errors when opening WRF-Chem datasets,
   please use pinned versions (e.g., ``netCDF4<1.7``, ``setuptools<70``).


Option 2) Using Conda and GitHub
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
You are also welcome to install using our old method. The stable branch of MELODIES MONET (``main``) 
should always be the same as the conda-forge release of MELODIES MONET and be compatible with the
conda-forge releases of MONET/MONETIO.

First create and activate a conda environment::

    $ conda create --name melodies-monet python=3.11
    $ conda activate melodies-monet

Add dependencies from conda-forge::

    $ conda install -y -c conda-forge pyyaml pandas=2 monet monetio \
      "netcdf4<1.7" "setuptools<70" "dask>=2024.2.1" wrf-python \
      "cartopy=0.24" metpy windrose statannotations \
      typer pooch jupyterlab
   
Now, install the stable branch of MELODIES MONET to the environment::

    $ pip install --no-deps https://github.com/NCAR/MELODIES-MONET/archive/main.zip


.. note::
   If you are interested in modifying what MELODIES MONET can do,
   take a look at the :doc:`/develop/developers_guide`.


.. [#yaml] Examples of `conda <https://conda.io>`__
   `environment.yml files <https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html#creating-an-environment-from-an-environment-yml-file>`__
   that include a record
   of all the dependencies (direct and indirect) are available via the GitHub:

   - `NCAR Casper environment.yml <https://github.com/NCAR/MELODIES-MONET/tree/develop/python_env_ymls/casper>`__
   - `NOAA Hera environment.yml <https://github.com/NCAR/MELODIES-MONET/tree/develop/python_env_ymls/hera>`__