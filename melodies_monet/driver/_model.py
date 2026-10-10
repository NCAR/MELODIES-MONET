# SPDX-License-Identifier: Apache-2.0
#
import os
import warnings
import xarray as xr
import monetio as mio

try:
    import uxarray as ux
except ImportError:  # optional dep
    ux = None


class model:
    """The model class.

    A class with information and data from model results.
    """

    def __init__(self):
        """Initialize a :class:`model` object."""
        self.model = None
        self.is_global = False
        self.is_track = False
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
        self.extra_calc = None
        self.mapping = None
        self.variable_dict = None
        self.variable_summing = None
        self.plot_kwargs = None
        self.proj = None
        self.mod_to_overpass = False

        # Build in uxarray native support ; populate for the scrip file provided in cesm-se 
        self.uxds = None
        self.uxgrid = None

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
            f"    extra_calc={self.extra_calc!r},\n"
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
        from melodies_monet import tutorial

        print(self.file_str)
        if isinstance(self.file_str, list):
            self.files = sorted(self.file_str)
        elif self.file_str.startswith("example:"):
            example_id = ":".join(s.strip() for s in self.file_str.split(":")[1:])
            self.files = [tutorial.fetch_example(example_id)]
        else:
            self.files = sort(glob(self.file_str))

        # add option to read list of files from text file
        if not isinstance(self.file_str, list):
            _, extension = os.path.splitext(self.file_str)
            if extension.lower() == '.txt':
                with open(self.file_str,'r') as f:
                    self.files = f.read().split()

        if self.file_vert_str is not None:
            self.files_vert = sort(glob(self.file_vert_str))
        if self.file_surf_str is not None:
            if self.file_surf_str.startswith("example:"):
                example_id = ":".join(s.strip() for s in self.file_surf_str.split(":")[1:])
                self.files_surf = [tutorial.fetch_example(example_id)]
            else:
                self.files_surf = sort(glob(self.file_surf_str))
        if self.file_pm25_str is not None:
            self.files_pm25 = sort(glob(self.file_pm25_str))

    def open_model_files(self, time_interval=None, control_dict=None):
        """Open the model files, store data in :class:`model` instance attributes,
        and apply mask and scaling.

        Models supported are cmaq, wrfchem, ufs (rrfs is deprecated), and gsdchem.
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
        from melodies_monet.util import time_interval_subset as tsub

        print(self.model.lower())

        self.glob_files()
        # Calculate species to input into MONET, so works for all mechanisms in wrfchem
        # I want to expand this for the other models too when add aircraft data.
        # First make a list of variables not in mapping but from variable_summing, if provided

        # extra_calc handling for the model.
        if self.extra_calc is not None:
            for v in self.extra_calc.values():
                if v is None:
                    continue
                for input_var in v.values():
                    if self.variable_dict is None:
                        self.variable_dict = {}
                    if input_var not in self.variable_dict:
                        self.variable_dict[input_var] = "None"
        
        if self.variable_summing is not None:
            vars_for_summing = []
            for var in self.variable_summing.keys():
                vars_for_summing = vars_for_summing + self.variable_summing[var]["vars"]
        list_input_var = list(self.variable_dict.keys()) if self.variable_dict is not None else []
        
        for obs_map in self.mapping:
            if self.variable_summing is not None:
                list_input_var = list_input_var + list(
                    set(self.mapping[obs_map].keys()).union(set(vars_for_summing))
                    - set(self.variable_summing.keys())
                    - set(list_input_var)
                )
            else:
                list_input_var = list_input_var + list(
                    set(self.mapping[obs_map].keys()) - set(list_input_var)
                )
        # Only certain models need this option for speeding up i/o.

        # Remove standardized variable names that user may have requested to pair on or output in MM
        # as they will be added anyway and here would cause [var_list] to fail in the below model readers.
        for vn in ["temperature_k", "pres_pa_mid", "pressure_model"]:
            if vn in list_input_var:
                list_input_var.remove(vn)

        #Remove variable names in extra sfc_varlist
        if 'sfc_varlist' in self.mod_kwargs.keys():
            for vn in self.mod_kwargs['sfc_varlist']:
                if vn in list_input_var:
                    list_input_var.remove(vn)

        # Remove variables that havent been calcd yet. 
        if self.extra_calc is not None: 
            calc_vars = set(self.extra_calc.keys())
            #print("this is calc vars", calc_vars)
            list_input_var = [v for v in list_input_var if v not in calc_vars]

        if "cmaq" in self.model.lower():
            print("**** Reading CMAQ model output...")
            self.mod_kwargs.update({"var_list": list_input_var})
            if self.files_vert is not None:
                self.mod_kwargs.update({"fname_vert": self.files_vert})
            if self.files_surf is not None:
                self.mod_kwargs.update({"fname_surf": self.files_surf})
            if len(self.files) > 1:
                self.mod_kwargs.update({"concatenate_forecasts": True})
            try:
                self.obj = mio.models._cmaq_mm.open_mfdataset(self.files, **self.mod_kwargs)
                #Note this is tried first because if connect with old MONETIO code you need to use
                #the _cmaq_mm.py reader and not the cmaq.py reader, which is old.
            except AttributeError:
                self.obj = mio.models.cmaq.open_mfdataset(self.files, **self.mod_kwargs)
        elif "wrfchem" in self.model.lower():
            print("**** Reading WRF-Chem model output...")
            #Handle the awkward renaming of species in wrf-python automatically.
            if any(item in list_input_var for item in ("uvmet10_u", "uvmet10_v")):
                    list_input_var.append("uvmet10")
            if any(item in list_input_var for item in ("uvmet_u", "uvmet_v")):
                    list_input_var.append("uvmet")
            if any(item in list_input_var for item in ("uvmet10_wdir", "uvmet10_wspd")):
                    list_input_var.append("uvmet10_wspd_wdir")
            if any(item in list_input_var for item in ("uvmet_wdir", "uvmet_wspd")):
                    list_input_var.append("uvmet_wspd_wdir")   
            for vn in ["uvmet10_u", "uvmet10_v","uvmet_u","uvmet_v",
                       "uvmet10_wdir","uvmet10_wspd","uvmet_wdir","uvmet_wspd"]:
                if vn in list_input_var:
                    list_input_var.remove(vn)
            self.mod_kwargs.update({"var_list": list_input_var})
            try:
                self.obj = mio.models.wrfchem.open_mfdataset(self.files, **self.mod_kwargs)
            except AttributeError:
                self.obj = mio.models._wrfchem_mm.open_mfdataset(self.files, **self.mod_kwargs)
        elif "chimere" in self.model.lower():
            print("**** Reading Chimere model output...")
            self.mod_kwargs.update(
                {
                    "var_list": list_input_var,
                    "surf_only": control_dict["model"][self.label].get("surf_only", False),
                }
            )
            self.obj = mio.models.chimere.open_mfdataset(self.files, **self.mod_kwargs)
        elif any([mod_type in self.model.lower() for mod_type in ("ufs", "rrfs")]):
            print("**** Reading UFS-AQM or UFS-Chem model output...")
            if "rrfs" in self.model.lower():
                warnings.warn("mod_type: 'rrfs' is deprecated. use 'ufs'.", DeprecationWarning)
            if self.files_pm25 is not None:
                self.mod_kwargs.update({"fname_pm25": self.files_pm25})
            if self.files_surf is not None:
                self.mod_kwargs.update({'fname_sfc' : self.files_surf})
            self.mod_kwargs.update({"var_list": list_input_var})
            if hasattr(mio.models, "ufs"):
                loader = mio.models.ufs.open_mfdataset
            else:
                warnings.warn(
                    "usage of _rrfs_cmaq_mm is deprecated, use models.ufs.open_mf_dataset",
                    DeprecationWarning,
                )
                loader = mio.models._rrfs_cmaq_mm.open_mfdataset
            self.obj = loader(self.files, **self.mod_kwargs)
        elif "gsdchem" in self.model.lower():
            print("**** Reading GSD-Chem model output...")
            if len(self.files) > 1:
                self.obj = mio.fv3chem.open_mfdataset(self.files, **self.mod_kwargs)
            else:
                self.obj = mio.fv3chem.open_dataset(self.files, **self.mod_kwargs)
        elif "cesm_fv" in self.model.lower():
            print("**** Reading CESM FV model output...")
            self.mod_kwargs.update({"var_list": list_input_var})
            try:
                self.obj = mio.models.cesm_fv.open_mfdataset(self.files, **self.mod_kwargs)
            except AttributeError:
                self.obj = mio.models._cesm_fv_mm.open_mfdataset(self.files, **self.mod_kwargs)
       
        # CAM-chem-SE grid or MUSICAv0
        elif "cesm_se" in self.model.lower() or "mpas" in self.model.lower():
            print("**** Reading CAM unstructured model output (cesm_se / mpas)...")
            self.mod_kwargs.update({"var_list": list_input_var})

            # Grid geometry: SCRIP (CESM-SE) or native MPAS mesh/init file.
            scrip = getattr(self, "scrip_file", None)
            mesh = getattr(self, "mesh_file", None)
            if scrip and scrip.startswith("example:"):
                from melodies_monet import tutorial
                example_id = ":".join(s.strip() for s in scrip.split(":")[1:])
                scrip = self.scrip_file = tutorial.fetch_example(example_id)
            ux_grid_path = scrip or mesh
            if ux_grid_path is None:
                raise ValueError(
                    'CAM unstructured output (cesm_se / mpas) requires '
                    '"scrip_file" (SCRIP, e.g. CESM-SE) or "mesh_file" '
                    '(MPAS mesh/init file) in the YAML config.')

            if scrip:
                self.mod_kwargs.update({"scrip_file": scrip})
            if mesh:
                self.mod_kwargs.update({"mesh_file": mesh})
            print(f"Using unstructured grid file: {ux_grid_path}")

            # monetio's unstructured CAM reader is _cam_unstructured in recent
            # versions (it also handles the MPAS mesh_file input); fall back to
            # the older cesm_se module names so released monetio still works.
            try:
                from monetio.models import _cam_unstructured
            except ImportError:
                if mesh:
                    raise ImportError(
                        'MPAS "mesh_file" input requires the monetio '
                        'unstructured CAM reader '
                        '(monetio.models._cam_unstructured), which this monetio '
                        'version does not provide. Please update monetio.'
                    )
                try:
                    self.obj = mio.models.cesm_se.open_mfdataset(
                        self.files, **self.mod_kwargs)
                except AttributeError:
                    self.obj = mio.models._cesm_se_mm.open_mfdataset(
                        self.files, **self.mod_kwargs)
            else:
                self.obj = _cam_unstructured.open_mfdataset(
                    self.files, **self.mod_kwargs)
            
            try:
                self.uxgrid = ux.open_grid(ux_grid_path)
                print("**** Opened uxarray grid:", ux_grid_path)
            except Exception as e:
                self.uxgrid = None
                warnings.warn(f"Could not open uxarray grid from {ux_grid_path!r}; "
                    f"continuing with the legacy plotting path. Reason: {e}")
            if scrip:
                self.obj.attrs['mio_scrip_file'] = scrip
            if mesh:
                self.obj.attrs['mio_mesh_file'] = mesh
                
            self.obj.attrs['mio_has_unstructured_grid'] = True

            # insert this here for the unstructured grid stuff. This renaming may be breakng somewhere else, but gets it out of the 
            # juypter notebook. 
            _rename = {}
            if "lon" in self.obj.data_vars and "longitude" not in self.obj.variables:
                _rename["lon"] = "longitude"
            if "lat" in self.obj.data_vars and "latitude" not in self.obj.variables:
                _rename["lat"] = "latitude"
            if _rename:
                self.obj = self.obj.rename(_rename)
            _promote = [c for c in ("longitude", "latitude") if c in self.obj.data_vars]
            if _promote:
                self.obj = self.obj.set_coords(_promote)

        elif "camx" in self.model.lower():
            self.mod_kwargs.update({"var_list": list_input_var})
            self.mod_kwargs.update(
                {"surf_only": control_dict["model"][self.label].get("surf_only", False)}
            )
            self.mod_kwargs.update(
                {"fname_met_3D": control_dict["model"][self.label].get("files_vert", None)}
            )
            self.mod_kwargs.update(
                {"fname_met_2D": control_dict["model"][self.label].get("files_met_surf", None)}
            )
            try:
                self.obj = mio.models._camx_mm.open_mfdataset(self.files, **self.mod_kwargs)
                #Note this is tried first because if connect with old MONETIO code you need to use
                #the _camx_mm.py reader and not the camx.py reader, which is old.
            except AttributeError:
                self.obj = mio.models.camx.open_mfdataset(self.files, **self.mod_kwargs)
                
        elif "raqms" in self.model.lower():
            self.mod_kwargs.update({"var_list": list_input_var})
            if time_interval is not None:
                # fill filelist with subset
                print("subsetting model files to interval")
                file_list = tsub.subset_model_filelist(
                    self.files, "%m_%d_%Y_%HZ", "6H", time_interval
                )
            else:
                file_list = self.files
            if len(file_list) > 1:
                self.obj = mio.models.raqms.open_mfdataset(file_list, **self.mod_kwargs)
            else:
                self.obj = mio.models.raqms.open_dataset(file_list)
            if "ptrop" in self.obj and "pres_pa_trop" not in self.obj:
                self.obj = self.obj.rename({"ptrop": "pres_pa_trop"})

        else:
            print("**** Reading Unspecified model output. Take Caution...")
            if len(self.files) > 1:
                self.obj = xr.open_mfdataset(self.files, **self.mod_kwargs)
            else:
                self.obj = xr.open_dataset(self.files[0], **self.mod_kwargs)
        
        self.mask_and_scale()
        self.rename_vars()  # rename any variables as necessary
        self.sum_variables()

        if self.extra_calc is not None:
            print("Performing extra model calculations...")
            
            if "dewpoint" in self.extra_calc:
                print("Calculating modeled Dewpoint...")
                from melodies_monet.util.metcalc import dewpoint # import functions from the util.metcalc file
                
                varmap = self.extra_calc["dewpoint"]
                self.obj=dewpoint(self.obj, varmap = varmap)

            if "rel_hum" in self.extra_calc:
                print("Calculating modeled relative humidity...")
                from melodies_monet.util.metcalc import relh

                varmap = self.extra_calc["rel_hum"]
                self.obj=relh(self.obj, varmap = varmap)

            if "windspeed" in self.extra_calc:
                print("Calculating modeled windspeed...")
                from melodies_monet.util.metcalc import wspd

                varmap = self.extra_calc["windspeed"]
                self.obj=wspd(self.obj, varmap = varmap)
                
            if "winddir" in self.extra_calc:
                print("Calculating modeled wind direction...")
                from melodies_monet.util.metcalc import wdir

                varmap = self.extra_calc["winddir"]
                self.obj=wdir(self.obj, varmap = varmap)          
                
            if "ptemp_mod" in self.extra_calc:
                print("Calculating modeled potential temperature...")
                from melodies_monet.util.metcalc import ptemp
            
                varmap = self.extra_calc["ptemp_mod"]
                self.obj = ptemp(
                    self.obj,
                    varmap=varmap,
                    output_key="ptemp_mod"
                )

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
                    if "rename" in d:
                        self.obj = self.obj.rename({v: d["rename"]})
                        self.variable_dict[d["rename"]] = self.variable_dict.pop(v)

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
                    if "unit_scale" in d:
                        scale = d["unit_scale"]
                    else:
                        scale = 1
                    if "unit_scale_method" in d:
                        if d["unit_scale_method"] == "*":
                            self.obj[v].data *= scale
                        elif d["unit_scale_method"] == "/":
                            self.obj[v].data /= scale
                        elif d["unit_scale_method"] == "+":
                            self.obj[v].data += scale
                        elif d["unit_scale_method"] == "-":
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
                        print(
                            "The variable name, {}, already exists and cannot be created with variable_summing.".format(
                                var_new
                            )
                        )
                        raise ValueError
                    var_new_info = self.variable_summing[var_new]
                    if self.variable_dict is None:
                        self.variable_dict = {}
                    self.variable_dict[var_new] = var_new_info
                    for i, var in enumerate(var_new_info["vars"]):
                        if i == 0:
                            self.obj[var_new] = self.obj[var].copy()
                        else:
                            self.obj[var_new] += self.obj[var]
        except ValueError as e:
            raise Exception("Something happened when using variable_summing:") from e
