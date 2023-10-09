# Copyright (C) 2022 National Center for Atmospheric Research and National Oceanic and Atmospheric Administration 
# SPDX-License-Identifier: Apache-2.0
#
"""
Drive the entire analysis package via the :class:`analysis` class.
"""
import monetio as mio
import monet as m
import os
import xarray as xr
import pandas as pd
import numpy as np
import datetime

from .util import write_util

__all__ = (
    "pair",
    "observation",
    "model",
    "analysis",
)


class pair:
    """The pair class.

    The pair class pairs model data 
    directly with observational data along time and space.
    """
    
    def __init__(self):
        """Initialize a :class:`pair` object."""
        self.type = 'pt_sfc'
        self.radius_of_influence = 1e6
        self.obs = None
        self.model = None
        self.model_vars = None
        self.obs_vars = None
        self.filename = None

    def __repr__(self):
        return (
            f"{type(self).__name__}(\n"
            f"    type={self.type!r},\n"
            f"    radius_of_influence={self.radius_of_influence!r},\n"
            f"    obs={self.obs!r},\n"
            f"    model={self.model!r},\n"
            f"    model_vars={self.model_vars!r},\n"
            f"    obs_vars={self.obs_vars!r},\n"
            f"    filename={self.filename!r},\n"
            ")"
        )

    def fix_paired_xarray(self, dset):
        """Reformat the paired dataset.
    
        Parameters
        ----------
        dset : xarray.Dataset
        
        Returns
        -------
        xarray.Dataset
            Reformatted paired dataset.
        """
        # first convert to dataframe
        df = dset.to_dataframe().reset_index(drop=True)

        # now get just the single site index
        dfpsite = df.rename({'siteid': 'x'}, axis=1).drop_duplicates(subset=['x'])
        columns = dfpsite.columns  # all columns
        site_columns = [
            'latitude',
            'longitude',
            'x',
            'site',
            'msa_code',
            'cmsa_name',
            'epa_region',
            'state_name',
            'msa_name',
            'site',
            'utcoffset',
        ]  # only columns for single site identificaiton

        # site only xarray obj (no time dependence)
        dfps = dfpsite.loc[:, columns[columns.isin(site_columns)]].set_index(['x']).to_xarray()  # single column index

        # now pivot df and convert back to xarray using only non site_columns
        site_columns.remove('x')  # need to keep x to merge later
        dfx = df.loc[:, df.columns[~df.columns.isin(site_columns)]].rename({'siteid': 'x'}, axis=1).set_index(['time', 'x']).to_xarray()

        # merge the time dependent and time independent
        out = xr.merge([dfx, dfps])

        # reset x index and add siteid back to the xarray object
        if ~pd.api.types.is_numeric_dtype(out.x):
            siteid = out.x.values
            out['x'] = range(len(siteid))
            out['siteid'] = (('x'), siteid)

        return out


class observation:
    """The observation class.
    
    A class with information and data from an observational dataset.
    """

    def __init__(self):
        """Initialize an :class:`observation` object."""
        self.obs = None
        self.label = None
        self.file = None
        self.obj = None
        """The data object (:class:`pandas.DataFrame` or :class:`xarray.Dataset`)."""
        self.type = 'pt_src'
        self.sat_type = None
        self.data_proc = None
        self.variable_dict = None

    def __repr__(self):
        return (
            f"{type(self).__name__}(\n"
            f"    obs={self.obs!r},\n"
            f"    label={self.label!r},\n"
            f"    file={self.file!r},\n"
            f"    obj={repr(self.obj) if self.obj is None else '...'},\n"
            f"    type={self.type!r},\n"
            f"    type={self.data_proc!r},\n"
            f"    variable_dict={self.variable_dict!r},\n"
            ")"
        )

    def open_obs(self, time_interval=None):
        """Open the observational data, store data in observation pair,
        and apply mask and scaling.

        Parameters
        __________
        time_interval (optional, default None) : [pandas.Timestamp, pandas.Timestamp]
            If not None, restrict obs to datetime range spanned by time interval [start, end].

        Returns
        -------
        None
        """
        from glob import glob
        from numpy import sort
        
        from . import tutorial

        if self.file.startswith("example:"):
            example_id = ":".join(s.strip() for s in self.file.split(":")[1:])
            files = [tutorial.fetch_example(example_id)]
        else:
            files = sort(glob(self.file))

        assert len(files) >= 1, "need at least one"

        _, extension = os.path.splitext(files[0]) 
        try:
            if extension in ['.nc', '.ncf', '.netcdf', '.nc4']:
                if len(glob(self.file)) > 1:
                    self.obj = xr.open_mfdataset(sort(glob(self.file)))
                else:
                    self.obj = xr.open_dataset(self.file[0])
            elif extension in ['.ict', '.icarrt']:
                self.obj = mio.icarrt.add_data(self.file)
        except ValueError:
            print('something happened opening file')

        self.mask_and_scale()  # mask and scale values from the control values
        self.filter_obs()

    def open_sat_obs(self,time_interval=None):
        """Methods to opens satellite data observations. 
        Uses in-house python code to open and load observations.
        Alternatively may use the satpy reader.
        Fills the object class associated with the equivalent label (self.label) with satellite observation
        dataset read in from the associated file (self.file) by the satellite file reader

        Parameters
        __________
        time_interval (optional, default None) : [pandas.Timestamp, pandas.Timestamp]
            If not None, restrict obs to datetime range spanned by time interval [start, end].

        Returns
        -------
        None
        """
        from .util import time_interval_subset as tsub
        
        try:
            if self.sat_type == 'omps_l3':
                print('Reading OMPS L3')
                self.obj = mio.sat._omps_l3_mm.read_OMPS_l3(self.file)
            elif self.sat_type == 'omps_nm':
                print('Reading OMPS_NM')
                if time_interval is not None:
                    flst = tsub.subset_OMPS_l2(self.file,time_interval)
                else: flst = self.file

                self.obj = mio.sat._omps_nadir_mm.read_OMPS_nm(flst)
                
                # couple of changes to move to reader
                self.obj = self.obj.swap_dims({'x':'time'}) # indexing needs
                self.obj = self.obj.sortby('time') # enforce time in order. 
                # restrict observation data to time_interval if using
                # additional development to deal with files crossing intervals needed (eg situtations where orbit start at 23hrs, ends next day).
                if time_interval is not None:
                    self.obj = self.obj.sel(time=slice(time_interval[0],time_interval[-1]))
                    
            elif self.sat_type == 'mopitt_l3':
                print('Reading MOPITT')
                self.obj = mio.sat._mopitt_l3_mm.read_mopittdataset(self.file, 'column')
            elif self.sat_type == 'modis_l2':
                from monetio import modis_l2
                print('Reading MODIS L2')
                self.obj = modis_l2.read_mfdataset(
                    self.file, self.variable_dict, debug=self.debug)

            elif self.label == 'tropomi_l2_no2':
                #from monetio import tropomi_l2_no2
                print('Reading TROPOMI L2 NO2')
                self.obj = mio.sat._tropomi_l2_no2_mm.read_trpdataset(
                    self.file, self.variable_dict, debug=self.debug)
            else:
                print('file reader not implemented for {} observation'.format(self.sat_type))
                raise ValueError
        except ValueError as e:
            print('something happened opening file:', e)
            return
        
    def filter_obs(self):
        """Filter observations based on filter_dict.
        
        Returns
        -------
            None
        """
        if self.data_proc is not None:
            if 'filter_dict' in self.data_proc:
                filter_dict = self.data_proc['filter_dict']
                for column in filter_dict.keys():
                    filter_vals = filter_dict[column]['value']
                    filter_op = filter_dict[column]['oper']
                    if filter_op == 'isin':
                        self.obj = self.obj.where(self.obj[column].isin(filter_vals),drop=True)
                    elif filter_op == 'isnotin':
                        self.obj = self.obj.where(~self.obj[column].isin(filter_vals),drop=True)
                    elif filter_op == '==':
                        self.obj = self.obj.where(self.obj[column] == filter_vals,drop=True)
                    elif filter_op == '>':
                        self.obj = self.obj.where(self.obj[column] > filter_vals,drop=True)
                    elif filter_op == '<':
                        self.obj = self.obj.where(self.obj[column] < filter_vals,drop=True)
                    elif filter_op == '>=':
                        self.obj = self.obj.where(self.obj[column] >= filter_vals,drop=True)
                    elif filter_op == '<=':
                        self.obj = self.obj.where(self.obj[column] <= filter_vals,drop=True)
                    elif filter_op == '!=':
                        self.obj = self.obj.where(self.obj[column] != filter_vals,drop=True)
                    else:
                        raise ValueError(f'Filter operation {filter_op!r} is not supported')
        
    def mask_and_scale(self):
        """Mask and scale observations, including unit conversions and setting
        detection limits.
        
        Returns
        -------
        None
        """
        vars = self.obj.data_vars
        if self.variable_dict is not None:
            for v in vars:
                if v in self.variable_dict:
                    d = self.variable_dict[v]
                    # Apply removal of min, max, and nan on the units in the obs file first.
                    if 'obs_min' in d:
                        self.obj[v].data = self.obj[v].where(self.obj[v] >= d['obs_min'])
                    if 'obs_max' in d:
                        self.obj[v].data = self.obj[v].where(self.obj[v] <= d['obs_max'])
                    if 'nan_value' in d:
                        self.obj[v].data = self.obj[v].where(self.obj[v] != d['nan_value'])
                    # Then apply a correction if needed for the units.
                    if 'unit_scale' in d:
                        scale = d['unit_scale']
                    else:
                        scale = 1
                    if 'unit_scale_method' in d:
                        if d['unit_scale_method'] == '*':
                            self.obj[v].data *= scale
                        elif d['unit_scale_method'] == '/':
                            self.obj[v].data /= scale
                        elif d['unit_scale_method'] == '+':
                            self.obj[v].data += scale
                        elif d['unit_scale_method'] == '-':
                            self.obj[v].data += -1 * scale

    def obs_to_df(self):
        """Convert and reformat observation object (:attr:`obj`) to dataframe.

        Returns
        -------
        None
        """
        try:
            self.obj = self.obj.to_dataframe().reset_index().drop(['x', 'y'], axis=1)
        except KeyError:
            self.obj = self.obj.to_dataframe().reset_index().drop(['x'], axis=1)

