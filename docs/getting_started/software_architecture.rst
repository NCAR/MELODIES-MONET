Software Architecture
=====================

The User Interface
------------------
The main file users will need to update is the YAML input file. If you are 
unfamiliar with the YAML format check out 
`Chapter 2 of the YAML Specification Document <https://yaml.org/spec/1.1/#id857168>`__.
MELODIES MONET will read all user-specified information from this input YAML 
file. Users run MELODIES MONET by importing the driver script, creating an 
analysis class, reading in the YAML input file, opening the models, opening 
the observations, pairing the model and observations, creating the plots, and 
calculating the statistics. The exact commands to run MELODIES MONET are 
described in the :doc:`how_to_run` section of this tutorial.
All model and observational datasets are read into MELODIES MONET into a 
consistent format prior to analysis. The input YAML file allows users to 
specify a mapping dictionary with how to pair model and observation variable 
names. Unit conversions can also be specified in the input YAML file. These 
capabilities allow MELODIES MONET to evaluate a variety of models against a 
variety of observational datasets all within a common framework.


How MELODIES MONET works
------------------------

`Driver files <https://github.com/NCAR/MELODIES-MONET/blob/develop/melodies_monet/driver/>`__ 
includes the core code that "drives" MELODIES MONET. The driver files 
initializes several classes as shown in the schematic below. 

* **Analysis class** -- This class holds all information needed for the 
  analysis including all information from the YAML input file, all instances
  of the model class, all instances of the observation class, and all
  instances of the pairing class.
* **Model class** -- This class holds all information related to a single 
  model dataset including the model label, type, mapping dictionary for how 
  to pair the model variables with observational variables, plotting 
  information, and unit conversions as needed. The analysis class can hold 
  multiple instances of the model class.
* **Observation class** -- This class holds all information related to a 
  single observational dataset including the observation label, type, 
  plotting information, and unit conversions as needed. The analysis class can hold 
  multiple instances of the observation class.
* **Pairing class** -- This class holds all information related to a 
  model/observational pair. In MELODIES MONET all models are paired with 
  all observations listed in the input YAML file. Model results are 
  directly paired in both time and space to the observational dataset for 
  all variables listed in the mapping dictionary specified in the model 
  class.

After all of the relevant information is incorporated into the analysis class,
the plotting and stats routines in the driver can be called to generate the 
plots and calculate statistics. The plotting and statistical routines will 
loop over all specified variables in the mapping table, all model/observational
pairs, and all domains. Where possible typical inputs into Matplotlib or 
Pandas are used in the input YAML file to make the plotting routines 
generalizable and easy to adjust figure, text, and mapping properties, so that 
**users can both produce hundreds of plots for quick diagnostic assessments and
have the flexibility to create publication quality plots**. 

The driver files, input YAML file, and example run scripts (jupyter notebook 
and bash) are configured in the same way to first define the analysis, model, 
observation, and pairing classes and second to create the plots and calculate 
the statistics. By maintaining a consistent structure for all of these files, 
we aim for the average user of MELODIES MONET to be able to easily understand 
the core code and contribute new components.

To learn more about current capabilities and future development objectives
see the :doc:`/users_guide/supported_datasets` ,
:doc:`/users_guide/supported_plots`, and
:doc:`/users_guide/supported_stats` pages in the
Background section of this guide.


.. figure:: /_static/MM_classes_connections.png
  :alt: diagram showing the Python classes defined and used in MELODIES MONET.
  
  Schematic of the classes defined in the Python code and used by MELODIES 
  MONET.
