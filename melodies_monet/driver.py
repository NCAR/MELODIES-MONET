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
        self.variable_summing = None
        self.resample = None
        self.time_var = None
        self.regrid_method = None

    def __repr__(self):
        return (
            f"{type(self).__name__}(\n"
            f"    obs={self.obs!r},\n"
            f"    label={self.label!r},\n"
            f"    file={self.file!r},\n"
            f"    obj={repr(self.obj) if self.obj is None else '...'},\n"
            f"    type={self.type!r},\n"
            f"    sat_type={self.sat_type!r},\n"
            f"    data_proc={self.data_proc!r},\n"
            f"    variable_dict={self.variable_dict!r},\n"
            f"    resample={self.resample!r},\n"
            f"    time_var={self.time_var!r},\n"
            f"    regrid_method={self.regrid_method!r},\n"
            ")"
        )

    def open_obs(self, time_interval=None, control_dict=None):
        """Open the observational data, store data in observation pair,
        and apply mask and scaling.

        Parameters
        ----------
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
            if extension in {'.nc', '.ncf', '.netcdf', '.nc4'}:
                if len(files) > 1:
                    self.obj = xr.open_mfdataset(files)
                else:
                    self.obj = xr.open_dataset(files[0])
            elif extension in ['.ict', '.icartt']:
                assert len(files) == 1, "monetio.icartt.add_data can only read one file"
                self.obj = mio.icartt.add_data(files[0])
            elif extension in ['.csv']:
                from .util.read_util import read_aircraft_obs_csv
                assert len(files) == 1, "MELODIES-MONET can only read one csv file"
                self.obj = read_aircraft_obs_csv(filename=files[0],time_var=self.time_var)
            else:
                raise ValueError(f'extension {extension!r} currently unsupported')
        except Exception as e:
            print('something happened opening file:', e)
            return
        
        self.add_coordinates_ground() # If ground site then add coordinates based on yaml if necessary
        self.mask_and_scale()  # mask and scale values from the control values
        self.rename_vars() # rename any variables as necessary 
        self.sum_variables() 
        self.resample_data()
        self.filter_obs()

    def add_coordinates_ground(self):
        """Add latitude and longitude coordinates to data when the observation type is ground and 
        ground_coordinate is specified
        
        Returns
        -------
        None
        """
                
        # If ground site
        if self.obs_type == 'ground':
            if self.ground_coordinate and isinstance(self.ground_coordinate,dict):
                self.obj['latitude'] = xr.ones_like(self.obj['time'],dtype=np.float64)*self.ground_coordinate['latitude']
                self.obj['longitude'] = xr.ones_like(self.obj['time'],dtype=np.float64)*self.ground_coordinate['longitude']
            elif self.ground_coordinate and ~isinstance(self.ground_coordinate,dict): 
                raise TypeError('The ground_coordinate option must be specified as a dict with keys latitude and longitude.')

    def rename_vars(self):
        """Rename any variables in observation with rename set.
        
        Returns
        -------
        None
        """
        data_vars = self.obj.data_vars
        # For xarray datasets using data_vars does not grab names of coordinates
        if isinstance(self.obj,xr.Dataset):
            data_vars = list(self.obj.data_vars) + list(self.obj.coords)
        
        if self.variable_dict is not None:
            for v in data_vars:
                if v in self.variable_dict:
                    d = self.variable_dict[v]
                    if 'rename' in d:
                        self.obj = self.obj.rename({v:d['rename']})
                        self.variable_dict[d['rename']] = self.variable_dict.pop(v)

    def open_sat_obs(self, time_interval=None, control_dict=None):
        """Methods to opens satellite data observations. 
        Uses in-house python code to open and load observations.
        Alternatively may use the satpy reader.
        Fills the object class associated with the equivalent label (self.label) with satellite observation
        dataset read in from the associated file (self.file) by the satellite file reader

        Parameters
        ----------
        time_interval (optional, default None) : [pandas.Timestamp, pandas.Timestamp]
            If not None, restrict obs to datetime range spanned by time interval [start, end].

        Returns
        -------
        None
        """
        from .util import time_interval_subset as tsub
        from glob import glob
        try:
            if self.sat_type == 'omps_l3':
                print('Reading OMPS L3')
                self.obj = mio.sat._omps_l3_mm.open_dataset(self.file)
            elif self.sat_type == 'omps_nm':
                print('Reading OMPS_NM')
                if time_interval is not None:
                    flst = tsub.subset_OMPS_l2(self.file,time_interval)
                else:
                    flst = self.file

                self.obj = mio.sat._omps_nadir_mm.read_OMPS_nm(flst)

                # couple of changes to move to reader
                self.obj = self.obj.swap_dims({'x':'time'}) # indexing needs
                self.obj = self.obj.sortby('time') # enforce time in order. 
                # restrict observation data to time_interval if using
                # additional development to deal with files crossing intervals needed (eg situations where orbit start at 23hrs, ends next day).
                if time_interval is not None:
                    self.obj = self.obj.sel(time=slice(time_interval[0],time_interval[-1]))

            elif self.sat_type == 'mopitt_l3':
                print('Reading MOPITT')
                if time_interval is not None:
                    flst = tsub.subset_mopitt_l3(self.file,time_interval)
                else:
                    flst = self.file
                self.obj = mio.sat._mopitt_l3_mm.open_dataset(flst, ['column','pressure_surf','apriori_col',
                                                                          'apriori_surf','apriori_prof','ak_col'])

                # Determine if monthly or daily product and set as attribute
                if any(mtype in glob(self.file)[0] for mtype in ('MOP03JM','MOP03NM','MOP03TM')):
                    self.obj.attrs['monthly'] = True
                else:
                    self.obj.attrs['monthly'] = False
                            
            elif self.sat_type == 'modis_l2':
                # from monetio import modis_l2
                print('Reading MODIS L2')
                flst = tsub.subset_MODIS_l2(self.file,time_interval)
                # self.obj = mio.sat._modis_l2_mm.read_mfdataset(
                #     self.file, self.variable_dict, debug=self.debug)
                self.obj = mio.sat._modis_l2_mm.read_mfdataset(
                    flst, self.variable_dict, debug=self.debug)
                # self.obj = granules, an OrderedDict of Datasets, keyed by datetime_str,
                #   with variables: Latitude, Longitude, Scan_Start_Time, parameters, ...
            elif self.sat_type == 'tropomi_l2_no2':
                #from monetio import tropomi_l2_no2
                print('Reading TROPOMI L2 NO2')
                self.obj = mio.sat._tropomi_l2_no2_mm.read_trpdataset(
                    self.file, self.variable_dict, debug=self.debug)
            elif "tempo_l2" in self.sat_type:
                print('Reading TEMPO L2')
                self.obj = mio.sat._tempo_l2_no2_mm.open_dataset(
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
                    
                    # Then replace LLOD_value with LLOD_setvalue (after unit conversion)
                    if 'LLOD_value' in d:
                        self.obj[v].data = self.obj[v].where(self.obj[v] != d['LLOD_value'],d['LLOD_setvalue'])
    
    def sum_variables(self):
        """Sum any variables noted that should be summed to create new variables.
        This occurs after any unit scaling.

        Returns
        -------
        None
        """
        
        try:
            if self.variable_summing is not None:
                for var_new in self.variable_summing.keys():
                    if var_new in self.obj.variables:
                        print('The variable name, {}, already exists and cannot be created with variable_summing.'.format(var_new))
                        raise ValueError
                    var_new_info = self.variable_summing[var_new]
                    if self.variable_dict is None:
                        self.variable_dict = {}
                    self.variable_dict[var_new] = var_new_info
                    for i,var in enumerate(var_new_info['vars']):
                        if i ==0:
                            self.obj[var_new] = self.obj[var].copy()
                        else:
                            self.obj[var_new] += self.obj[var]
        except ValueError as e:
            raise Exception("Something happened when using variable_summing:") from e

    def resample_data(self):
        """Resample the obs df based on the value set in the control file.
        
        Returns
        -------
        None
        """ 
                        
        ##Resample the data
        if self.resample is not None:
            self.obj = self.obj.resample(time=self.resample).mean(dim='time')

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
        self.is_global = False
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
        self.variable_summing = None
        self.plot_kwargs = None
        self.proj = None

    def __repr__(self):
        return (
            f"{type(self).__name__}(\n"
            f"    model={self.model!r},\n"
            f"    is_global={self.is_global!r},\n"
            f"    radius_of_influence={self.radius_of_influence!r},\n"
            f"    mod_kwargs={self.mod_kwargs!r},\n"
            f"    file_str={self.file_str!r},\n"
            f"    label={self.label!r},\n"
            f"    obj={repr(self.obj) if self.obj is None else '...'},\n"
            f"    mapping={self.mapping!r},\n"
            f"    variable_dict={self.variable_dict!r},\n"
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

    def open_model_files(self, time_interval=None, control_dict=None):
        """Open the model files, store data in :class:`model` instance attributes,
        and apply mask and scaling.
        
        Models supported are cmaq, wrfchem, rrfs, and gsdchem.
        If a model is not supported, MELODIES-MONET will try to open 
        the model data using a generic reader. If you wish to include new 
        models, add the new model option to this module.

        Parameters
        ----------
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
        # First make a list of variables not in mapping but from variable_summing, if provided
        if self.variable_summing is not None:
            vars_for_summing  = []
            for var in self.variable_summing.keys():
                vars_for_summing= vars_for_summing + self.variable_summing[var]['vars']
        list_input_var = list(self.variable_dict.keys()) if self.variable_dict is not None else []
        for obs_map in self.mapping:
            if self.variable_summing is not None:
                list_input_var = list_input_var + list(set(self.mapping[obs_map].keys()).union(set(vars_for_summing)) - set(self.variable_summing.keys()) - set(list_input_var) )
            else:
                list_input_var = list_input_var + list(set(self.mapping[obs_map].keys()) - set(list_input_var))
        #Only certain models need this option for speeding up i/o.

        # Remove standardized variable names that user may have requested to pair on or output in MM
        # as they will be added anyway and here would cause [var_list] to fail in the below model readers.
        for vn in ["temperature_k", "pres_pa_mid"]:
            if vn in list_input_var:
                list_input_var.remove(vn)

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
            self.obj = mio.models._rrfs_cmaq_mm.open_mfdataset(self.files,**self.mod_kwargs) # add liam 
        elif 'ufschem' in self.model.lower(): # added ufs-chem
            print('**** Reading UFS-CHEM model output...')
            self.mod_kwargs.update({'var_list' : list_input_var})
            self.obj = mio.models._ufschem_v1.open_mfdataset(self.files,**self.mod_kwargs)
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
        elif "camx" in self.model.lower():
            self.mod_kwargs.update({"var_list": list_input_var})
            self.mod_kwargs.update({"surf_only": control_dict['model'][self.label].get('surf_only', False)})
            self.mod_kwargs.update({"fname_met_3D": control_dict['model'][self.label].get('files_vert', None)})
            self.mod_kwargs.update({"fname_met_2D": control_dict['model'][self.label].get('files_met_surf', None)})
            self.obj = mio.models._camx_mm.open_mfdataset(self.files, **self.mod_kwargs)
        elif 'raqms' in self.model.lower():
            self.mod_kwargs.update({'var_list': list_input_var})
            if time_interval is not None:
                # fill filelist with subset
                print('subsetting model files to interval')
                file_list = tsub.subset_model_filelist(self.files,'%m_%d_%Y_%HZ','6H',time_interval)
            else:
                file_list = self.files
            if len(file_list) > 1:
                self.obj = mio.models.raqms.open_mfdataset(file_list,**self.mod_kwargs)
            else:
                self.obj = mio.models.raqms.open_dataset(file_list)
            if 'ptrop' in self.obj and 'pres_pa_trop' not in self.obj:
                self.obj = self.obj.rename({'ptrop':'pres_pa_trop'})

        else:
            print('**** Reading Unspecified model output. Take Caution...')
            if len(self.files) > 1:
                self.obj = xr.open_mfdataset(self.files,**self.mod_kwargs)
            else:
                self.obj = xr.open_dataset(self.files[0],**self.mod_kwargs)
        self.mask_and_scale()
        self.rename_vars() # rename any variables as necessary 
        self.sum_variables()

    def rename_vars(self):
        """Rename any variables in model with rename set.
        
        Returns
        -------
        None
        """ 
        data_vars = self.obj.data_vars
        if self.variable_dict is not None:
            for v in data_vars:
                if v in self.variable_dict:
                    d = self.variable_dict[v]
                    if 'rename' in d:
                        self.obj = self.obj.rename({v:d['rename']})
                        self.variable_dict[d['rename']] = self.variable_dict.pop(v)

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
    
    def sum_variables(self):
        """Sum any variables noted that should be summed to create new variables.
        This occurs after any unit scaling.

        Returns
        -------
        None
        """
        
        try:
            if self.variable_summing is not None:
                for var_new in self.variable_summing.keys():
                    if var_new in self.obj.variables:
                        print('The variable name, {}, already exists and cannot be created with variable_summing.'.format(var_new))
                        raise ValueError
                    var_new_info = self.variable_summing[var_new]
                    if self.variable_dict is None:
                        self.variable_dict = {}
                    self.variable_dict[var_new] = var_new_info
                    for i,var in enumerate(var_new_info['vars']):
                        if i ==0:
                            self.obj[var_new] = self.obj[var].copy()
                        else:
                            self.obj[var_new] += self.obj[var]
        except ValueError as e:
            raise Exception("Something happened when using variable_summing:") from e

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
        self.regrid = False  # Default to False
        self.target_grid = None
        self.obs_regridders = None
        self.model_regridders = None
        self.obs_grid = None
        self.obs_edges = None
        self.obs_gridded_data = {}
        self.obs_gridded_count = {}
        self.obs_gridded_dataset = None
        self.add_logo = True
        """bool, default=True : Add the MELODIES MONET logo to the plots."""
        self.pairing_kwargs = {}


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
            f"    regrid={self.regrid!r},\n"
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
        if 'start_time' in self.control_dict['analysis'].keys():
            self.start_time = pd.Timestamp(self.control_dict['analysis']['start_time'])
        if 'end_time' in self.control_dict['analysis'].keys():
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
        if 'add_logo' in self.control_dict['analysis'].keys():
            self.add_logo = self.control_dict['analysis']['add_logo']

        if 'regrid' in self.control_dict['analysis'].keys():
            self.regrid = self.control_dict['analysis']['regrid']
        if 'target_grid' in self.control_dict['analysis'].keys():
            self.target_grid = self.control_dict['analysis']['target_grid']

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
        
        # specific arguments for pairing options
        if 'pairing_kwargs' in self.control_dict['analysis'].keys():
            self.pairing_kwargs = self.control_dict['analysis']['pairing_kwargs']
            
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

    def setup_regridders(self):
        """Create an obs xesmf.Regridder from base and target grids specified in the control_dict

        Returns
        -------
        None
        """
        from .util import regrid_util
        if self.regrid:
            if self.target_grid == 'obs_grid':
                self.model_regridders = regrid_util.setup_regridder(self.control_dict, config_group='model', target_grid=self.da_obs_grid)
            else:
                self.obs_regridders = regrid_util.setup_regridder(self.control_dict, config_group='obs')
                self.model_regridders = regrid_util.setup_regridder(self.control_dict, config_group='model')

    def open_models(self, time_interval=None,load_files=True):
        """Open all models listed in the input yaml file and create a :class:`model` 
        object for each of them, populating the :attr:`models` dict.

        Parameters
        ----------
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
                if "is_global" in self.control_dict['model'][mod].keys():
                    m.is_global = self.control_dict['model'][mod]['is_global']
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
                if 'variable_summing' in self.control_dict['model'][mod].keys():
                    m.variable_summing = self.control_dict['model'][mod]['variable_summing']
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
                    m.open_model_files(time_interval=time_interval, control_dict=self.control_dict)
                self.models[m.label] = m

    def open_obs(self, time_interval=None, load_files=True):
        """Open all observations listed in the input yaml file and create an 
        :class:`observation` instance for each of them,
        populating the :attr:`obs` dict.

        Parameters
        ----------
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
                if 'variable_summing' in self.control_dict['obs'][obs].keys():
                    o.variable_summing = self.control_dict['obs'][obs]['variable_summing']
                if 'resample' in self.control_dict['obs'][obs].keys():
                    o.resample = self.control_dict['obs'][obs]['resample']
                if 'time_var' in self.control_dict['obs'][obs].keys():
                    o.time_var = self.control_dict['obs'][obs]['time_var']
                if 'ground_coordinate' in self.control_dict['obs'][obs].keys():
                    o.ground_coordinate = self.control_dict['obs'][obs]['ground_coordinate']
                if 'sat_type' in self.control_dict['obs'][obs].keys():
                    o.sat_type = self.control_dict['obs'][obs]['sat_type']
                if load_files:
                    if o.obs_type in ['sat_swath_sfc', 'sat_swath_clm', 'sat_grid_sfc',\
                                        'sat_grid_clm', 'sat_swath_prof']:
                        o.open_sat_obs(time_interval=time_interval, control_dict=self.control_dict)
                    else:
                        o.open_obs(time_interval=time_interval, control_dict=self.control_dict)
                self.obs[o.label] = o

    def setup_obs_grid(self):
        """
        Setup a uniform observation grid.
        """
        from .util import grid_util
        ntime = self.control_dict['obs_grid']['ntime']
        nlat = self.control_dict['obs_grid']['nlat']
        nlon = self.control_dict['obs_grid']['nlon']
        self.obs_grid, self.obs_edges = grid_util.generate_uniform_grid(
            self.control_dict['obs_grid']['start_time'],
            self.control_dict['obs_grid']['end_time'],
            ntime, nlat, nlon)

        self.da_obs_grid = xr.DataArray(dims=['lon', 'lat'],
            coords={'lon': self.obs_grid['longitude'],
                    'lat': self.obs_grid['latitude']})
        # print(self.da_obs_grid)

        for obs in self.control_dict['obs']:
            for var in self.control_dict['obs'][obs]['variables']:
                print('initializing gridded data and counts ', obs, var)
                self.obs_gridded_data[obs + '_' + var] = np.zeros([ntime, nlon, nlat], dtype=np.float32)
                self.obs_gridded_count[obs + '_' + var] = np.zeros([ntime, nlon, nlat], dtype=np.int32)

    def update_obs_gridded_data(self):
        from .util import grid_util
        """
        Update observation grid cell values and counts,
        for all observation datasets and parameters.
        """
        for obs in self.obs:
            for obs_time in self.obs[obs].obj:
                print('updating obs time: ', obs, obs_time)
                obs_timestamp = pd.to_datetime(
                    obs_time, format='%Y%j%H%M').timestamp()
                # print(obs_timestamp)
                for var in self.obs[obs].obj[obs_time]:
                    key = obs + '_' + var
                    print(key)
                    n_obs = self.obs[obs].obj[obs_time][var].size
                    grid_util.update_data_grid(
                        self.obs_edges['time_edges'],
                        self.obs_edges['lon_edges'],
                        self.obs_edges['lat_edges'],
                        np.full(n_obs, obs_timestamp, dtype=np.float32),
                        self.obs[obs].obj[obs_time].coords['lon'].values.flatten(),
                        self.obs[obs].obj[obs_time].coords['lat'].values.flatten(),
                        self.obs[obs].obj[obs_time][var].values.flatten(),
                        self.obs_gridded_count[key],
                        self.obs_gridded_data[key])

    def normalize_obs_gridded_data(self):
        from .util import grid_util
        """
        Normalize observation grid cell values where counts is not zero.
        Create data arrays for the obs_gridded_dataset dictionary.
        """
        self.obs_gridded_dataset = xr.Dataset()

        for obs in self.obs:
            for var in self.control_dict['obs'][obs]['variables']:
                key = obs + '_' + var
                print(key)
                grid_util.normalize_data_grid(
                    self.obs_gridded_count[key],
                    self.obs_gridded_data[key])
                da_data = xr.DataArray(
                    self.obs_gridded_data[key],
                    dims=['time', 'lon', 'lat'],
                    coords={'time': self.obs_grid['time'],
                            'lon': self.obs_grid['longitude'],
                            'lat': self.obs_grid['latitude']})
                da_count = xr.DataArray(
                    self.obs_gridded_count[key],
                    dims=['time', 'lon', 'lat'],
                    coords={'time': self.obs_grid['time'],
                            'lon': self.obs_grid['longitude'],
                            'lat': self.obs_grid['latitude']})
                self.obs_gridded_dataset[key + '_data'] = da_data
                self.obs_gridded_dataset[key + '_count'] = da_count

    def pair_data(self, time_interval=None):
        """Pair all observations and models in the analysis class
        (i.e., those listed in the input yaml file) together,
        populating the :attr:`paired` dict.

        Parameters
        ----------
        time_interval (optional, default None) : [pandas.Timestamp, pandas.Timestamp]
            If not None, restrict pairing to datetime range spanned by time interval [start, end].


        Returns
        -------
        None
        """
        print('1, in pair data')
        for model_label in self.models:
            mod = self.models[model_label]
            # Now we have the models we need to loop through the mapping table for each network and pair the data
            # each paired dataset will be output to a netcdf file with 'model_label_network.nc'
            for obs_to_pair in mod.mapping.keys():
                # get the variables to pair from the model data (ie don't pair all data)
                keys = [key for key in mod.mapping[obs_to_pair].keys()]
                obs_vars = [mod.mapping[obs_to_pair][key] for key in keys]

                if mod.variable_dict is not None:
                    mod_vars = [key for key in mod.variable_dict.keys()]
                else:
                    mod_vars = []
                
                # unstructured grid check - lon/lat variables should be explicitly added 
                # in addition to comparison variables
                if mod.obj.attrs.get("mio_scrip_file", False):
                    lonlat_list = [ 'lon', 'lat', 'longitude', 'latitude', 'Longitude', 'Latitude' ]
                    for ll in lonlat_list:
                        if ll in mod.obj.data_vars:
                            keys += [ll]

                if mod.variable_dict is not None:
                    model_obj = mod.obj[keys+mod_vars]
                else:
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
                    print('saving pair')
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
                    
                # if aircraft (aircraft observation)
                elif obs.obs_type.lower() == 'aircraft':
                    from .util.tools import vert_interp
                    # convert this to pandas dataframe unless already done because second time paired this obs
                    if not isinstance(obs.obj, pd.DataFrame):
                        obs.obj = obs.obj.to_dataframe()
                    
                    #drop any variables where coords NaN
                    obs.obj = obs.obj.reset_index().dropna(subset=['pressure_obs','latitude','longitude']).set_index('time')
                    
                    # do the facy trick to convert to get something useful for MONET
                    # this converts to dimensions of x and y
                    # you may want to make pressure / msl a coordinate too
                    new_ds_obs = obs.obj.rename_axis('time_obs').reset_index().monet._df_to_da().set_coords(['time_obs','pressure_obs'])
                    
                    #Nearest neighbor approach to find closest grid cell to each point.
                    ds_model = m.util.combinetool.combine_da_to_da(model_obj,new_ds_obs,merge=False)
                    #Interpolate based on time in the observations
                    ds_model = ds_model.interp(time=ds_model.time_obs.squeeze())

                    # Debugging: Print the variables in ds_model to verify 'pressure_model' is included  ##qzr++
                    #print("Variables in ds_model after combine_da_to_da and interp:", ds_model.variables)
                    
                    # Ensure 'pressure_model' is included in ds_model (checked it exists)
                    #if 'pressure_model' not in ds_model:
                     #   raise KeyError("'pressure_model' is missing in the model dataset")   #qzr++
                    
                    paired_data = vert_interp(ds_model,obs.obj,keys+mod_vars)
                    print('After pairing: ', paired_data)

                    # Ensure 'pressure_model' is included in the DataFrame (pairdf) #qzr++
                    #if 'pressure_model' not in paired_data.columns:
                       # raise KeyError("'pressure_model' is missing in the paired_data")   #qzr++

                      
                    
                    # this outputs as a pandas dataframe.  Convert this to xarray obj
                    p = pair()
                    p.type = 'aircraft'
                    p.radius_of_influence = None
                    p.obs = obs.label
                    p.model = mod.label
                    p.model_vars = keys
                    p.obs_vars = obs_vars
                    p.filename = '{}_{}.nc'.format(p.obs, p.model)
                    p.obj = paired_data.set_index('time').to_xarray().expand_dims('x').transpose('time','x')
                    label = "{}_{}".format(p.obs, p.model)
                    self.paired[label] = p
                    # write_util.write_ncf(p.obj,p.filename) # write out to file

                elif obs.obs_type.lower() == 'sonde':
                    from .util.tools import vert_interp
                    # convert this to pandas dataframe unless already done because second time paired this obs
                    if not isinstance(obs.obj, pd.DataFrame):
                        obs.obj = obs.obj.to_dataframe()
                    #drop any variables where coords NaN
                    obs.obj = obs.obj.reset_index().dropna(subset=['pressure_obs','latitude','longitude']).set_index('time')
 
                    import datetime 
                    plot_dict_sonde = self.control_dict['plots']
                    for grp_sonde, grp_dict_sonde in plot_dict_sonde.items():
                        plot_type_sonde = grp_dict_sonde['type']
                        plot_sonde_type_list_all = ['vertical_single_date','vertical_boxplot_os','density_scatter_plot_os']
                        if plot_type_sonde in plot_sonde_type_list_all:
                           station_name_sonde = grp_dict_sonde['station_name']
                           cds_sonde = grp_dict_sonde['compare_date_single']
                           obs.obj=obs.obj.loc[obs.obj['station']==station_name_sonde[0]]
                           obs.obj=obs.obj.loc[datetime.datetime(
                               cds_sonde[0],cds_sonde[1],cds_sonde[2],cds_sonde[3],cds_sonde[4],cds_sonde[5])]
                           break
                   
                    # do the facy trick to convert to get something useful for MONET
                    # this converts to dimensions of x and y
                    # you may want to make pressure / msl a coordinate too
                    new_ds_obs = obs.obj.rename_axis('time_obs').reset_index().monet._df_to_da().set_coords(['time_obs','pressure_obs'])
                    #Nearest neighbor approach to find closest grid cell to each point.
                    ds_model = m.util.combinetool.combine_da_to_da(model_obj,new_ds_obs,merge=False)
                    #Interpolate based on time in the observations
                    ds_model = ds_model.interp(time=ds_model.time_obs.squeeze())
                    paired_data = vert_interp(ds_model,obs.obj,keys+mod_vars)
                    print('In pair function, After pairing: ', paired_data)
                    # this outputs as a pandas dataframe.  Convert this to xarray obj
                    p = pair()
                    p.type = 'sonde'
                    p.radius_of_influence = None
                    p.obs = obs.label
                    p.model = mod.label
                    p.model_vars = keys
                    p.obs_vars = obs_vars
                    p.filename = '{}_{}.nc'.format(p.obs, p.model)
                    p.obj = paired_data.set_index('time').to_xarray().expand_dims('x').transpose('time','x')
                    label = "{}_{}".format(p.obs, p.model)
                    self.paired[label] = p

                    # write_util.write_ncf(p.obj,p.filename) # write out to file 
                # If mobile surface data or single ground site surface data
                elif obs.obs_type.lower() == 'mobile' or obs.obs_type.lower() == 'ground':
                    from .util.tools import mobile_and_ground_pair
                    # convert this to pandas dataframe unless already done because second time paired this obs
                    if not isinstance(obs.obj, pd.DataFrame):
                        obs.obj = obs.obj.to_dataframe()
                    
                    #drop any variables where coords NaN
                    obs.obj = obs.obj.reset_index().dropna(subset=['latitude','longitude']).set_index('time')
                    
                    # do the facy trick to convert to get something useful for MONET
                    # this converts to dimensions of x and y
                    # you may want to make pressure / msl a coordinate too
                    new_ds_obs = obs.obj.rename_axis('time_obs').reset_index().monet._df_to_da().set_coords(['time_obs'])
                    
                    #Nearest neighbor approach to find closest grid cell to each point.
                    ds_model = m.util.combinetool.combine_da_to_da(model_obj,new_ds_obs,merge=False)
                    #Interpolate based on time in the observations
                    ds_model = ds_model.interp(time=ds_model.time_obs.squeeze())
                    
                    paired_data = mobile_and_ground_pair(ds_model,obs.obj,keys+mod_vars)
                    print('After pairing: ', paired_data)
                    # this outputs as a pandas dataframe.  Convert this to xarray obj
                    p = pair()
                    if obs.obs_type.lower() == 'mobile':
                        p.type = 'mobile'
                    elif obs.obs_type.lower() == 'ground':
                        p.type = 'ground'
                    p.radius_of_influence = None
                    p.obs = obs.label
                    p.model = mod.label
                    p.model_vars = keys
                    p.obs_vars = obs_vars
                    p.filename = '{}_{}.nc'.format(p.obs, p.model)
                    p.obj = paired_data.set_index('time').to_xarray().expand_dims('x').transpose('time','x')
                    label = "{}_{}".format(p.obs, p.model)
                    self.paired[label] = p
                
                # TODO: add other network types / data types where (ie flight, satellite etc)
                # if sat_swath_clm (satellite l2 column products)
                elif obs.obs_type.lower() == 'sat_swath_clm':
                    # grab kwargs for pairing. Use default if not specified
                    pairing_kws = {'apply_ak':True,'mod_to_overpass':False}
                    for key in self.pairing_kwargs.get(obs.obs_type.lower(), {}):
                        pairing_kws[key] = self.pairing_kwargs[obs.obs_type.lower()][key]
                    if 'apply_ak' not in self.pairing_kwargs.get(obs.obs_type.lower(), {}):
                        print('WARNING: The satellite pairing option apply_ak is being set to True because it was not specified in the YAML. Pairing will fail if there is no AK available.')
                    
                    if obs.sat_type == 'omps_nm':
                        
                        from .util import satellite_utilities as sutil
                        
                        # necessary observation index things 
                        ## the along track coordinate dim sometimes needs to be time and other times an unassigned 'x'
                        if 'time' in obs.obj.dims:
                            obs.obj = obs.obj.sel(time=slice(self.start_time,self.end_time))
                            obs.obj = obs.obj.swap_dims({'time':'x'})
                        if pairing_kws['apply_ak'] is True:
                            model_obj = mod.obj[keys+['pres_pa_mid','surfpres_pa']]
                            
                            paired_data = sutil.omps_nm_pairing_apriori(model_obj,obs.obj,keys)
                        else:
                            model_obj = mod.obj[keys+['dp_pa']]
                            paired_data = sutil.omps_nm_pairing(model_obj,obs.obj,keys)

                        paired_data = paired_data.where(paired_data.ozone_column.notnull())
                        p = pair()
                        p.type = obs.obs_type
                        p.obs = obs.label
                        p.model = mod.label
                        p.model_vars = keys
                        p.obs_vars = obs_vars
                        p.obj = paired_data 
                        label = '{}_{}'.format(p.obs,p.model)
                        self.paired[label] = p

                    if obs.sat_type == 'tropomi_l2_no2':
                        from .util import sat_l2_swath_utility as no2util
                        from .util import satellite_utilities as sutil

                        # calculate model no2 trop. columns. M.Li
                        # to fix the "time" duplicate error
                        model_obj = mod.obj
                        i_no2_varname = [i for i,x in enumerate(obs_vars) if x == 'nitrogendioxide_tropospheric_column']
                        if len(i_no2_varname) > 1:
                            print('The TROPOMI NO2 variable is matched to more than one model variable.')
                            print('Pairing is being done for model variable: '+keys[i_no2_varname[0]])
                        no2_varname = keys[i_no2_varname[0]]

                        if pairing_kws['mod_to_overpass']:
                            print('sampling model to 13:30 local overpass time')
                            overpass_datetime = pd.date_range(self.start_time.replace(hour=13,minute=30),
                                                              self.end_time.replace(hour=13,minute=30),freq='D')
                            model_obj = sutil.mod_to_overpasstime(model_obj,overpass_datetime,partial_col=no2_varname)
                            # enforce dimension order is time, z, y, x
                            model_obj = model_obj.transpose('time','z','y','x',...)
                        else:
                            print('Warning: The pairing_kwarg mod_to_overpass is False.')
                            print('Pairing will proceed assuming that the model data is already at overpass time.')
                            from .util.tools import calc_partialcolumn
                            model_obj[f'{no2_varname}_col'] = calc_partialcolumn(model_obj,var=no2_varname)
                        if pairing_kws['apply_ak'] is True:
                            paired_data = no2util.trp_interp_swatogrd_ak(obs.obj, model_obj,no2varname=no2_varname)
                        else:
                            paired_data = no2util.trp_interp_swatogrd(obs.obj, model_obj, no2varname=no2_varname)


                        p = pair()

                        paired_data_cp = paired_data.sel(time=slice(self.start_time.date(),self.end_time.date())).copy()

                        p.type = obs.obs_type
                        p.obs = obs.label
                        p.model = mod.label
                        p.model_vars = keys
                        p.obs_vars = obs_vars
                        p.obj = paired_data_cp 
                        label = '{}_{}'.format(p.obs,p.model)

                        self.paired[label] = p

                    if 'tempo_l2' in obs.sat_type:
                        from .util import sat_l2_swath_utility_tempo as sutil

                        if obs.sat_type == 'tempo_l2_no2':
                            sat_sp = 'NO2'
                            sp = 'vertical_column_troposphere'
                            key = "tempo_l2_no2"
                        elif obs.sat_type == 'tempo_l2_hcho':
                            sat_sp = 'HCHO'
                            sp = 'vertical_column'
                            key = "tempo_l2_hcho"
                        else:
                            raise KeyError(f" You asked for {obs.sat_type}. "
                                           + "Only NO2 and HCHO L2 data have been implemented")
                        mod_sp = [
                            k_sp for k_sp, v in mod.mapping[key].items() if v == sp
                        ]

                        regrid_method = obs.regrid_method if obs.regrid_method is not None else "bilinear"
                        paired_data_atswath = sutil.regrid_and_apply_weights(
                            obs.obj, mod.obj, species=mod_sp, method=regrid_method, tempo_sp=sat_sp
                        )
                        paired_data_atgrid = sutil.back_to_modgrid_multiscan(
                            paired_data_atswath, model_obj, method=regrid_method
                        )

                        p = pair()

                        paired_data = paired_data_atgrid.sel(time=slice(self.start_time, self.end_time))

                        p.type = obs.obs_type
                        p.obs = obs.label
                        p.model = mod.label
                        p.model_vars = keys
                        p.obs_vars = obs_vars
                        p.obj = paired_data
                        label = "{}_{}".format(p.obs,p.model)
                        p.filename = "{}.nc".format(label)

                        self.paired[label] = p
                        
                # if sat_grid_clm (satellite l3 column products)
                elif obs.obs_type.lower() == 'sat_grid_clm':
                    # grab kwargs for pairing. Use default if not specified
                    pairing_kws = {'apply_ak':True,'mod_to_overpass':False}
                    for key in self.pairing_kwargs.get(obs.obs_type.lower(), {}):
                        pairing_kws[key] = self.pairing_kwargs[obs.obs_type.lower()][key]
                    if 'apply_ak' not in self.pairing_kwargs[obs.obs_type.lower()]:
                        print('WARNING: The satellite pairing option apply_ak is being set to True because it was not specified in the YAML. Pairing will fail if there is no AK available.')
                    if len(keys) > 1: 
                        print('Caution: More than 1 variable is included in mapping keys.')
                        print('Pairing code is calculating a column for {}'.format(keys[0])) 
                    if obs.sat_type == 'omps_l3':
                        from .util import satellite_utilities as sutil
                        # trim obs array to only data within analysis window
                        obs_dat = obs.obj.sel(time=slice(self.start_time.date(),self.end_time.date()))#.copy()
                        mod_dat = mod.obj.sel(time=slice(self.start_time.date(),self.end_time.date()))
                        paired_obsgrid = sutil.omps_l3_daily_o3_pairing(mod_dat,obs_dat,keys[0])
                       
                        p = pair()
                        p.type = obs.obs_type
                        p.obs = obs.label
                        p.model = mod.label
                        p.model_vars = keys
                        p.obs_vars = obs_vars
                        p.obj = paired_obsgrid
                        label = '{}_{}'.format(p.obs,p.model)
                        self.paired[label] = p

                    elif obs.sat_type == 'mopitt_l3':
                        from .util import satellite_utilities as sutil
                        
                        if pairing_kws['apply_ak']: 
                            model_obj = mod.obj[keys+['pres_pa_mid']]
                            
                            # Sample model to observation overpass time
                            if pairing_kws['mod_to_overpass']:
                                print('sampling model to 10:30 local overpass time')
                                overpass_datetime = pd.date_range(self.start_time.replace(hour=10,minute=30),
                                                                  self.end_time.replace(hour=10,minute=30),freq='D')
                                model_obj = sutil.mod_to_overpasstime(model_obj,overpass_datetime)
                            # trim to only data within analysis window, as averaging kernels can't be applied outside it
                            obs_dat = obs.obj.sel(time=slice(self.start_time.date(),self.end_time.date()))
                            model_obj = model_obj.sel(time=slice(self.start_time.date(),self.end_time.date()))
                            # interpolate model to observation, calculate column with averaging kernels applied
                            paired = sutil.mopitt_l3_pairing(model_obj,obs_dat,keys[0],global_model=mod.is_global)
                            p = pair()
                            p.type = obs.obs_type
                            p.obs = obs.label
                            p.model = mod.label
                            p.model_vars = keys
                            p.model_vars[0] += '_column_model'
                            p.obs_vars = obs_vars
                            p.obj = paired
                            label ='{}_{}'.format(p.obs,p.model)
                            self.paired[label] = p
                        else:
                            print("Pairing without averaging kernel has not been enabled for this dataset")

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
        
        from .util.tools import resample_stratify
        from .util.region_select import select_region
        import matplotlib.pyplot as plt
        pair_keys = list(self.paired.keys())
        if self.paired[pair_keys[0]].type.lower() in ['sat_grid_clm','sat_swath_clm']:
            from .plots import satplots as splots,savefig
        else: 
            from .plots import surfplots as splots, savefig
            from .plots import aircraftplots as airplots
            from .plots import sonde_plots as sondeplots
        from .plots import xarray_plots as xrplots
        if not self.add_logo:
            savefig.keywords.update(decorate=False)

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

        # Loop through the plot_dict items
        for grp, grp_dict in plot_dict.items():
            
            # Read the interquartile_style argument (for vertprofile plot type) if it exists
            if grp_dict.get('type') == 'vertprofile':
                interquartile_style = grp_dict.get('data_proc', {}).get('interquartile_style', 'shading')
            else:
                interquartile_style = None

            pair_labels = grp_dict['data']
            # Get the plot type
            plot_type = grp_dict['type']

            #read-in special settings for multi-boxplot
            if plot_type == 'multi_boxplot':
                region_name = grp_dict['region_name'] 
                region_list = grp_dict['region_list']
                model_name_list = grp_dict['model_name_list']     

            #read-in special settings for ozone sonde related plots
            if plot_type in {'vertical_single_date', 'vertical_boxplot_os', 'density_scatter_plot_os'}:
                altitude_range = grp_dict['altitude_range']
                altitude_method = grp_dict['altitude_method']
                station_name = grp_dict['station_name']
                monet_logo_position = grp_dict['monet_logo_position']
                cds = grp_dict['compare_date_single']
                release_time= datetime.datetime(cds[0],cds[1],cds[2],cds[3],cds[4],cds[5])

                if plot_type == 'vertical_boxplot_os':
                    altitude_threshold_list = grp_dict['altitude_threshold_list']
                elif plot_type == 'density_scatter_plot_os':
                    cmap_method = grp_dict['cmap_method']
                    model_name_list = grp_dict['model_name_list']
                
            #read-in special settings for scorecard
            if plot_type == 'scorecard':
                region_list = grp_dict['region_list']
                region_name = grp_dict['region_name']
                urban_rural_name = grp_dict['urban_rural_name']
                urban_rural_differentiate_value = grp_dict['urban_rural_differentiate_value']
                better_or_worse_method = grp_dict['better_or_worse_method']
                model_name_list = grp_dict['model_name_list']

            #read-in special settings for csi plot
            if plot_type == 'csi':
                threshold_list = grp_dict['threshold_list']
                score_name = grp_dict['score_name']
                model_name_list = grp_dict['model_name_list']
                threshold_tick_style = grp_dict.get('threshold_tick_style',None)

            # Read in special settings for SLR 
            if plot_type == "slr":
                model_name_list = grp_dict["model_name_list"]
               
            

            # first get the observational obs labels

            obs_vars = []
            for pair_label in pair_labels:
                obs_vars.extend(self.paired[pair_label].obs_vars)
            # Guarantee uniqueness of obs_vars, without altering order
            obs_vars = list(dict.fromkeys(obs_vars))

            # loop through obs variables
            for obsvar in obs_vars:
                # Loop also over the domain types. So can easily create several overview and zoomed in plots.
                domain_types = grp_dict.get('domain_type', [None])
                domain_names = grp_dict.get('domain_name', [None])
                domain_infos = grp_dict.get('domain_info', {})
                # Use only pair_labels containing obs_var
                pair_labels_obsvar = [p for p in pair_labels if obsvar in self.paired[p].obs_vars]
                for domain in range(len(domain_types)):
                    domain_type = domain_types[domain]
                    domain_name = domain_names[domain]
                    domain_info = domain_infos.get(domain_name, None)
                    for p_index, p_label in enumerate(pair_labels_obsvar):
                        p = self.paired[p_label]
                        obs_type = p.type

                        # find the pair model label that matches the obs var
                        index = p.obs_vars.index(obsvar)
                        modvar = p.model_vars[index]

                        # Adjust the modvar as done in pairing script, if the species name in obs and model are the same.
                        if obsvar == modvar:
                            modvar = modvar + '_new'

                        # Adjust the modvar for satellite no2 trop. column paring. M.Li
                        if obsvar == 'nitrogendioxide_tropospheric_column':
                            modvar = modvar + 'trpcol'
                            
                        # for pt_sfc data, convert to pandas dataframe, format, and trim
                        # Query selected points if applicable
                        if domain_type != 'all':
                            p_region = select_region(p.obj, domain_type, domain_name, domain_info)
                        else:
                            p_region = p.obj

                        
                        if obs_type in ["sat_swath_sfc", "sat_swath_clm", "sat_grid_sfc",
                                        "sat_grid_clm", "sat_swath_prof"]:
                             # convert index to time; setup for sat_swath_clm
                            
                            if 'time' not in p_region.dims and obs_type == 'sat_swath_clm':
                                pairdf_all = p_region.swap_dims({'x':'time'})

                            else:
                                pairdf_all = p_region
                            # Select only the analysis time window.
                            pairdf_all = pairdf_all.sel(time=slice(self.start_time,self.end_time))
                        else:
                            # convert to dataframe
                            pairdf_all = p_region.to_dataframe(dim_order=["time", "x"])
                            # Select only the analysis time window.
                            pairdf_all = pairdf_all.loc[self.start_time : self.end_time]
                            
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
                        if p.obs in self.obs and self.obs[p.obs].variable_dict is not None:
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
                        if grp_dict['data_proc'].get('set_axis', False):
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
                        # Setting statistical Significance for Boxplots and Violin plots 
                        set_stat_sig = grp_dict['data_proc'].get('set_stat_sig', False)
                    
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
                        if obs_type in ['pt_sfc','aircraft','mobile','ground','sonde']: 
                            if grp_dict['data_proc']['rem_obs_nan'] is True:
                                # I removed drop=True in reset_index in order to keep 'time' as a column.
                                pairdf = pairdf_all.reset_index().dropna(subset=[modvar, obsvar])
                            else:
                                pairdf = pairdf_all.reset_index().dropna(subset=[modvar])
                        elif obs_type in ["sat_swath_sfc", "sat_swath_clm", 
                                          "sat_grid_sfc", "sat_grid_clm", 
                                          "sat_swath_prof"]: 
                            # xarray doesn't need nan drop because its math operations seem to ignore nans
                            # MEB (10/9/24): Add statement to ensure model and obs variables have nans at the same place
                            pairdf = pairdf_all.where(pairdf_all[obsvar].notnull() & pairdf_all[modvar].notnull())

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
                                .resample('h', on='time_local')
                                .mean(numeric_only=True)
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
                        if plot_type.lower() == 'timeseries' or plot_type.lower() == 'diurnal':
                            if set_yaxis is True:
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

                            # 2024-03-01 MEB needs to only apply if pandas. fails for xarray
                            if isinstance(pairdf,pd.core.frame.DataFrame):
                                pairdf = pairdf.set_index(grp_dict['data_proc']['ts_select_time'])
                            # Specify ts_avg_window if noted in yaml file. #qzr++

                            if 'ts_avg_window' in grp_dict['data_proc'].keys():
                                a_w = grp_dict['data_proc']['ts_avg_window']
                            else:
                                a_w = None

                            #Steps needed to subset paired df if secondary y-axis (altitude_variable) limits are provided, 
                            #ELSE: make_timeseries from surfaceplots.py plots the whole df by default
                            #Edit below to accommodate 'ground' or 'mobile' where altitude_yax2 is not needed for timeseries
                            altitude_yax2 = grp_dict['data_proc'].get('altitude_yax2', {})

                            # Extract vmin_y2 and vmax_y2 from filter_dict
                            # Check if 'filter_dict' exists and 'altitude' is a key in filter_criteria
                            # Extract vmin_y2 and vmax_y2 from filter_dict
                            #Better structure for filter_dict (min and max secondary axis) to be optional below
                            filter_criteria = (
                                altitude_yax2.get('filter_dict', None)
                                if isinstance(altitude_yax2, dict)
                                else None
                            )
                            
                            
                            if filter_criteria and 'altitude' in filter_criteria:
                                vmin_y2, vmax_y2 = filter_criteria['altitude']['value']
                            elif filter_criteria is None:

                                if 'altitude' in pairdf:
                                    vmin_y2 = pairdf['altitude'].min()
                                    vmax_y2 = pairdf['altitude'].max()
                                else:
                                    vmin_y2 = vmax_y2 = None
                            else:
                                vmin_y2 = vmax_y2 = None
                            

                                
                            # Check if filter_criteria exists and is not None (Subset the data based on filter criteria if provided)
                            if filter_criteria:
                                for column, condition in filter_criteria.items():
                                    operation = condition['oper']
                                    value = condition['value']
                                    
                                    if operation == "between" and isinstance(value, list) and len(value) == 2:
                                        pairdf = pairdf[pairdf[column].between(vmin_y2, vmax_y2)]
                            
                            # Now proceed with plotting, call the make_timeseries function with the subsetted pairdf (if vmin2 and vmax2 are not nOne) otherwise whole df                                 
                            if self.obs[p.obs].sat_type is not None and self.obs[p.obs].sat_type.startswith("tempo_l2"):
                                if plot_type.lower() == 'timeseries':
                                    make_timeseries = xrplots.make_timeseries
                                else:
                                    make_timeseries = xrplots.make_diurnal_cycle
                                plot_kwargs = {'dset': pairdf, 'varname': obsvar}
                            else:
                                if plot_type.lower() == "timeseries":
                                    make_timeseries = splots.make_timeseries
                                else:
                                    make_timeseries = splots.make_diurnal_cycle
                                plot_kwargs = {
                                    'df': pairdf, 'df_reg': pairdf_reg, 'column': obsvar
                                }
                            settings = grp_dict.get('settings', {})
                            plot_kwargs = {
                                **plot_kwargs,
                                **{
                                    'label':p.obs,
                                    'avg_window': a_w,
                                    'ylabel': use_ylabel,
                                    'vmin':vmin,
                                    'vmax':vmax,
                                    'domain_type': domain_type,
                                    'domain_name': domain_name,
                                    'plot_dict': obs_dict,
                                    'fig_dict': fig_dict,
                                    'text_dict': text_dict,
                                    'debug': self.debug,
                                },
                                **settings
                            }
                            if p_index == 0:
                                # First plot the observations.
                                ax = make_timeseries(**plot_kwargs)
                            # For all p_index plot the model.
                            if self.obs[p.obs].sat_type is not None and self.obs[p.obs].sat_type.startswith("tempo_l2"):
                                plot_kwargs['varname']=modvar
                            else:
                                plot_kwargs['column']=modvar
                            plot_kwargs['label'] = p.model
                            plot_kwargs['plot_dict'] = plot_dict
                            plot_kwargs['ax'] = ax
                            ax = make_timeseries(**plot_kwargs)

                            # Extract text_kwargs from the appropriate plot group
                            text_kwargs = grp_dict.get('text_kwargs', {'fontsize': 20})  # Default to fontsize 20 if not defined                            

                            # At the end save the plot.
                            if p_index == len(pair_labels) - 1:
                                # Adding Altitude variable as secondary y-axis to timeseries (for, model vs aircraft) qzr++
                                if 'altitude_yax2' in grp_dict['data_proc'] and 'altitude_variable' in grp_dict['data_proc']['altitude_yax2']:
                                    altitude_yax2 = grp_dict['data_proc']['altitude_yax2']
                                    ax = airplots.add_yax2_altitude(ax, pairdf, altitude_yax2, text_kwargs, vmin_y2, vmax_y2)
                                savefig(outname + '.png', logo_height=150)

                                del (ax, fig_dict, plot_dict, text_dict, obs_dict, obs_plot_dict)  # Clear axis for next plot.
                                


                            # At the end save the plot.
                            ##if p_index == len(pair_labels) - 1:
                                #Adding Altitude variable as secondary y-axis to timeseries (for, model vs aircraft) qzr++
                                
                                #Older approach without 'altitude_yax2' control list in YAML now commented out
                                ##if grp_dict['data_proc'].get('altitude_variable'):
                                  ##  altitude_variable = grp_dict['data_proc']['altitude_variable']
                                  ##  altitude_ticks = grp_dict['data_proc'].get('altitude_ticks', 1000)  # Get altitude tick interval from YAML or default to 1000
                                  ##  ax = airplots.add_yax2_altitude(ax, pairdf, altitude_variable, altitude_ticks, text_kwargs)
                                ##savefig(outname + '.png', logo_height=150)
                                ##del (ax, fig_dict, plot_dict, text_dict, obs_dict, obs_plot_dict) #Clear axis for next plot.

                        elif plot_type.lower() == 'curtain':
                            # Set cmin and cmax from obs_plot_dict for colorbar limits
                            if set_yaxis:
                                if all(k in obs_plot_dict for k in ('vmin_plot', 'vmax_plot')):
                                    cmin = obs_plot_dict['vmin_plot']
                                    cmax = obs_plot_dict['vmax_plot']
                                else:
                                    print('Warning: vmin_plot and vmax_plot not specified for ' + obsvar + ', so default used.')
                                    cmin = None
                                    cmax = None
                            else:
                                cmin = None
                                cmax = None
                            
                            # Set vmin and vmax from grp_dict for altitude limits
                            if set_yaxis:
                                vmin = grp_dict.get('vmin', None)
                                vmax = grp_dict.get('vmax', None)
                            else:
                                vmin = None
                                vmax = None

                                
                            curtain_config = grp_dict # Curtain plot grp YAML dict
                            # Inside your loop for processing each pair
                            obs_label = p.obs
                            model_label = p.model
                        
                            
                            #Ensure we use the correct observation and model objects from pairing
                            obs = self.obs[p.obs]
                            mod = self.models[p.model]
                            model_obj = mod.obj
                        
                            # Fetch the observation configuration for colorbar labels
                            obs_label_config = self.control_dict['obs'][obs_label]['variables']
                        
                            # Fetch the model and observation data from pairdf
                            pairdf = pairdf_all.reset_index()
                        
                            #### For model_data_2d for curtain/contourfill plot #####                       
                            # Convert to get something useful for MONET
                            new_ds_obs = obs.obj.rename_axis('time_obs').reset_index().monet._df_to_da().set_coords(['time_obs', 'pressure_obs'])
                        
                            # Nearest neighbor approach to find closest grid cell to each point
                            ds_model = m.util.combinetool.combine_da_to_da(model_obj, new_ds_obs, merge=False)
                        
                            # Interpolate based on time in the observations
                            ds_model = ds_model.interp(time=ds_model.time_obs.squeeze())                 
                        
                            # Print ds_model and pressure_model values #Debugging
                            ##print(f"ds_model: {ds_model}")
                            ##print(f"pressure_model values: {ds_model['pressure_model'].values}")
                        
                            # Define target pressures for interpolation based on the range of pressure_model
                            min_pressure = ds_model['pressure_model'].min().compute()
                            max_pressure = ds_model['pressure_model'].max().compute()
                            
                            # Fetch the interval and num_levels from curtain_config
                            interval = curtain_config.get('interval', 10000)  # Default to 10,000 Pa if not provided      # Y-axis tick interval
                            num_levels = curtain_config.get('num_levels', 100)   # Default to 100 levels if not provided
                        
                            print(f"Pressure MIN:{min_pressure}, max: {max_pressure}, ytick_interval: {interval}, interpolation_levels: {num_levels}  ")
                            
                            # Use num_levels to define target_pressures interpolation levels 
                            target_pressures = np.linspace(max_pressure, min_pressure, num_levels)
                            
                            # Debugging: print target pressures
                            ##print(f"Generated target pressures: {target_pressures}, shape: {target_pressures.shape}")
                        
                            # Check for NaN values before interpolation
                            ##print(f"NaNs in model data before interpolation: {np.isnan(ds_model[modvar]).sum().compute()}")
                            ##print(f"NaNs in pressure_model before interpolation: {np.isnan(ds_model['pressure_model']).sum().compute()}")

                        
                            # Resample model data to target pressures using stratify
                            da_wrf_const = resample_stratify(ds_model[modvar], target_pressures, ds_model['pressure_model'], axis=1, interpolation='linear', extrapolation='nan')
                            da_wrf_const.name = modvar
                        
                            # Create target_pressures DataArray
                            da_target_pressures = xr.DataArray(target_pressures, dims=('z'))
                            da_target_pressures.name = 'target_pressures'
                        
                            # Merge DataArrays into a single Dataset
                            ds_wrf_const = xr.merge([da_wrf_const, da_target_pressures])
                            ds_wrf_const = ds_wrf_const.set_coords('target_pressures')
                        
                            # Debugging: print merged dataset for model curtain
                            ##print(ds_wrf_const)
                        
                            # Ensure model_data_2d is properly reshaped for the contourfill plot
                            model_data_2d = ds_wrf_const[modvar].squeeze()
                        
                            # Debugging: print reshaped model data shape
                            ##print(f"Reshaped model data shape: {model_data_2d.shape}")
                            
                            #### model_data_2d for curtain plot ready ####


                            # Fetch model pressure and other model and observation data from "pairdf" (for scatter plot overlay)
                            time = pairdf['time']
                            obs_pressure = pairdf['pressure_obs']  
                            ##print(f"Length of time: {len(time)}") #Debugging
                            ##print(f"Length of obs_pressure: {len(obs_pressure)}") #Debugging
                        
                            # Generate the curtain plot using airplots.make_curtain_plot
                            try:
                                outname_pair = f"{outname}_{obs_label}_vs_{model_label}.png"

                                print(f"Saving curtain plot to {outname_pair}...")
                        
                                ax = airplots.make_curtain_plot(
                                    time=pd.to_datetime(time),
                                    altitude=target_pressures,  # Use target_pressures for interpolation
                                    model_data_2d=model_data_2d,  # Already reshaped to match the expected shape
                                    obs_pressure=obs_pressure,  # Pressure_obs for obs scatter plot
                                    pairdf=pairdf,  #use pairdf for scatter overlay (model and obs)
                                    mod_var=modvar,
                                    obs_var=obsvar,
                                    grp_dict=curtain_config,
                                    vmin=vmin,
                                    vmax=vmax,
                                    cmin=cmin,
                                    cmax=cmax,
                                    plot_dict=plot_dict,
                                    outname=outname_pair,
                                    domain_type=domain_type,
                                    domain_name=domain_name,
                                    obs_label_config=obs_label_config,
                                    text_dict=text_dict,
                                    debug=self.debug  # Pass debug flag
                                )
                            
                                
                            except Exception as e:
                                print(f"Error generating curtain plot for {modvar} vs {obsvar}: {e}")
                            finally:
                                plt.close('all')  # Clean up matplotlib resources


                            
                                
                        #qzr++ Added vertprofile plotype for aircraft vs model comparisons         
                        elif plot_type.lower() == 'vertprofile':
                            if set_yaxis is True:
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
                            # Select altitude variable from the .yaml file
                            altitude_variable = grp_dict['altitude_variable']
                            # Define the bins for binning the altitude
                            bins = grp_dict['vertprofile_bins']
                            if p_index == 0:
                                # First plot the observations.
                                ax = airplots.make_vertprofile(
                                    pairdf,
                                    column=obsvar,
                                    label=p.obs,
                                    bins=bins,
                                    altitude_variable=altitude_variable,
                                    ylabel=use_ylabel,
                                    vmin=vmin,
                                    vmax=vmax,
                                    domain_type=domain_type,
                                    domain_name=domain_name,
                                    plot_dict=obs_dict,
                                    fig_dict=fig_dict,
                                    text_dict=text_dict,
                                    debug=self.debug,
                                    interquartile_style=interquartile_style 
                            )
                            
                            # For all p_index plot the model.
                            ax = airplots.make_vertprofile(
                                pairdf,
                                column=modvar,
                                label=p.model,
                                ax=ax,
                                bins=bins,
                                altitude_variable=altitude_variable,
                                ylabel=use_ylabel,
                                vmin=vmin,
                                vmax=vmax,
                                domain_type=domain_type,
                                domain_name=domain_name,
                                plot_dict=plot_dict,
                                text_dict=text_dict,
                                debug=self.debug,
                                interquartile_style=interquartile_style 
                            )
                            
                            
                            # At the end save the plot.
                            if p_index == len(pair_labels) - 1:
                                savefig(outname + '.png', logo_height=250)
                                del (ax, fig_dict, plot_dict, text_dict, obs_dict, obs_plot_dict) # Clear axis for next plot.

                        elif plot_type.lower() == 'vertical_single_date':
                            #to use vmin, vmax from obs in yaml
                            if set_yaxis is True:
                                if all(k in obs_plot_dict for k in ('vmin_plot','vmax_plot')):
                                    vmin = obs_plot_dict['vmin_plot']
                                    vmax = obs_plot_dict['vmax_plot']
                                else:
                                    print('warning: vmin_plot and vmax_plot not specified for '+obsvar+',so default used.')
                                    vmin = None
                                    vmax = None
                            else:
                                vmin = None
                                vmax = None
                            #begin plotting
                            if p_index ==0:
                                comb_bx, label_bx = splots.calculate_boxplot(pairdf, pairdf_reg, column=obsvar, label=p.obs, plot_dict=obs_dict)
                            comb_bx, label_bx = splots.calculate_boxplot(pairdf, pairdf_reg, column=modvar, label=p.model, plot_dict=plot_dict, comb_bx = comb_bx, label_bx = label_bx)
                            if p_index == len(pair_labels) - 1:
                                sondeplots.make_vertical_single_date(pairdf,
                                                                      comb_bx,
                                                                      altitude_range=altitude_range,
                                                                      altitude_method=altitude_method,
                                                                      vmin=vmin,
                                                                      vmax=vmax,
                                                                      station_name=station_name,
                                                                      release_time=release_time,
                                                                      label_bx=label_bx,
                                                                      fig_dict=fig_dict,
                                                                      text_dict=text_dict
                                                                      )
                                #save plot
                                plt.tight_layout()
                                savefig(outname+".png", loc=monet_logo_position[0], logo_height=100, dpi=300)

                                del (comb_bx,label_bx,fig_dict, plot_dict, text_dict, obs_dict,obs_plot_dict)

                        elif plot_type.lower() == 'vertical_boxplot_os':
                            #to use vmin, vmax from obs in yaml
                            if set_yaxis is True:
                                if all(k in obs_plot_dict for k in ('vmin_plot','vmax_plot')):
                                    vmin = obs_plot_dict['vmin_plot']
                                    vmax = obs_plot_dict['vmax_plot']
                                else:
                                    print('warning: vmin_plot and vmax_plot not specified for '+obsvar+',so default used.')
                                    vmin=None
                                    vmax=None
                            else:
                                vmin=None
                                vmax=None
                            #begin plotting
                            if p_index ==0:
                                comb_bx, label_bx = splots.calculate_boxplot(pairdf, pairdf_reg, column=obsvar, label=p.obs, plot_dict=obs_dict)
                            comb_bx, label_bx = splots.calculate_boxplot(pairdf, pairdf_reg, column=modvar, label=p.model, plot_dict=plot_dict, comb_bx = comb_bx, label_bx = label_bx)

                            if p_index == len(pair_labels) - 1:
                                sondeplots.make_vertical_boxplot_os(pairdf,
                                                                     comb_bx,
                                                                     label_bx=label_bx,
                                                                     altitude_range=altitude_range,
                                                                     altitude_method=altitude_method,
                                                                     vmin=vmin,
                                                                     vmax=vmax,
                                                                     altitude_threshold_list=altitude_threshold_list,
                                                                     station_name=station_name,
                                                                     release_time=release_time,
                                                                     fig_dict=fig_dict,
                                                                     text_dict=text_dict)
                                #save plot
                                plt.tight_layout()
                                savefig(outname+".png", loc=monet_logo_position[0], logo_height=100, dpi=300)
                                del (comb_bx,label_bx,fig_dict, plot_dict, text_dict, obs_dict,obs_plot_dict)

                        elif plot_type.lower() == 'density_scatter_plot_os':
                            #to use vmin, vmax from obs in yaml
                            if set_yaxis is True:
                                if all(k in obs_plot_dict for k in ('vmin_plot','vmax_plot')):
                                    vmin = obs_plot_dict['vmin_plot']
                                    vmax = obs_plot_dict['vmax_plot']
                                else:
                                    print('warning: vmin_plot and vmax_plot not specified for '+obsvar+',so default used.')
                                    vmin=None
                                    vmax=None
                            else:
                                vmin=None
                                vmax=None

                            #begin plotting
                            plt.figure()
                            sondeplots.density_scatter_plot_os(pairdf,altitude_range,vmin,vmax,station_name,altitude_method,cmap_method,modvar,obsvar)
                            plt.title('Scatter plot for '+model_name_list[0]+' vs. '+model_name_list[p_index+1]+'\nat '+str(station_name[0])+' on '+str(release_time)+' UTC',fontsize=15)
                            plt.tight_layout()
                            savefig(outname+"."+p_label+"."+"-".join(altitude_method[0].split())+".png", loc=monet_logo_position[0], logo_height=100, dpi=300)
                            del (pairdf)
                            
                        elif plot_type.lower() == 'violin':
                            if set_yaxis:
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
                            
                            # Initialize the combined DataFrame for violin plots and labels/colors list
                            if p_index == 0:
                                comb_violin = pd.DataFrame()
                                label_violin = []

                                                       
                            # Define a default color for observations
                            default_obs_color = 'gray'  # Default color for observations
                            
                            # Inside your loop for processing each pair
                            obs_label = p.obs
                            model_label = p.model
                            
                            # Retrieve plot_kwargs for observation
                            if hasattr(self.obs[p.obs], 'plot_kwargs') and self.obs[p.obs].plot_kwargs is not None:
                                obs_dict = self.obs[p.obs].plot_kwargs
                            else:
                                obs_dict = {'color': default_obs_color}
                            
                            # Retrieve plot_kwargs for the model
                            model_dict = self.models[p.model].plot_kwargs if self.models[p.model].plot_kwargs is not None else {'color': 'blue'} # Fallback color for models, in case it's missing
                            
                            # Call calculate_violin for observation data
                            if p_index ==0:
                                comb_violin, label_violin = airplots.calculate_violin(
                                    df=pairdf,
                                    column=obsvar,
                                    label=obs_label,
                                    plot_dict=obs_dict,
                                    comb_violin=comb_violin,
                                    label_violin=label_violin
                                )
                            
                            # Call calculate_violin for model data
                            comb_violin, label_violin = airplots.calculate_violin(
                                df=pairdf,
                                column=modvar,
                                label=model_label,
                                plot_dict=model_dict,
                                comb_violin=comb_violin,
                                label_violin=label_violin
                            )

                            
                            # For the last pair, create the violin plot
                            if p_index == len(pair_labels) - 1:
                                airplots.make_violin_plot(
                                    comb_violin=comb_violin,
                                    label_violin=label_violin,
                                    ylabel=use_ylabel,
                                    vmin=vmin,
                                    vmax=vmax,
                                    outname=outname,
                                    domain_type=domain_type,
                                    domain_name=domain_name,
                                    fig_dict=fig_dict,
                                    text_dict=text_dict,
                                    debug=self.debug
                                )
                            
                            # Clear the variables for the next plot if needed
                            if p_index == len(pair_labels) - 1:
                                del (comb_violin, label_violin, fig_dict, plot_dict, text_dict, obs_dict, obs_plot_dict)

                        

                        elif plot_type.lower() == 'scatter_density':
                            scatter_density_config = grp_dict

                            
                            # Extract relevant parameters from the configuration
                            color_map = scatter_density_config.get('color_map', 'viridis')
                            fill = scatter_density_config.get('fill', False)
                            print(f"Value of fill after reading from scatter_density_config: {fill}") #Debugging

                            
                            vmin_x = scatter_density_config.get('vmin_x', None)
                            vmax_x = scatter_density_config.get('vmax_x', None)
                            vmin_y = scatter_density_config.get('vmin_y', None)
                            vmax_y = scatter_density_config.get('vmax_y', None)
                                                    
                            # Accessing the correct model and observation configuration/labels/variables
                            model_label = p.model
                            obs_label = p.obs
                            
                            try:
                                _ = self.control_dict['model'][model_label]['mapping'][obs_label]
                            except KeyError:
                                print(f"Error: Mapping not found for model label '{model_label}' with observation label '{obs_label}' in scatter_density plot")
                                continue  # Skip this iteration if mapping is not found
                            
                            obs_config = self.control_dict['obs'][obs_label]['variables'] # Accessing the correct observation configuration

                            
                            # Extract ylabel_plot for units extraction
                            ylabel_plot = obs_config.get(obsvar, {}).get('ylabel_plot', f"{obsvar} (units)")
                            title = ylabel_plot
                            units = ylabel_plot[ylabel_plot.find("(")+1 : ylabel_plot.find(")")]
                            xlabel = f"Model {modvar} ({units})"
                            ylabel = f"Observation {obsvar} ({units})"

                            

                            
                            # Exclude keys from kwargs that are being passed explicitly
                            excluded_keys = ['color_map', 'fill', 'vmin_x', 'vmax_x', 'vmin_y', 'vmax_y', 'xlabel', 'ylabel', 'title', 'data']
                            kwargs = {key: value for key, value in scatter_density_config.items() if key not in excluded_keys}
                            if 'shade_lowest' in kwargs:
                                kwargs['thresh'] = 0
                                del kwargs['shade_lowest']


                            outname_pair = f"{outname}_{obs_label}_vs_{model_label}.png"

                            print(f"Saving scatter density plot to {outname_pair}...")
                            
                            # Create the scatter density plot
                            print(f"Processing scatter density plot for model '{model_label}' and observation '{obs_label}'...")
                            ax = airplots.make_scatter_density_plot(
                                pairdf,
                                mod_var=modvar,
                                obs_var=obsvar,
                                color_map=color_map,
                                xlabel=xlabel,
                                ylabel=ylabel,
                                title=title,
                                fill=fill,
                                vmin_x=vmin_x,
                                vmax_x=vmax_x,
                                vmin_y=vmin_y,
                                vmax_y=vmax_y,
                                outname=outname_pair,
                                **kwargs                            
                            )

                            
                            plt.close()  # Close the current figure
                            
                        elif plot_type.lower() == 'boxplot':
                            # squeeze the xarray for boxplot, M.Li
                            if obs_type in ["sat_swath_sfc", "sat_swath_clm",
                                            "sat_grid_sfc", "sat_grid_clm",
                                            "sat_swath_prof"]:
                                pairdf_sel = pairdf.squeeze()
                            else: 
                                pairdf_sel = pairdf

                            if set_yaxis is True:
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
                                comb_bx, label_bx = splots.calculate_boxplot(pairdf_sel, pairdf_reg, column=obsvar,   
                                                                                       label=p.obs, plot_dict=obs_dict)
                            # Then add the models to this dataarray.
                            comb_bx, label_bx = splots.calculate_boxplot(pairdf_sel, pairdf_reg, column=modvar, label=p.model,  
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
                                    debug=self.debug,
                                    set_stat_sig=False
                                )
                                #Clear info for next plot.
                                del (comb_bx, label_bx, fig_dict, plot_dict, text_dict, obs_dict, obs_plot_dict)   
                        
                        elif plot_type.lower() == 'multi_boxplot':
                            if set_yaxis is True:
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
                                comb_bx, label_bx,region_bx = splots.calculate_multi_boxplot(pairdf, pairdf_reg,region_name=region_name, column=obsvar, 
                                                                             label=p.obs, plot_dict=obs_dict)
                                
                            # Then add the models to this dataarray.
                            comb_bx, label_bx,region_bx = splots.calculate_multi_boxplot(pairdf, pairdf_reg, region_name= region_name,column=modvar, label=p.model, 
                                                                         plot_dict=plot_dict, comb_bx=comb_bx,
                                                                         label_bx=label_bx)
                            
                            # For the last p_index make the plot.
                            if p_index == len(pair_labels) - 1:                             
                                splots.make_multi_boxplot(
                                    comb_bx,
                                    label_bx,
                                    region_bx,  
                                    region_list = region_list,
                                    model_name_list=model_name_list,
                                    ylabel=use_ylabel,
                                    vmin=vmin,
                                    vmax=vmax,
                                    outname=outname,
                                    domain_type=domain_type,
                                    domain_name=domain_name,
                                    plot_dict=obs_dict,
                                    fig_dict=fig_dict,
                                    text_dict=text_dict,
                                    debug=self.debug)
                                #Clear info for next plot.
                                del (comb_bx, label_bx,region_bx, fig_dict, plot_dict, text_dict, obs_dict, obs_plot_dict)
                                
                        elif plot_type.lower() == 'scorecard':
                            # First for p_index = 0 create the obs box plot data array.
                            if p_index == 0:
                                comb_bx, label_bx,region_bx,msa_bx,time_bx = splots.scorecard_step1_combine_df(pairdf, pairdf_reg,region_name=region_name,urban_rural_name=urban_rural_name,
                                                                                                       column=obsvar, label=p.obs, plot_dict=obs_dict)
                            # Then add the model to this dataarray.
                            comb_bx, label_bx,region_bx, msa_bx,time_bx = splots.scorecard_step1_combine_df(pairdf, pairdf_reg, region_name= region_name,urban_rural_name=urban_rural_name, 
                                                                                                   column=modvar, label=p.model, plot_dict=plot_dict, comb_bx=comb_bx, label_bx=label_bx)
                            # For the last p_index make the plot.
                            if p_index == len(pair_labels) - 1:
                                output_obs, output_model1, output_model2 = splots.scorecard_step2_prepare_individual_df(comb_bx,region_bx,msa_bx,time_bx,model_name_list=model_name_list)
      
                                #split by region, data, and urban/rural
                                datelist = splots.GetDateList(self.start_time,self.end_time)
                                OBS_Region_Date_Urban_list, OBS_Region_Date_Rural_list = splots.scorecard_step4_GetRegionLUCDate(ds_name=output_obs,region_list=region_list,datelist=datelist,urban_rural_differentiate_value=urban_rural_differentiate_value)
                                MODEL1_Region_Date_Urban_list, MODEL1_Region_Date_Rural_list= splots.scorecard_step4_GetRegionLUCDate(ds_name=output_model1,region_list=region_list,datelist=datelist,urban_rural_differentiate_value=urban_rural_differentiate_value)
                                MODEL2_Region_Date_Urban_list, MODEL2_Region_Date_Rural_list= splots.scorecard_step4_GetRegionLUCDate(ds_name=output_model2,region_list=region_list,datelist=datelist,urban_rural_differentiate_value=urban_rural_differentiate_value)
                                
                                #Kick Nan values
                                OBS_Region_Date_Urban_list_noNan,MODEL1_Region_Date_Urban_list_noNan,MODEL2_Region_Date_Urban_list_noNan = splots.scorecard_step5_KickNan(obs_input=OBS_Region_Date_Urban_list,
                                                                                                                                                                          model_input_1=MODEL1_Region_Date_Urban_list,
                                                                                                                                                                          model_input_2=MODEL2_Region_Date_Urban_list)
                                OBS_Region_Date_Rural_list_noNan,MODEL1_Region_Date_Rural_list_noNan,MODEL2_Region_Date_Rural_list_noNan = splots.scorecard_step5_KickNan(obs_input=OBS_Region_Date_Rural_list,
                                                                                                                                                                          model_input_1=MODEL1_Region_Date_Rural_list,
                                                                                                                                                                          model_input_2=MODEL2_Region_Date_Rural_list)
                                #Get final output Matrix
                                Output_matrix = splots.scorecard_step8_OutputMatrix(obs_urban_input    = OBS_Region_Date_Urban_list_noNan, 
                                                                                    model1_urban_input = MODEL1_Region_Date_Urban_list_noNan,
                                                                                    model2_urban_input = MODEL2_Region_Date_Urban_list_noNan,
                                                                                    obs_rural_input    = OBS_Region_Date_Rural_list_noNan, 
                                                                                    model1_rural_input = MODEL1_Region_Date_Rural_list_noNan,
                                                                                    model2_rural_input = MODEL2_Region_Date_Rural_list_noNan,
                                                                                    better_or_worse_method = better_or_worse_method)
                                #plot the scorecard
                                splots.scorecard_step9_makeplot(output_matrix=Output_matrix,
                                                         column=obsvar,
                                                         region_list=region_list,
                                                         model_name_list=model_name_list,
                                                         outname=outname,
                                                         domain_type=domain_type,
                                                         domain_name=domain_name,
                                                         fig_dict=fig_dict,
                                                         text_dict=text_dict,
                                                         datelist=datelist,
                                                         better_or_worse_method = better_or_worse_method)
                                #Clear info for next plot.
                                del (comb_bx, label_bx, region_bx, msa_bx, time_bx, fig_dict, plot_dict, text_dict, obs_dict, obs_plot_dict)

                        elif plot_type.lower() == 'csi':
                            # First for p_index = 0 create the obs box plot data array.
                            if p_index == 0:
                               
                                comb_bx, label_bx = splots.calculate_boxplot(pairdf, pairdf_reg, column=obsvar,label=p.obs, plot_dict=obs_dict)
                                print(p_index,np.shape(comb_bx))
                            # Then add the models to this dataarray.
                            comb_bx, label_bx = splots.calculate_boxplot(pairdf, pairdf_reg, column=modvar, label=p.model,plot_dict=plot_dict, comb_bx=comb_bx, label_bx=label_bx)
                            print(p_index,np.shape(comb_bx))
                            if p_index == len(pair_labels) - 1:
                                print('final',p_index, len(pair_labels) - 1)
                                splots.Plot_CSI(column=obsvar,
                                                score_name_input=score_name,
                                                threshold_list_input=threshold_list, 
                                                comb_bx_input=comb_bx,
                                                plot_dict=plot_dict,
                                                fig_dict=fig_dict,
                                                text_dict=text_dict,
                                                domain_type=domain_type,
                                                domain_name=domain_name,
                                                model_name_list=model_name_list,
                                                threshold_tick_style=threshold_tick_style)
                                #save figure
                                plt.tight_layout()
                                savefig(outname +'.'+score_name+'.png', loc=1, logo_height=100) 

                                #Clear info for next plot.
                                del (comb_bx, label_bx, fig_dict, plot_dict, text_dict, obs_dict, obs_plot_dict)


                        elif plot_type.lower() == 'taylor':
                            if self.obs[p.obs].sat_type is not None and self.obs[p.obs].sat_type.startswith("tempo_l2"):
                                make_taylor = xrplots.make_taylor
                                plot_kwargs = {
                                    'dset': pairdf,
                                    'varname_o': obsvar,
                                    'varname_m': modvar,
                                    'normalize': True,
                                }
                            else:
                                make_taylor = splots.make_taylor
                                plot_kwargs = {
                                    'df': pairdf,
                                    'column_o': obsvar,
                                    'column_m': modvar,
                                }
                            plot_kwargs = {
                                **plot_kwargs,
                                **{
                                    'label_o': p.obs,
                                    'label_m': p.model,
                                    'ylabel': use_ylabel,
                                    'domain_type': domain_type,
                                    'domain_name': domain_name,
                                    'plot_dict': plot_dict,
                                    'fig_dict': fig_dict,
                                    'text_dict': text_dict,
                                    'debug': self.debug,
                                }
                            }

                            if set_yaxis is True:
                                if 'ty_scale' in obs_plot_dict.keys():
                                    plot_kwargs["ty_scale"] = obs_plot_dict['ty_scale']
                                else:
                                    print('Warning: ty_scale not specified for ' + obsvar + ', so default used.')
                                    plot_kwargs["ty_scale"] = 1.5  # Use default
                            else:
                                plot_kwargs["ty_scale"] = 1.5  # Use default
                            try: 
                                plot_kwargs["ty_scale"] = grp_dict["data_proc"].get("ty_scale", 1.5)
                            except KeyError:
                                plot_kwargs["ty_scale"]=2
                            if p_index == 0:
                                # Plot initial obs/model
                                dia = make_taylor(**plot_kwargs)
                            else:
                                # For the rest, plot on top of dia
                                dia = make_taylor(dia=dia, **plot_kwargs)
                            # At the end save the plot.
                            if p_index == len(pair_labels) - 1:
                                savefig(outname + '.png', logo_height=70)
                                del (dia, fig_dict, plot_dict, text_dict, obs_dict, obs_plot_dict) #Clear info for next plot.
                       

                        
                        
                        elif plot_type.lower() == 'spatial_bias':
                            if set_yaxis is True:
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
                            outname = "{}.{}".format(outname, p_label)
                            if self.obs[p.obs].sat_type is not None and self.obs[p.obs].sat_type.startswith("tempo_l2"):
                                make_spatial_bias_gridded = xrplots.make_spatial_bias_gridded
                                plot_kwargs = {
                                    'dset': pairdf, 'varname_o': obsvar, 'varname_m': modvar,
                                }
                            else:
                                make_spatial_bias_gridded = splots.make_spatial_bias_gridded
                                plot_kwargs = {'df': pairdf, 'column_o': obsvar, 'column_m': modvar}

                            plot_kwargs = {
                                **plot_kwargs,
                                **{
                                    "label_o": p.obs,
                                    "label_m": p.model,
                                    "ylabel": use_ylabel,
                                    "outname": outname,
                                    "domain_type": domain_type,
                                    "domain_name": domain_name,
                                    "vdiff": grp_dict["data_proc"].get("vdiff", None),
                                    "vmax": grp_dict["data_proc"].get("vmax", None),
                                    "vmin": grp_dict["data_proc"].get("vmin", None),
                                    "nlevels": grp_dict["data_proc"].get("nlevels", None),
                                    "fig_dict": fig_dict,
                                    "text_dict": text_dict,
                                    "debug": self.debug
                                }
                            }
                            make_spatial_bias_gridded(**plot_kwargs)
                            del (fig_dict, plot_dict, text_dict, obs_dict, obs_plot_dict) #Clear info for next plot.
                        elif plot_type.lower() == 'spatial_dist':
                            outname = "{}.{}".format(outname, p.obs)
                            plot_kwargs = {
                                "dset": pairdf,
                                "varname": obsvar,
                                "outname": outname,
                                "label": p.obs,
                                "ylabel": use_ylabel,
                                "domain_type": domain_type,
                                "domain_name": domain_name,
                                "vmax": grp_dict["data_proc"].get("vmax", None),
                                "vmin": grp_dict["data_proc"].get("vmin", None),
                                "fig_dict": fig_dict,
                                "text_dict": text_dict,
                                "debug": self.debug,
                            }
                            if isinstance(plot_kwargs["vmax"], str):
                                plot_kwargs["vmax"] = float(plot_kwargs["vmax"])
                            if isinstance(plot_kwargs["vmin"], str):
                                plot_kwargs["vmin"] = float(plot_kwargs["vmin"])
                            xrplots.make_spatial_dist(**plot_kwargs)
                            plot_kwargs["varname"] = modvar
                            plot_kwargs["label"] = p.model
                            plot_kwargs["outname"] = outname.replace(p.obs, p.model)
                            xrplots.make_spatial_dist(**plot_kwargs)
                        elif plot_type.lower() == 'spatial_bias_exceedance':
                            if cal_reg:
                                if set_yaxis is True:
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
                            if set_yaxis is True:
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
                            if grp_dict.get('data_proc', {}).get('crop_model', False) and domain_name != all:
                                vmodel = select_region(vmodel, domain_type, domain_name, domain_info)

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
                            
                        elif plot_type.lower() == "slr":
                            if obs_type in ["airnow_ufschem_v1"]:
                                pairdf_sel = pairdf.squeeze()
                            else:
                                pairdf_sel = pairdf
                            if p_index == 0: 
                                obs_x, label_x = splots.make_slr_plot(pairdf_sel
                                                                     )
                                
                            splots.make_slr_plot(
                                pairdf,
                                column_o=obsvar,
                                label_o=p.obs,
                                column_m=modvar,
                                label_m=p.model,

                                fig_dict=fig_dict,
                                text_dict=text_dict,
                                debug=self.debug
                            )


                            # First for p_index = 0 create the obs box plot data array.
                            if p_index == 0:
                                comb_bx, label_bx = splots.calculate_boxplot(pairdf_sel, pairdf_reg, column=obsvar,   
                                                                                       label=p.obs, plot_dict=obs_dict)
                            # Then add the models to this dataarray.
                            comb_bx, label_bx = splots.calculate_boxplot(pairdf_sel, pairdf_reg, column=modvar, label=p.model,  
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
                                    debug=self.debug,
                                    set_stat_sig=False
                                )
                                #Clear info for next plot.
                                del (comb_bx, label_bx, fig_dict, plot_dict, text_dict, obs_dict, obs_plot_dict)   


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
        from .util.region_select import select_region

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
            domain_infos = stat_dict.get('domain_info', {})
            for domain in range(len(domain_types)):
                domain_type = domain_types[domain]
                domain_name = domain_names[domain]
                domain_info = domain_infos.get(domain_name, None)

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
                        # for satellite no2 trop. columns paired data, M.Li
                        if obsvar == 'nitrogendioxide_tropospheric_column':
                            modvar = modvar + 'trpcol' 
                        
                        # Query selected points if applicable
                        if domain_type != 'all':
                            p_region = select_region(p.obj, domain_type, domain_name, domain_info)
                        else:
                            p_region = p.obj

                        dim_order = [dim for dim in ["time", "y", "x"] if dim in p_region.dims]
                        pairdf_all = p_region.to_dataframe(dim_order=dim_order)

                        # Select only the analysis time window.
                        pairdf_all = pairdf_all.loc[self.start_time : self.end_time]

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
                                .resample('h', on='time_local')
                                .mean(numeric_only=True)
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

                if stat_dict['output_table'] is True:
                    # Output as a table graphic too.
                    # Change to use the name with full spaces.
                    df_o_d['Stat_FullName'] = stat_fullname_s
 
                    proc_stats.create_table(df_o_d.drop(columns=['Stat_ID']),
                                            outname=outname,
                                            title=title,
                                            out_table_kwargs=out_table_kwargs,
                                            debug=self.debug
                                           )