class model:
    """The model class.
    
    A class with information and data from model results.
    """    

    def __init__(self):
        """Initialize a :class:`model` object."""
        self.model = None
        self.apply_ak = False
        self.radius_of_influence = None
        self.mod_kwargs = {}
        self.file_str = None
        self.files = None
        self.file_vert_str = None
        self.files_vert = None
        self.file_surf_str = None
        self.files_surf = None
        self.file_pm25_str = None
        self.files_pm25 = None
        self.label = None
        self.obj = None
        self.mapping = None
        self.variable_dict = None
        self.plot_kwargs = None
        self.proj = None

    def __repr__(self):
        return (
            f"{type(self).__name__}(\n"
            f"    model={self.model!r},\n"
            f"    radius_of_influence={self.radius_of_influence!r},\n"
            f"    mod_kwargs={self.mod_kwargs!r},\n"
            f"    file_str={self.file_str!r},\n"
            f"    label={self.label!r},\n"
            f"    obj={repr(self.obj) if self.obj is None else '...'},\n"
            f"    mapping={self.mapping!r},\n"
            f"    label={self.label!r},\n"
            "    ...\n"
            ")"
        )

    def glob_files(self):
        """Convert the model file location string read in by the yaml file
        into a list of files containing all model data.

        Returns
        -------
        None
        """
        from numpy import sort  # TODO: maybe use `sorted` for this
        from glob import glob
        from . import tutorial

        print(self.file_str)
        if self.file_str.startswith("example:"):
            example_id = ":".join(s.strip() for s in self.file_str.split(":")[1:])
            self.files = [tutorial.fetch_example(example_id)]
        else:
            self.files = sort(glob(self.file_str))
 
        # add option to read list of files from text file
        _, extension = os.path.splitext(self.file_str)
        if extension.lower() == '.txt':
            with open(self.file_str,'r') as f:
                self.files = f.read().split()

        if self.file_vert_str is not None:
            self.files_vert = sort(glob(self.file_vert_str))
        if self.file_surf_str is not None:
            self.files_surf = sort(glob(self.file_surf_str))
        if self.file_pm25_str is not None:
            self.files_pm25 = sort(glob(self.file_pm25_str))

    def open_model_files(self, time_interval=None):
        """Open the model files, store data in :class:`model` instance attributes,
        and apply mask and scaling.
        
        Models supported are cmaq, wrfchem, rrfs, and gsdchem.
        If a model is not supported, MELODIES-MONET will try to open 
        the model data using a generic reader. If you wish to include new 
        models, add the new model option to this module.

        Parameters
        __________
        time_interval (optional, default None) : [pandas.Timestamp, pandas.Timestamp]
            If not None, restrict models to datetime range spanned by time interval [start, end].

        Returns
        -------
        None
        """
        from .util import time_interval_subset as tsub
        print(self.model.lower())

        self.glob_files()
        # Calculate species to input into MONET, so works for all mechanisms in wrfchem
        # I want to expand this for the other models too when add aircraft data.
        list_input_var = []
        for obs_map in self.mapping:
            list_input_var = list_input_var + list(set(self.mapping[obs_map].keys()) - set(list_input_var))
        #Only certain models need this option for speeding up i/o.
        if 'cmaq' in self.model.lower():
            print('**** Reading CMAQ model output...')
            self.mod_kwargs.update({'var_list' : list_input_var})
            if self.files_vert is not None:
                self.mod_kwargs.update({'fname_vert' : self.files_vert})
            if self.files_surf is not None:
                self.mod_kwargs.update({'fname_surf' : self.files_surf})
            if len(self.files) > 1:
                self.mod_kwargs.update({'concatenate_forecasts' : True})
            self.obj = mio.models._cmaq_mm.open_mfdataset(self.files,**self.mod_kwargs)
        elif 'wrfchem' in self.model.lower():
            print('**** Reading WRF-Chem model output...')
            self.mod_kwargs.update({'var_list' : list_input_var})
            self.obj = mio.models._wrfchem_mm.open_mfdataset(self.files,**self.mod_kwargs)
        elif 'rrfs' in self.model.lower():
            print('**** Reading RRFS-CMAQ model output...')
            if self.files_pm25 is not None:
                self.mod_kwargs.update({'fname_pm25' : self.files_pm25})
            self.mod_kwargs.update({'var_list' : list_input_var})
            self.obj = mio.models._rrfs_cmaq_mm.open_mfdataset(self.files,**self.mod_kwargs)
        elif 'gsdchem' in self.model.lower():
            print('**** Reading GSD-Chem model output...')
            if len(self.files) > 1:
                self.obj = mio.fv3chem.open_mfdataset(self.files,**self.mod_kwargs)
            else:
                self.obj = mio.fv3chem.open_dataset(self.files,**self.mod_kwargs)
        elif 'cesm_fv' in self.model.lower():
            print('**** Reading CESM FV model output...')
            self.mod_kwargs.update({'var_list' : list_input_var})
            self.obj = mio.models._cesm_fv_mm.open_mfdataset(self.files,**self.mod_kwargs)
        # CAM-chem-SE grid or MUSICAv0
        elif 'cesm_se' in self.model.lower(): 
            print('**** Reading CESM SE model output...')
            self.mod_kwargs.update({'var_list' : list_input_var})
            if self.scrip_file.startswith("example:"):
                from . import tutorial
                example_id = ":".join(s.strip() for s in self.scrip_file.split(":")[1:])
                self.scrip_file = tutorial.fetch_example(example_id)
            self.mod_kwargs.update({'scrip_file' : self.scrip_file})            
            self.obj = mio.models._cesm_se_mm.open_mfdataset(self.files,**self.mod_kwargs)
            #self.obj, self.obj_scrip = read_cesm_se.open_mfdataset(self.files,**self.mod_kwargs)
            #self.obj.monet.scrip = self.obj_scrip
        elif 'raqms' in self.model.lower():
            if time_interval is not None:
                # fill filelist with subset
                file_sublist = tsub.subset_model_filelist(self.files,'%m_%d_%Y_%H','6H',time_interval)
            else:
                # fill filelist with all files
                file_sublist = self.files
            if len(self.files) > 1:
                self.obj = mio.raqms.open_mfdataset(file_sublist,**self.mod_kwargs)
            else:
                self.obj = mio.raqms.open_dataset(file_sublist,**self.mod_kwargs)
        else:
            print('**** Reading Unspecified model output. Take Caution...')
            if len(self.files) > 1:
                self.obj = xr.open_mfdataset(self.files,**self.mod_kwargs)
            else:
                self.obj = xr.open_dataset(self.files[0],**self.mod_kwargs)
        self.mask_and_scale()

    def mask_and_scale(self):
        """Mask and scale model data including unit conversions.

        Returns
        -------
        None
        """
        vars = self.obj.data_vars
        if self.variable_dict is not None:
            for v in vars:
                if v in self.variable_dict:
                    d = self.variable_dict[v]
                    if 'unit_scale' in d:
                        scale = d['unit_scale']
                    else:
                        scale = 1
                    if 'unit_scale_method' in d:
                        if d['unit_scale_method'] == '*':
                            self.obj[v].data *= scale
                        elif d['unit_scale_method'] == '/':
                            self.obj[v].data /= scale
                        elif d['unit_scale_method'] == '+':
                            self.obj[v].data += scale
                        elif d['unit_scale_method'] == '-':
                            self.obj[v].data += -1 * scale
                    if self.obj[v].units == 'ppv':
                        print('changing units for {}'.format(v))
                        self.obj[v].values *= 1e9
                        self.obj[v].attrs['units'] = 'ppbv'        

class analysis:
    """The analysis class.
    
    The analysis class is the highest
    level class and stores all information about the analysis. It reads 
    and stores information from the input yaml file and defines 
    overarching analysis information like the start and end time, which 
    models and observations to pair, etc.
    """

    def __init__(self):
        """Initialize an :class:`analysis` object."""
        self.control = 'control.yaml'
        self.control_dict = None
        self.models = {}
        """dict : Models, set by :meth:`open_models`."""
        self.obs = {}
        """dict : Observations, set by :meth:`open_obs`."""
        self.paired = {}
        """dict : Paired data, set by :meth:`pair_data`."""
        self.start_time = None
        self.end_time = None
        self.time_intervals = None
        self.download_maps = True  # Default to True
        self.output_dir = None
        self.output_dir_save = None
        self.output_dir_read = None
        self.debug = False
        self.save = None
        self.read = None
        
    def __repr__(self):
        return (
            f"{type(self).__name__}(\n"
            f"    control={self.control!r},\n"
            f"    control_dict={repr(self.control_dict) if self.control_dict is None else '...'},\n"
            f"    models={self.models!r},\n"
            f"    obs={self.obs!r},\n"
            f"    paired={self.paired!r},\n"
            f"    start_time={self.start_time!r},\n"
            f"    end_time={self.end_time!r},\n"
            f"    time_intervals={self.time_intervals!r},\n"
            f"    download_maps={self.download_maps!r},\n"
            f"    output_dir={self.output_dir!r},\n"
            f"    output_dir_save={self.output_dir_save!r},\n"
            f"    output_dir_read={self.output_dir_read!r},\n"
            f"    debug={self.debug!r},\n"
            f"    save={self.save!r},\n"
            f"    read={self.read!r},\n"
            ")"
        )
    def read_control(self, control=None):
        """Read the input yaml file,
        updating various :class:`analysis` instance attributes.

        Parameters
        ----------
        control : str
            Input yaml file path.
            If provided, :attr:`control` will be set to this value.

        Returns
        -------
        type
            Reads the contents of the yaml control file into a dictionary associated with the analysis class.
        """
        import yaml

        if control is not None:
            self.control = control

        with open(self.control, 'r') as stream:
            self.control_dict = yaml.safe_load(stream)

        # set analysis time
        self.start_time = pd.Timestamp(self.control_dict['analysis']['start_time'])
        self.end_time = pd.Timestamp(self.control_dict['analysis']['end_time'])
        if 'output_dir' in self.control_dict['analysis'].keys():
            self.output_dir = os.path.expandvars(
                    self.control_dict['analysis']['output_dir'])
        else:
            raise Exception('output_dir was not specified and is required. Please set analysis.output_dir in the control file.')
        if 'output_dir_save' in self.control_dict['analysis'].keys():
            self.output_dir_save = os.path.expandvars(
                self.control_dict['analysis']['output_dir_save'])
        else:
            self.output_dir_save=self.output_dir
        if 'output_dir_read' in self.control_dict['analysis'].keys():
            if self.control_dict['analysis']['output_dir_read'] is not None:
                self.output_dir_read = os.path.expandvars(
                    self.control_dict['analysis']['output_dir_read'])
        else:
            self.output_dir_read=self.output_dir
            
        self.debug = self.control_dict['analysis']['debug']
        if 'save' in self.control_dict['analysis'].keys():
            self.save = self.control_dict['analysis']['save']
        if 'read' in self.control_dict['analysis'].keys():
            self.read = self.control_dict['analysis']['read']

        # generate time intervals for time chunking
        if 'time_interval' in self.control_dict['analysis'].keys():
            time_stamps = pd.date_range(
                start=self.start_time, end=self.end_time,
                freq=self.control_dict['analysis']['time_interval'])
            # if (end_time - start_time) is not an integer multiple
            #   of freq, append end_time to time_stamps
            if time_stamps[-1] < pd.Timestamp(self.end_time):
                time_stamps = time_stamps.append(
                    pd.DatetimeIndex([self.end_time]))
            self.time_intervals \
                = [[time_stamps[n], time_stamps[n+1]]
                    for n in range(len(time_stamps)-1)]
        
        # Enable Dask progress bars? (default: false)
        enable_dask_progress_bars = self.control_dict["analysis"].get(
            "enable_dask_progress_bars", False)
        if enable_dask_progress_bars:
            from dask.diagnostics import ProgressBar

            ProgressBar().register()
        else:
            from dask.callbacks import Callback

            Callback.active = set()
    
    def save_analysis(self):
        """Save all analysis attributes listed in analysis section of input yaml file.

        Returns
        -------
        None
        """
        if self.save is not None:
            # Loop over each possible attr type (models, obs and paired)
            for attr in self.save:
                if self.save[attr]['method']=='pkl':
                    from .util.write_util import write_pkl
                    write_pkl(obj=getattr(self,attr), output_name=os.path.join(self.output_dir_save,self.save[attr]['output_name']))

                elif self.save[attr]['method']=='netcdf':
                    from .util.write_util import write_analysis_ncf
                    # save either all groups or selected groups
                    if self.save[attr]['data']=='all':
                        if 'prefix' in self.save[attr]:
                            write_analysis_ncf(obj=getattr(self,attr), output_dir=self.output_dir_save,
                                               fn_prefix=self.save[attr]['prefix'])
                        else:
                            write_analysis_ncf(obj=getattr(self,attr), output_dir=self.output_dir_save)
                    else:
                        if 'prefix' in self.save[attr]:
                            write_analysis_ncf(obj=getattr(self,attr), output_dir=self.output_dir_save, 
                                               fn_prefix=self.save[attr]['prefix'], keep_groups=self.save[attr]['data'])
                        else:
                            write_analysis_ncf(obj=getattr(self,attr), output_dir=self.output_dir_save, 
                                               keep_groups=self.save[attr]['data'])
        
    def read_analysis(self):
        """Read all previously saved analysis attributes listed in analysis section of input yaml file.

        Returns
        -------
        None
        """
        if self.read is not None:
            # Loop over each possible attr type (models, obs and paired)
            from .util.read_util import read_saved_data
            for attr in self.read:
                if self.read[attr]['method']=='pkl':
                    read_saved_data(analysis=self,filenames=self.read[attr]['filenames'], method='pkl', attr=attr)
                elif self.read[attr]['method']=='netcdf':
                    read_saved_data(analysis=self,filenames=self.read[attr]['filenames'], method='netcdf', attr=attr)
                if attr == 'paired':
                    # initialize model/obs attributes, since needed for plotting and stats
                    if not self.models:
                        self.open_models(load_files=False)
                    if not self.obs:
                        self.open_obs(load_files=False)


    def open_models(self, time_interval=None,load_files=True):
        """Open all models listed in the input yaml file and create a :class:`model` 
        object for each of them, populating the :attr:`models` dict.

        Parameters
        __________
        time_interval (optional, default None) : [pandas.Timestamp, pandas.Timestamp]
            If not None, restrict models to datetime range spanned by time interval [start, end].
        load_files (optional, default True): boolean
            If False, only populate :attr: dict with yaml file parameters and do not open model files. 
        Returns
        -------
        None
        """
        if 'model' in self.control_dict:
            # open each model
            for mod in self.control_dict['model']:
                # create a new model instance
                m = model()
                # this is the model type (ie cmaq, rapchem, gsdchem etc)
                m.model = self.control_dict['model'][mod]['mod_type']
                # set the model label in the dictionary and model class instance
                if "apply_ak" in self.control_dict['model'][mod].keys():
                    m.apply_ak = self.control_dict['model'][mod]['apply_ak']
                if 'radius_of_influence' in self.control_dict['model'][mod].keys():
                    m.radius_of_influence = self.control_dict['model'][mod]['radius_of_influence']
                else:
                    m.radius_of_influence = 1e6
                        
                if 'mod_kwargs' in self.control_dict['model'][mod].keys():
                    m.mod_kwargs = self.control_dict['model'][mod]['mod_kwargs']    
                m.label = mod
                # create file string (note this can include hot strings)
                m.file_str = os.path.expandvars(
                    self.control_dict['model'][mod]['files'])
                if 'files_vert' in self.control_dict['model'][mod].keys():
                    m.file_vert_str = os.path.expandvars(
                        self.control_dict['model'][mod]['files_vert'])
                if 'files_surf' in self.control_dict['model'][mod].keys():
                    m.file_surf_str = os.path.expandvars(
                        self.control_dict['model'][mod]['files_surf'])
                if 'files_pm25' in self.control_dict['model'][mod].keys():
                    m.file_pm25_str = os.path.expandvars(
                        self.control_dict['model'][mod]['files_pm25'])
                # create mapping
                m.mapping = self.control_dict['model'][mod]['mapping']
                # add variable dict

                if 'variables' in self.control_dict['model'][mod].keys():
                    m.variable_dict = self.control_dict['model'][mod]['variables']
                if 'plot_kwargs' in self.control_dict['model'][mod].keys():
                    m.plot_kwargs = self.control_dict['model'][mod]['plot_kwargs']
                    
                # unstructured grid check
                if m.model in ['cesm_se']:
                    if 'scrip_file' in self.control_dict['model'][mod].keys():
                        m.scrip_file = self.control_dict['model'][mod]['scrip_file']
                    else:
                        raise ValueError( '"Scrip_file" must be provided for unstructured grid output!' )

                # maybe set projection
                proj_in = self.control_dict['model'][mod].get("projection")
                if proj_in == "None":
                    print(
                        f"NOTE: model.{mod}.projection is {proj_in!r} (str), "
                        "but we assume you want `None` (Python null sentinel). "
                        "To avoid this warning, "
                        "update your control file to remove the projection setting "
                        "or set to `~` or `null` if you want null value in YAML."
                    )
                    proj_in = None
                if proj_in is not None:
                    if isinstance(proj_in, str) and proj_in.startswith("model:"):
                        m.proj = proj_in
                    elif isinstance(proj_in, str) and proj_in.startswith("ccrs."):
                        import cartopy.crs as ccrs
                        m.proj = eval(proj_in)
                    else:
                        import cartopy.crs as ccrs

                        if isinstance(proj_in, ccrs.Projection):
                            m.proj = proj_in
                        else:
                            m.proj = ccrs.Projection(proj_in)

                # open the model
                if load_files:
                    m.open_model_files(time_interval=time_interval)
                self.models[m.label] = m

    def open_obs(self, time_interval=None, load_files=True):
        """Open all observations listed in the input yaml file and create an 
        :class:`observation` instance for each of them,
        populating the :attr:`obs` dict.

        Parameters
        __________
        time_interval (optional, default None) : [pandas.Timestamp, pandas.Timestamp]
            If not None, restrict obs to datetime range spanned by time interval [start, end].
        load_files (optional, default True): boolean
            If False, only populate :attr: dict with yaml file parameters and do not open obs files. 
            
        Returns
        -------
        None
        """
        if 'obs' in self.control_dict:
            for obs in self.control_dict['obs']:
                o = observation()
                o.obs = obs
                o.label = obs
                o.obs_type = self.control_dict['obs'][obs]['obs_type']
                if 'data_proc' in self.control_dict['obs'][obs].keys():
                    o.data_proc = self.control_dict['obs'][obs]['data_proc']
                o.file = os.path.expandvars(
                    self.control_dict['obs'][obs]['filename'])
                if 'debug' in self.control_dict['obs'][obs].keys():
                    o.debug = self.control_dict['obs'][obs]['debug']
                if 'variables' in self.control_dict['obs'][obs].keys():
                    o.variable_dict = self.control_dict['obs'][obs]['variables']
                if 'sat_type' in self.control_dict['obs'][obs].keys():
                    o.sat_type = self.control_dict['obs'][obs]['sat_type']
                if load_files:
                    if o.obs_type in ['sat_swath_sfc', 'sat_swath_clm', 'sat_grid_sfc',\
                                        'sat_grid_clm', 'sat_swath_prof']:
                        o.open_sat_obs(time_interval=time_interval)
                    else:
                        o.open_obs(time_interval=time_interval)
                self.obs[o.label] = o

    def pair_data(self, time_interval=None):
        """Pair all observations and models in the analysis class
        (i.e., those listed in the input yaml file) together,
        populating the :attr:`paired` dict.

        Parameters
        __________
        time_interval (optional, default None) : [pandas.Timestamp, pandas.Timestamp]
            If not None, restrict pairing to datetime range spanned by time interval [start, end].


        Returns
        -------
        None
        """
        pairs = {}  # TODO: unused
        for model_label in self.models:
            mod = self.models[model_label]
            # Now we have the models we need to loop through the mapping table for each network and pair the data
            # each paired dataset will be output to a netcdf file with 'model_label_network.nc'
            for obs_to_pair in mod.mapping.keys():
                # get the variables to pair from the model data (ie don't pair all data)
                keys = [key for key in mod.mapping[obs_to_pair].keys()]
                obs_vars = [mod.mapping[obs_to_pair][key] for key in keys]
                
                # unstructured grid check - lon/lat variables should be explicitly added 
                # in addition to comparison variables
                if mod.obj.attrs.get("mio_scrip_file", False):
                    lonlat_list = [ 'lon', 'lat', 'longitude', 'latitude', 'Longitude', 'Latitude' ]
                    for ll in lonlat_list:
                        if ll in mod.obj.data_vars:
                            keys += [ll]
                model_obj = mod.obj[keys]
                
                ## TODO:  add in ability for simple addition of variables from

                # simplify the objs object with the correct mapping variables
                obs = self.obs[obs_to_pair]

                # pair the data
                # if pt_sfc (surface point network or monitor)
                if obs.obs_type.lower() == 'pt_sfc':
                    # convert this to pandas dataframe unless already done because second time paired this obs
                    if not isinstance(obs.obj, pd.DataFrame):
                        obs.obs_to_df()
                    #Check if z dim is larger than 1. If so select, the first level as all models read through 
                    #MONETIO will be reordered such that the first level is the level nearest to the surface.
                    try:
                        if model_obj.sizes['z'] > 1:
                            # Select only the surface values to pair with obs.
                            model_obj = model_obj.isel(z=0).expand_dims('z',axis=1)
                    except KeyError as e:
                        raise Exception("MONET requires an altitude dimension named 'z'") from e
                    # now combine obs with
                    paired_data = model_obj.monet.combine_point(obs.obj, radius_of_influence=mod.radius_of_influence, suffix=mod.label)
                    if self.debug:
                        print('After pairing: ', paired_data)
                    # this outputs as a pandas dataframe.  Convert this to xarray obj
                    p = pair()
                    p.obs = obs.label
                    p.model = mod.label
                    p.model_vars = keys
                    p.obs_vars = obs_vars
                    p.filename = '{}_{}.nc'.format(p.obs, p.model)
                    p.obj = paired_data.monet._df_to_da()
                    label = "{}_{}".format(p.obs, p.model)
                    self.paired[label] = p
                    p.obj = p.fix_paired_xarray(dset=p.obj)
                    # write_util.write_ncf(p.obj,p.filename) # write out to file
                # TODO: add other network types / data types where (ie flight, satellite etc)
                # if sat_swath_clm (satellite l2 column products)
                elif obs.obs_type.lower() == 'sat_swath_clm':                
                    if obs.label == 'omps_nm':
                        
                        from .util import satellite_utilities as sutil
                        
                        #necessary observation index things 
                        #the along track coordinate dim sometimes needs to be time and other times an unassigned 'x'
                        obs.obj = obs.obj.swap_dims({'time':'x'})
                        if mod.apply_ak == True:
                            model_obj = mod.obj[keys+['pres_pa_mid','surfpres_pa']]
                            
                            paired_data = sutil.omps_nm_pairing_apriori(model_obj,obs.obj,keys)
                        else:
                            model_obj = mod.obj[keys+['dp_pa']]
                            paired_data = sutil.omps_nm_pairing(model_obj,obs.obj,keys)

                        paired_data = paired_data.where((paired_data.o3vmr > 0))
                        p = pair()
                        p.type = obs.obs_type
                        p.obs = obs.label
                        p.model = mod.label
                        p.model_vars = keys
                        p.obs_vars = obs_vars
                        p.obj = paired_data 
                        label = '{}_{}'.format(p.obs,p.model)
                        self.paired[label] = p

                    if obs.label == 'tropomi_l2_no2':
                        from .util import sat_l2_swath_utility as sutil

                        if mod.apply_ak == True:
                            paired_data = sutil.trp_interp_swatogrd_ak(obs.obj, model_obj)
                        else:
                            paired_data = sutil.trp_interp_swatogrd(obs.obj, model_obj)

                        p = pair()
                        p.type = obs.obs_type
                        p.obs = obs.label
                        p.model = mod.label
                        p.model_vars = keys
                        p.obs_vars = obs_vars
                        p.obj = paired_data 
                        label = '{}_{}'.format(p.obs,p.model)
                        self.paired[label] = p

                # if sat_grid_clm (satellite l3 column products)
                elif obs.obs_type.lower() == 'sat_grid_clm':
                    if obs.label == 'omps_l3':
                        from .util import satellite_utilities as sutil
                        # trim obs array to only data within analysis window
                        obs_dat = obs.obj.sel(time=slice(self.start_time.date(),self.end_time.date())).copy()
                        model_obsgrid = sutil.omps_l3_daily_o3_pairing(mod.obj,obs_dat,'o3vmr')
                        # combine model and observations into paired dataset
                        obs_dat['o3vmr'] = (['time','x','y'],model_obsgrid.sel(time=slice(self.start_time.date(),self.end_time.date())).data)
                        p = pair()
                        p.type = obs.obs_type
                        p.obs = obs.label
                        p.model = mod.label
                        p.model_vars = keys
                        p.obs_vars = obs_vars
                        p.obj = obs_dat
                        label = '{}_{}'.format(p.obs,p.model)
                        self.paired[label] = p

    def concat_pairs(self):
        """Read and concatenate all observation and model time interval pair data,
        populating the :attr:`paired` dict.

        Returns
        -------
        None
        """
        pass
    
    ### TODO: Create the plotting driver (most complicated one)
    # def plotting(self):
    def plotting(self):
        """Cycle through all the plotting groups (e.g., plot_grp1) listed in 
        the input yaml file and create the plots.
        
        This routine loops over all the domains and
        model/obs pairs specified in the plotting group (``.control_dict['plots']``)
        for all the variables specified in the mapping dictionary listed in 
        :attr:`paired`.

        Creates plots stored in the file location specified by output_dir
        in the analysis section of the yaml file.

        Returns
        -------
        None
        """
        import matplotlib.pyplot as plt
        pair_keys = list(self.paired.keys())
        if self.paired[pair_keys[0]].type.lower() == 'pt_sfc':
            from .plots import surfplots as splots,savefig
        else:
            from .plots import satplots as splots,savefig

        # Disable figure count warning
        initial_max_fig = plt.rcParams["figure.max_open_warning"]
        plt.rcParams["figure.max_open_warning"] = 0

        # first get the plotting dictionary from the yaml file
        plot_dict = self.control_dict['plots']
        # Calculate any items that do not need to recalculate each loop.
        startdatename = str(datetime.datetime.strftime(self.start_time, '%Y-%m-%d_%H'))
        enddatename = str(datetime.datetime.strftime(self.end_time, '%Y-%m-%d_%H'))
        # now we are going to loop through each plot_group (note we can have multiple plot groups)
        # a plot group can have
        #     1) a singular plot type
        #     2) multiple paired datasets or model datasets depending on the plot type
        #     3) kwargs for creating the figure ie size and marker (note the default for obs is 'x')
        for grp, grp_dict in plot_dict.items():
            pair_labels = grp_dict['data']
            # get the plot type
            plot_type = grp_dict['type']

            # first get the observational obs labels
            pair1 = self.paired[list(self.paired.keys())[0]]
            obs_vars = pair1.obs_vars
            obs_type = pair1.type
            # loop through obs variables
            for obsvar in obs_vars:
                # Loop also over the domain types. So can easily create several overview and zoomed in plots.
                domain_types = grp_dict['domain_type']
                domain_names = grp_dict['domain_name']
                for domain in range(len(domain_types)):
                    domain_type = domain_types[domain]
                    domain_name = domain_names[domain]

                    # Then loop through each of the pairs to add to the plot.
                    for p_index, p_label in enumerate(pair_labels):
                        p = self.paired[p_label]
                        # find the pair model label that matches the obs var
                        index = p.obs_vars.index(obsvar)
                        modvar = p.model_vars[index]

                        # Adjust the modvar as done in pairing script, if the species name in obs and model are the same.
                        if obsvar == modvar:
                            modvar = modvar + '_new'
                            
                        # for pt_sfc data, convert to pandas dataframe, format, and trim
                        if obs_type == 'pt_sfc':
                            # convert to dataframe
                            pairdf_all = p.obj.to_dataframe(dim_order=["time", "x"])
                            # Select only the analysis time window.
                            pairdf_all = pairdf_all.loc[self.start_time : self.end_time]
                        
                        # keep data in xarray, fix formatting, and trim
                        elif obs_type in ["sat_swath_sfc", "sat_swath_clm", 
                                                                        "sat_grid_sfc", "sat_grid_clm", 
                                                                        "sat_swath_prof"]:
                             # convert index to time; setup for sat_swath_clm
                            
                            if 'time' not in p.obj.dims and obs_type == 'sat_swath_clm':
                                
                                pairdf_all = p.obj.swap_dims({'x':'time'})
                            # squash lat/lon dimensions into single dimension
                            elif obs_type == 'sat_grid_clm':
                                pairdf_all = p.obj.stack(ll=['x','y'])
                                pairdf_all = pairdf_all.rename_dims({'ll':'y'})
                            else:
                                pairdf_all = p.obj
                            # Select only the analysis time window.
                            pairdf_all = pairdf_all.sel(time=slice(self.start_time,self.end_time))
                            
                        # Determine the default plotting colors.
                        if 'default_plot_kwargs' in grp_dict.keys():
                            if self.models[p.model].plot_kwargs is not None:
                                plot_dict = {**grp_dict['default_plot_kwargs'], **self.models[p.model].plot_kwargs}
                            else:
                                plot_dict = {**grp_dict['default_plot_kwargs'], **splots.calc_default_colors(p_index)}
                            obs_dict = grp_dict['default_plot_kwargs']
                        else:
                            if self.models[p.model].plot_kwargs is not None:
                                plot_dict = self.models[p.model].plot_kwargs.copy()
                            else:
                                plot_dict = splots.calc_default_colors(p_index).copy()
                            obs_dict = None

                        # Determine figure_kwargs and text_kwargs
                        if 'fig_kwargs' in grp_dict.keys():
                            fig_dict = grp_dict['fig_kwargs']
                        else:
                            fig_dict = None
                        if 'text_kwargs' in grp_dict.keys():
                            text_dict = grp_dict['text_kwargs']
                        else:
                            text_dict = None

                        # Read in some plotting specifications stored with observations.
                        if self.obs[p.obs].variable_dict is not None:
                            if obsvar in self.obs[p.obs].variable_dict.keys():
                                obs_plot_dict = self.obs[p.obs].variable_dict[obsvar].copy()
                            else:
                                obs_plot_dict = {}
                        else:
                            obs_plot_dict = {}

                        # Specify ylabel if noted in yaml file.
                        if 'ylabel_plot' in obs_plot_dict.keys():
                            use_ylabel = obs_plot_dict['ylabel_plot']
                        else:
                            use_ylabel = None

                        # Determine if set axis values or use defaults
                        if grp_dict['data_proc']['set_axis'] == True:
                            if obs_plot_dict:  # Is not null
                                set_yaxis = True
                            else:
                                print('Warning: variables dict for ' + obsvar + ' not provided, so defaults used')
                                set_yaxis = False
                        else:
                            set_yaxis = False

                        # Determine to calculate mean values or percentile
                        if 'percentile_opt' in obs_plot_dict.keys():
                            use_percentile = obs_plot_dict['percentile_opt']
                        else:
                            use_percentile = None

                        # Determine outname
                        outname = "{}.{}.{}.{}.{}.{}.{}".format(grp, plot_type, obsvar, startdatename, enddatename, domain_type, domain_name)

                        # Query selected points if applicable
                        if domain_type != 'all':
                            pairdf_all.query(domain_type + ' == ' + '"' + domain_name + '"', inplace=True)
                        
                        # Query with filter options
                        if 'filter_dict' in grp_dict['data_proc'] and 'filter_string' in grp_dict['data_proc']:
                            raise Exception("""For plot group: {}, only one of filter_dict and filter_string can be specified.""".format(grp))
                        elif 'filter_dict' in grp_dict['data_proc']:
                            filter_dict = grp_dict['data_proc']['filter_dict']
                            for column in filter_dict.keys():
                                filter_vals = filter_dict[column]['value']
                                filter_op = filter_dict[column]['oper']
                                if filter_op == 'isin':
                                    pairdf_all.query(f'{column} == {filter_vals}', inplace=True)
                                elif filter_op == 'isnotin':
                                    pairdf_all.query(f'{column} != {filter_vals}', inplace=True)
                                else:
                                    pairdf_all.query(f'{column} {filter_op} {filter_vals}', inplace=True)
                        elif 'filter_string' in grp_dict['data_proc']:
                            pairdf_all.query(grp_dict['data_proc']['filter_string'], inplace=True)

                        # Drop sites with greater than X percent NAN values
                        if 'rem_obs_by_nan_pct' in grp_dict['data_proc']:
                            grp_var = grp_dict['data_proc']['rem_obs_by_nan_pct']['group_var']
                            pct_cutoff = grp_dict['data_proc']['rem_obs_by_nan_pct']['pct_cutoff']
                            
                            if grp_dict['data_proc']['rem_obs_by_nan_pct']['times'] == 'hourly':
                                # Select only hours at the hour
                                hourly_pairdf_all = pairdf_all.reset_index().loc[pairdf_all.reset_index()['time'].dt.minute==0,:]
                                
                                # calculate total obs count, obs count with nan removed, and nan percent for each group
                                grp_fullcount = hourly_pairdf_all[[grp_var,obsvar]].groupby(grp_var).size().rename({0:obsvar})
                                grp_nonan_count = hourly_pairdf_all[[grp_var,obsvar]].groupby(grp_var).count() # counts only non NA values    
                            else: 
                                # calculate total obs count, obs count with nan removed, and nan percent for each group
                                grp_fullcount = pairdf_all[[grp_var,obsvar]].groupby(grp_var).size().rename({0:obsvar})
                                grp_nonan_count = pairdf_all[[grp_var,obsvar]].groupby(grp_var).count() # counts only non NA values  
                                
                            grp_pct_nan = 100 - grp_nonan_count.div(grp_fullcount,axis=0)*100

                            # make list of sites meeting condition and select paired data by this by this
                            grp_select = grp_pct_nan.query(obsvar + ' < ' + str(pct_cutoff)).reset_index()
                            pairdf_all = pairdf_all.loc[pairdf_all[grp_var].isin(grp_select[grp_var].values)]

                        # Drop NaNs if using pandas 
                        if obs_type == 'pt_sfc':
                            if grp_dict['data_proc']['rem_obs_nan'] == True:
                                # I removed drop=True in reset_index in order to keep 'time' as a column.
                                pairdf = pairdf_all.reset_index().dropna(subset=[modvar, obsvar])
                            else:
                                pairdf = pairdf_all.reset_index().dropna(subset=[modvar])
                        elif obs_type in  ["sat_swath_sfc", "sat_swath_clm", 
                                                                        "sat_grid_sfc", "sat_grid_clm", 
                                                                        "sat_swath_prof"]: 
                            # xarray doesn't need nan drop because its math operations seem to ignore nans
                            pairdf = pairdf_all
                        else:
                            print('Warning: set rem_obs_nan = True for regulatory metrics') 
                            pairdf = pairdf_all.reset_index().dropna(subset=[modvar])

                        # JianHe: do we need provide a warning if pairdf is empty (no valid obsdata) for specific subdomain?
                        # MEB: pairdf.empty fails for data left in xarray format. isnull format works.
                        if pairdf[obsvar].isnull().all():
                            print('Warning: no valid obs found for '+domain_name)
                            continue

                        # JianHe: Determine if calculate regulatory values
                        cal_reg = obs_plot_dict.get('regulatory', False)

                        if cal_reg:
                            # Reset use_ylabel for regulatory calculations
                            if 'ylabel_reg_plot' in obs_plot_dict.keys():
                                use_ylabel = obs_plot_dict['ylabel_reg_plot']
                            else:
                                use_ylabel = None

                            df2 = (
                                pairdf.copy()
                                .groupby("siteid")
                                .resample('H', on='time_local')
                                .mean()
                                .reset_index()
                            )

                            if obsvar == 'PM2.5':  
                                pairdf_reg = splots.make_24hr_regulatory(df2,[obsvar,modvar]).rename(index=str,columns={obsvar+'_y':obsvar+'_reg',modvar+'_y':modvar+'_reg'})
                            elif obsvar == 'OZONE':
                                pairdf_reg = splots.make_8hr_regulatory(df2,[obsvar,modvar]).rename(index=str,columns={obsvar+'_y':obsvar+'_reg',modvar+'_y':modvar+'_reg'})
                            else:
                                print('Warning: no regulatory calculations found for ' + obsvar + '. Skipping plot.')
                                del df2
                                continue
                            del df2
                            if len(pairdf_reg[obsvar+'_reg']) == 0:
                                print('No valid data for '+obsvar+'_reg. Skipping plot.')
                                continue
                            else:
                                # Reset outname for regulatory options
                                outname = "{}.{}.{}.{}.{}.{}.{}".format(grp, plot_type, obsvar+'_reg', startdatename, enddatename, domain_type, domain_name)
                        else:
                            pairdf_reg = None

                        if plot_type.lower() == 'spatial_bias': 
                            if use_percentile is None:
                                outname = outname+'.mean'
                            else:
                                outname = outname+'.p'+'{:02d}'.format(use_percentile) 

                        if self.output_dir is not None:
                            outname = self.output_dir + '/' + outname  # Extra / just in case.

                        # Types of plots
                        if plot_type.lower() == 'timeseries':
                            if set_yaxis == True:
                                if all(k in obs_plot_dict for k in ('vmin_plot', 'vmax_plot')):
                                    vmin = obs_plot_dict['vmin_plot']
                                    vmax = obs_plot_dict['vmax_plot']
                                else:
                                    print('Warning: vmin_plot and vmax_plot not specified for ' + obsvar + ', so default used.')
                                    vmin = None
                                    vmax = None
                            else:
                                vmin = None
                                vmax = None
                            # Select time to use as index.
                            pairdf = pairdf.set_index(grp_dict['data_proc']['ts_select_time'])
                            # Specify ts_avg_window if noted in yaml file. 
                            if 'ts_avg_window' in grp_dict['data_proc'].keys():
                                a_w = grp_dict['data_proc']['ts_avg_window']
                            else:
                                a_w = None  
                            if p_index == 0:
                                # First plot the observations.
                                ax = splots.make_timeseries(
                                    pairdf,
                                    pairdf_reg,
                                    column=obsvar,
                                    label=p.obs,
                                    avg_window=a_w,
                                    ylabel=use_ylabel,
                                    vmin=vmin,
                                    vmax=vmax,
                                    domain_type=domain_type,
                                    domain_name=domain_name,
                                    plot_dict=obs_dict,
                                    fig_dict=fig_dict,
                                    text_dict=text_dict,
                                    debug=self.debug
                                )
                            # For all p_index plot the model.
                            ax = splots.make_timeseries(
                                pairdf,
                                pairdf_reg,
                                column=modvar,
                                label=p.model,
                                ax=ax,
                                avg_window=a_w,
                                ylabel=use_ylabel,
                                vmin=vmin,
                                vmax=vmax,
                                domain_type=domain_type,
                                domain_name=domain_name,
                                plot_dict=plot_dict,
                                text_dict=text_dict,
                                debug=self.debug
                            )
                            # At the end save the plot.
                            if p_index == len(pair_labels) - 1:
                                savefig(outname + '.png', logo_height=150)
                                del (ax, fig_dict, plot_dict, text_dict, obs_dict, obs_plot_dict) #Clear axis for next plot.
                        if plot_type.lower() == 'boxplot':
                            if set_yaxis == True:
                                if all(k in obs_plot_dict for k in ('vmin_plot', 'vmax_plot')):
                                    vmin = obs_plot_dict['vmin_plot']
                                    vmax = obs_plot_dict['vmax_plot']
                                else:
                                    print('Warning: vmin_plot and vmax_plot not specified for ' + obsvar + ', so default used.')
                                    vmin = None
                                    vmax = None
                            else:
                                vmin = None
                                vmax = None
                            # First for p_index = 0 create the obs box plot data array.
                            if p_index == 0:
                                comb_bx, label_bx = splots.calculate_boxplot(pairdf, pairdf_reg, column=obsvar, 
                                                                             label=p.obs, plot_dict=obs_dict)
                            # Then add the models to this dataarray.
                            comb_bx, label_bx = splots.calculate_boxplot(pairdf, pairdf_reg, column=modvar, label=p.model,
                                                                         plot_dict=plot_dict, comb_bx=comb_bx,
                                                                         label_bx=label_bx)
                            # For the last p_index make the plot.
                            if p_index == len(pair_labels) - 1:
                                splots.make_boxplot(
                                    comb_bx,
                                    label_bx,
                                    ylabel=use_ylabel,
                                    vmin=vmin,
                                    vmax=vmax,
                                    outname=outname,
                                    domain_type=domain_type,
                                    domain_name=domain_name,
                                    plot_dict=obs_dict,
                                    fig_dict=fig_dict,
                                    text_dict=text_dict,
                                    debug=self.debug
                                )
                                #Clear info for next plot.
                                del (comb_bx, label_bx, fig_dict, plot_dict, text_dict, obs_dict, obs_plot_dict) 
                        elif plot_type.lower() == 'taylor':
                            if set_yaxis == True:
                                if 'ty_scale' in obs_plot_dict.keys():
                                    ty_scale = obs_plot_dict['ty_scale']
                                else:
                                    print('Warning: ty_scale not specified for ' + obsvar + ', so default used.')
                                    ty_scale = 1.5  # Use default
                            else:
                                ty_scale = 1.5  # Use default
                            if p_index == 0:
                                # Plot initial obs/model
                                dia = splots.make_taylor(
                                    pairdf,
                                    pairdf_reg,
                                    column_o=obsvar,
                                    label_o=p.obs,
                                    column_m=modvar,
                                    label_m=p.model,
                                    ylabel=use_ylabel,
                                    ty_scale=ty_scale,
                                    domain_type=domain_type,
                                    domain_name=domain_name,
                                    plot_dict=plot_dict,
                                    fig_dict=fig_dict,
                                    text_dict=text_dict,
                                    debug=self.debug
                                )
                            else:
                                # For the rest, plot on top of dia
                                dia = splots.make_taylor(
                                    pairdf,
                                    pairdf_reg,
                                    column_o=obsvar,
                                    label_o=p.obs,
                                    column_m=modvar,
                                    label_m=p.model,
                                    dia=dia,
                                    ylabel=use_ylabel,
                                    ty_scale=ty_scale,
                                    domain_type=domain_type,
                                    domain_name=domain_name,
                                    plot_dict=plot_dict,
                                    text_dict=text_dict,
                                    debug=self.debug
                                )
                            # At the end save the plot.
                            if p_index == len(pair_labels) - 1:
                                savefig(outname + '.png', logo_height=70)
                                del (dia, fig_dict, plot_dict, text_dict, obs_dict, obs_plot_dict) #Clear info for next plot.
                        elif plot_type.lower() == 'spatial_bias':
                            if set_yaxis == True:
                                if 'vdiff_plot' in obs_plot_dict.keys():
                                    vdiff = obs_plot_dict['vdiff_plot']
                                else:
                                    print('Warning: vdiff_plot not specified for ' + obsvar + ', so default used.')
                                    vdiff = None
                            else:
                                vdiff = None
                            # p_label needs to be added to the outname for this plot
                            outname = "{}.{}".format(outname, p_label)
                            splots.make_spatial_bias(
                                pairdf,
                                pairdf_reg,
                                column_o=obsvar,
                                label_o=p.obs,
                                column_m=modvar,
                                label_m=p.model,
                                ylabel=use_ylabel,
                                ptile=use_percentile,
                                vdiff=vdiff,
                                outname=outname,
                                domain_type=domain_type,
                                domain_name=domain_name,
                                fig_dict=fig_dict,
                                text_dict=text_dict,
                                debug=self.debug
                            )
                        elif plot_type.lower() == 'gridded_spatial_bias':
                            splots.make_spatial_bias_gridded(
                                p.obj,
                                column_o=obsvar,
                                label_o=p.obs,
                                column_m=modvar,
                                label_m=p.model,
                                ylabel=use_ylabel,
                                #vdiff=vdiff,
                                outname=outname,
                                domain_type=domain_type,
                                domain_name=domain_name,
                                fig_dict=fig_dict,
                                text_dict=text_dict,
                                debug=self.debug
                                )    
                            del (fig_dict, plot_dict, text_dict, obs_dict, obs_plot_dict) #Clear info for next plot.
                        elif plot_type.lower() == 'spatial_bias_exceedance':
                            if cal_reg:
                                if set_yaxis == True:
                                    if 'vdiff_reg_plot' in obs_plot_dict.keys():
                                        vdiff = obs_plot_dict['vdiff_reg_plot']
                                    else:
                                        print('Warning: vdiff_reg_plot not specified for ' + obsvar + ', so default used.')
                                        vdiff = None
                                else:
                                    vdiff = None

                                # p_label needs to be added to the outname for this plot
                                outname = "{}.{}".format(outname, p_label)
                                splots.make_spatial_bias_exceedance(
                                    pairdf_reg,
                                    column_o=obsvar+'_reg',
                                    label_o=p.obs,
                                    column_m=modvar+'_reg',
                                    label_m=p.model,
                                    ylabel=use_ylabel,
                                    vdiff=vdiff,
                                    outname=outname,
                                    domain_type=domain_type,
                                    domain_name=domain_name,
                                    fig_dict=fig_dict,
                                    text_dict=text_dict,
                                    debug=self.debug
                                )
                                del (fig_dict, plot_dict, text_dict, obs_dict, obs_plot_dict) #Clear info for next plot.
                            else:
                                print('Warning: spatial_bias_exceedance plot only works when regulatory=True.')
                        # JianHe: need updates to include regulatory option for overlay plots
                        elif plot_type.lower() == 'spatial_overlay':
                            if set_yaxis == True:
                                if all(k in obs_plot_dict for k in ('vmin_plot', 'vmax_plot', 'nlevels_plot')):
                                    vmin = obs_plot_dict['vmin_plot']
                                    vmax = obs_plot_dict['vmax_plot']
                                    nlevels = obs_plot_dict['nlevels_plot']
                                elif all(k in obs_plot_dict for k in ('vmin_plot', 'vmax_plot')):
                                    vmin = obs_plot_dict['vmin_plot']
                                    vmax = obs_plot_dict['vmax_plot']
                                    nlevels = None
                                else:
                                    print('Warning: vmin_plot and vmax_plot not specified for ' + obsvar + ', so default used.')
                                    vmin = None
                                    vmax = None
                                    nlevels = None
                            else:
                                vmin = None
                                vmax = None
                                nlevels = None
                            #Check if z dim is larger than 1. If so select, the first level as all models read through 
                            #MONETIO will be reordered such that the first level is the level nearest to the surface.
                            # Create model slice and select time window for spatial plots
                            try:
                                self.models[p.model].obj.sizes['z']
                                if self.models[p.model].obj.sizes['z'] > 1: #Select only surface values.
                                    vmodel = self.models[p.model].obj.isel(z=0).expand_dims('z',axis=1).loc[
                                        dict(time=slice(self.start_time, self.end_time))] 
                                else:
                                    vmodel = self.models[p.model].obj.loc[dict(time=slice(self.start_time, self.end_time))]
                            except KeyError as e:
                                raise Exception("MONET requires an altitude dimension named 'z'") from e

                            # Determine proj to use for spatial plots
                            proj = splots.map_projection(self.models[p.model])
                            # p_label needs to be added to the outname for this plot
                            outname = "{}.{}".format(outname, p_label)
                            # For just the spatial overlay plot, you do not use the model data from the pair file
                            # So get the variable name again since pairing one could be _new.
                            # JianHe: only make overplay plots for non-regulatory variables for now
                            if not cal_reg:
                                splots.make_spatial_overlay(
                                    pairdf,
                                    vmodel,
                                    column_o=obsvar,
                                    label_o=p.obs,
                                    column_m=p.model_vars[index],
                                    label_m=p.model,
                                    ylabel=use_ylabel,
                                    vmin=vmin,
                                    vmax=vmax,
                                    nlevels=nlevels,
                                    proj=proj,
                                    outname=outname,
                                    domain_type=domain_type,
                                    domain_name=domain_name,
                                    fig_dict=fig_dict,
                                    text_dict=text_dict,
                                    debug=self.debug
                                )
                            else:
                                print('Warning: Spatial overlay plots are not available yet for regulatory metrics.')

                            del (fig_dict, plot_dict, text_dict, obs_dict, obs_plot_dict) #Clear info for next plot.

        # Restore figure count warning
        plt.rcParams["figure.max_open_warning"] = initial_max_fig

    def stats(self):
        """Calculate statistics specified in the input yaml file.
        
        This routine  loops over all the domains and model/obs pairs for all the variables 
        specified in the mapping dictionary listed in :attr:`paired`.
        
        Creates a csv file storing the statistics and optionally a figure 
        visualizing the table.

        Returns
        -------
        None
        """
        from .stats import proc_stats as proc_stats
        from .plots import surfplots as splots

        # first get the stats dictionary from the yaml file
        stat_dict = self.control_dict['stats']
        # Calculate general items
        startdatename = str(datetime.datetime.strftime(self.start_time, '%Y-%m-%d_%H'))
        enddatename = str(datetime.datetime.strftime(self.end_time, '%Y-%m-%d_%H'))
        stat_list = stat_dict['stat_list']
        # Determine stat_grp full name
        stat_fullname_ns = proc_stats.produce_stat_dict(stat_list=stat_list, spaces=False)
        stat_fullname_s = proc_stats.produce_stat_dict(stat_list=stat_list, spaces=True)
        pair_labels = stat_dict['data']

        # Determine rounding
        if 'round_output' in stat_dict.keys():
            round_output = stat_dict['round_output']
        else:
            round_output = 3

        # Then loop over all the observations
        # first get the observational obs labels
        pair1 = self.paired[list(self.paired.keys())[0]]
        obs_vars = pair1.obs_vars
        for obsvar in obs_vars:
            # Read in some plotting specifications stored with observations.
            if self.obs[pair1.obs].variable_dict is not None:
                if obsvar in self.obs[pair1.obs].variable_dict.keys():
                    obs_plot_dict = self.obs[pair1.obs].variable_dict[obsvar]
                else:
                    obs_plot_dict = {}
            else:
                obs_plot_dict = {}

            # JianHe: Determine if calculate regulatory values
            cal_reg = obs_plot_dict.get('regulatory', False)

            # Next loop over all of the domains.
            # Loop also over the domain types.
            domain_types = stat_dict['domain_type']
            domain_names = stat_dict['domain_name']
            for domain in range(len(domain_types)):
                domain_type = domain_types[domain]
                domain_name = domain_names[domain]

                # The tables and text files will be output at this step in loop.
                # Create an empty pandas dataarray.
                df_o_d = pd.DataFrame()
                # Determine outname
                if cal_reg:
                    outname = "{}.{}.{}.{}.{}.{}".format('stats', obsvar+'_reg', domain_type, domain_name, startdatename, enddatename)
                else:
                    outname = "{}.{}.{}.{}.{}.{}".format('stats', obsvar, domain_type, domain_name, startdatename, enddatename)

                # Determine plotting kwargs
                if 'output_table_kwargs' in stat_dict.keys():
                    out_table_kwargs = stat_dict['output_table_kwargs']
                else:
                    out_table_kwargs = None

                # Add Stat ID and FullName to pandas dictionary.
                df_o_d['Stat_ID'] = stat_list
                df_o_d['Stat_FullName'] = stat_fullname_ns

                # Specify title for stat plots. 
                if cal_reg:
                    if 'ylabel_reg_plot' in obs_plot_dict.keys():
                        title = obs_plot_dict['ylabel_reg_plot'] + ': ' + domain_type + ' ' + domain_name
                    else:
                        title = obsvar + '_reg: ' + domain_type + ' ' + domain_name
                else:
                    if 'ylabel_plot' in obs_plot_dict.keys():
                        title = obs_plot_dict['ylabel_plot'] + ': ' + domain_type + ' ' + domain_name
                    else:
                        title = obsvar + ': ' + domain_type + ' ' + domain_name

                # Finally Loop through each of the pairs
                for p_label in pair_labels:
                    p = self.paired[p_label]
                    # Create an empty list to store the stat_var
                    p_stat_list = []

                    # Loop through each of the stats
                    for stat_grp in stat_list:

                        # find the pair model label that matches the obs var
                        index = p.obs_vars.index(obsvar)
                        modvar = p.model_vars[index]

                        # Adjust the modvar as done in pairing script, if the species name in obs and model are the same.
                        if obsvar == modvar:
                            modvar = modvar + '_new'

                        # convert to dataframe
                        pairdf_all = p.obj.to_dataframe(dim_order=["time", "x"])

                        # Select only the analysis time window.
                        pairdf_all = pairdf_all.loc[self.start_time : self.end_time]

                        # Query selected points if applicable
                        if domain_type != 'all':
                            pairdf_all.query(domain_type + ' == ' + '"' + domain_name + '"', inplace=True)
                        
                        # Query with filter options
                        if 'data_proc' in stat_dict:
                            if 'filter_dict' in stat_dict['data_proc'] and 'filter_string' in stat_dict['data_proc']:
                                raise Exception("For statistics, only one of filter_dict and filter_string can be specified.")
                            elif 'filter_dict' in stat_dict['data_proc']:
                                filter_dict = stat_dict['data_proc']['filter_dict']
                                for column in filter_dict.keys():
                                    filter_vals = filter_dict[column]['value']
                                    filter_op = filter_dict[column]['oper']
                                    if filter_op == 'isin':
                                        pairdf_all.query(f'{column} == {filter_vals}', inplace=True)
                                    elif filter_op == 'isnotin':
                                        pairdf_all.query(f'{column} != {filter_vals}', inplace=True)
                                    else:
                                        pairdf_all.query(f'{column} {filter_op} {filter_vals}', inplace=True)
                            elif 'filter_string' in stat_dict['data_proc']:
                                pairdf_all.query(stat_dict['data_proc']['filter_string'], inplace=True)

                        # Drop sites with greater than X percent NAN values
                        if 'data_proc' in stat_dict:
                            if 'rem_obs_by_nan_pct' in stat_dict['data_proc']:
                                grp_var = stat_dict['data_proc']['rem_obs_by_nan_pct']['group_var']
                                pct_cutoff = stat_dict['data_proc']['rem_obs_by_nan_pct']['pct_cutoff']

                                if stat_dict['data_proc']['rem_obs_by_nan_pct']['times'] == 'hourly':
                                    # Select only hours at the hour
                                    hourly_pairdf_all = pairdf_all.reset_index().loc[pairdf_all.reset_index()['time'].dt.minute==0,:]
                                    
                                    # calculate total obs count, obs count with nan removed, and nan percent for each group
                                    grp_fullcount = hourly_pairdf_all[[grp_var,obsvar]].groupby(grp_var).size().rename({0:obsvar})
                                    grp_nonan_count = hourly_pairdf_all[[grp_var,obsvar]].groupby(grp_var).count() # counts only non NA values    
                                else: 
                                    # calculate total obs count, obs count with nan removed, and nan percent for each group
                                    grp_fullcount = pairdf_all[[grp_var,obsvar]].groupby(grp_var).size().rename({0:obsvar})
                                    grp_nonan_count = pairdf_all[[grp_var,obsvar]].groupby(grp_var).count() # counts only non NA values  
                                
                                grp_pct_nan = 100 - grp_nonan_count.div(grp_fullcount,axis=0)*100
                                
                                # make list of sites meeting condition and select paired data by this by this
                                grp_select = grp_pct_nan.query(obsvar + ' < ' + str(pct_cutoff)).reset_index()
                                pairdf_all = pairdf_all.loc[pairdf_all[grp_var].isin(grp_select[grp_var].values)]
                        
                        # Drop NaNs for model and observations in all cases.
                        pairdf = pairdf_all.reset_index().dropna(subset=[modvar, obsvar])

                        # JianHe: do we need provide a warning if pairdf is empty (no valid obsdata) for specific subdomain?
                        if pairdf[obsvar].isnull().all() or pairdf.empty:
                            print('Warning: no valid obs found for '+domain_name)
                            p_stat_list.append('NaN')
                            continue

                        if cal_reg:
                            # Process regulatory values
                            df2 = (
                                pairdf.copy()
                                .groupby("siteid")
                                .resample('H', on='time_local')
                                .mean()
                                .reset_index()
                            )

                            if obsvar == 'PM2.5':
                                pairdf_reg = splots.make_24hr_regulatory(df2,[obsvar,modvar]).rename(index=str,columns={obsvar+'_y':obsvar+'_reg',modvar+'_y':modvar+'_reg'})
                            elif obsvar == 'OZONE':
                                pairdf_reg = splots.make_8hr_regulatory(df2,[obsvar,modvar]).rename(index=str,columns={obsvar+'_y':obsvar+'_reg',modvar+'_y':modvar+'_reg'})
                            else:
                                print('Warning: no regulatory calculations found for ' + obsvar + '. Setting stat calculation to NaN.')
                                del df2
                                p_stat_list.append('NaN')
                                continue
                            del df2
                            if len(pairdf_reg[obsvar+'_reg']) == 0:
                                print('No valid data for '+obsvar+'_reg. Setting stat calculation to NaN.')
                                p_stat_list.append('NaN')
                                continue
                            else:
                                # Drop NaNs for model and observations in all cases.
                                pairdf2 = pairdf_reg.reset_index().dropna(subset=[modvar+'_reg', obsvar+'_reg'])

                        # Create empty list for all dom
                        # Calculate statistic and append to list
                        if obsvar == 'WD':  # Use separate calculations for WD
                            p_stat_list.append(proc_stats.calc(pairdf, stat=stat_grp, obsvar=obsvar, modvar=modvar, wind=True))
                        else:
                            if cal_reg:
                                p_stat_list.append(proc_stats.calc(pairdf2, stat=stat_grp, obsvar=obsvar+'_reg', modvar=modvar+'_reg', wind=False))
                            else:
                                p_stat_list.append(proc_stats.calc(pairdf, stat=stat_grp, obsvar=obsvar, modvar=modvar, wind=False))

                    # Save the stat to a dataarray
                    df_o_d[p_label] = p_stat_list

                if self.output_dir is not None:
                    outname = self.output_dir + '/' + outname  # Extra / just in case.

                # Save the pandas dataframe to a txt file
                # Save rounded output
                df_o_d = df_o_d.round(round_output)
                df_o_d.to_csv(path_or_buf=outname + '.csv', index=False)

                if stat_dict['output_table'] == True:
                    # Output as a table graphic too.
                    # Change to use the name with full spaces.
                    df_o_d['Stat_FullName'] = stat_fullname_s
 
                    proc_stats.create_table(df_o_d.drop(columns=['Stat_ID']),
                                            outname=outname,
                                            title=title,
                                            out_table_kwargs=out_table_kwargs,
                                            debug=self.debug
                                           )
