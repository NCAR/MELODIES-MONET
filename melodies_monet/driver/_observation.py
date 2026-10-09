# SPDX-License-Identifier: Apache-2.0
#
import os
import xarray as xr
import numpy as np

import monetio as mio


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
        self.extra_calc = None
        self.type = "pt_src"
        self.sat_type = None
        self.sat_method = None
        self.data_proc = None
        self.variable_dict = None
        self.variable_summing = None
        self.resample = None
        self.time_var = None
        self.regrid_method = None
        self.debug = False

    def __repr__(self):
        return (
            f"{type(self).__name__}(\n"
            f"    obs={self.obs!r},\n"
            f"    label={self.label!r},\n"
            f"    file={self.file!r},\n"
            f"    obj={repr(self.obj) if self.obj is None else '...'},\n"
            f"    extra_calc={self.extra_calc!r},\n"
            f"    type={self.type!r},\n"
            f"    sat_type={self.sat_type!r},\n"
            f"    sat_method={self.sat_method!r},\n"
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

        from melodies_monet import tutorial

        if self.file.startswith("example:"):
            example_id = ":".join(s.strip() for s in self.file.split(":")[1:])
            files = [tutorial.fetch_example(example_id)]
        else:
            files = sort(glob(self.file))

        assert len(files) >= 1, "need at least one"

        # extra calc handling for obs
        if self.extra_calc is not None:
            for v in self.extra_calc.values():
                if v is None:
                    continue
                for input_var in v.values():
                    if self.variable_dict is None:
                        self.variable_dict = {}
                    if input_var not in self.variable_dict:
                        self.variable_dict[input_var] = "None"
                        
        _, extension = os.path.splitext(files[0])
        try:
            if extension in {".nc", ".ncf", ".netcdf", ".nc4"}:
                if len(files) > 1:
                    self.obj = xr.open_mfdataset(files)
                else:
                    self.obj = xr.open_dataset(files[0])
            elif extension in [".ict", ".icartt"]:
                assert len(files) == 1, "monetio.icartt.add_data can only read one file"
                self.obj = mio.icartt.add_data(files[0])
            elif extension in [".csv"]:
                from melodies_monet.util.read_util import read_aircraft_obs_csv

                assert len(files) == 1, "MELODIES-MONET can only read one csv file"
                self.obj = read_aircraft_obs_csv(filename=files[0], time_var=self.time_var)
            else:
                raise ValueError(f"extension {extension!r} currently unsupported")
        except Exception as e:
            print("something happened opening file:", e)
            return

        self.add_coordinates_ground()  # If ground site then add coordinates based on yaml if necessary
        self.mask_and_scale()  # mask and scale values from the control values
        self.rename_vars()  # rename any variables as necessary
        self.sum_variables()
        self.resample_data()
        self.filter_obs()

        if self.extra_calc is not None:
            print("Performing extra calculations for obs...")
            
            if "ptemp_obs" in self.extra_calc:
                print("Calculating observed potential temperature...")
                from melodies_monet.util.metcalc import ptemp
            
                varmap = self.extra_calc["ptemp_obs"]
                self.obj = ptemp(
                    self.obj,
                    varmap=varmap,
                    output_key="ptemp_obs"
                )

    def add_coordinates_ground(self):
        """Add latitude and longitude coordinates to data when the observation type is ground and
        ground_coordinate is specified

        Returns
        -------
        None
        """

        # If ground site
        if self.obs_type == "ground":
            if self.ground_coordinate and isinstance(self.ground_coordinate, dict):
                self.obj["latitude"] = (
                    xr.ones_like(self.obj["time"], dtype=np.float64)
                    * self.ground_coordinate["latitude"]
                )
                self.obj["longitude"] = (
                    xr.ones_like(self.obj["time"], dtype=np.float64)
                    * self.ground_coordinate["longitude"]
                )
            elif self.ground_coordinate and ~isinstance(self.ground_coordinate, dict):
                raise TypeError(
                    "The ground_coordinate option must be specified as a dict with keys latitude and longitude."
                )

    def rename_vars(self):
        """Rename any variables in observation with rename set.

        Returns
        -------
        None
        """
        data_vars = self.obj.data_vars
        # For xarray datasets using data_vars does not grab names of coordinates
        if isinstance(self.obj, xr.Dataset):
            data_vars = list(self.obj.data_vars) + list(self.obj.coords)

        if self.variable_dict is not None:
            for v in data_vars:
                if v in self.variable_dict:
                    d = self.variable_dict[v]
                    if "rename" in d:
                        self.obj = self.obj.rename({v: d["rename"]})
                        self.variable_dict[d["rename"]] = self.variable_dict.pop(v)

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
        from melodies_monet.util import time_interval_subset as tsub
        from melodies_monet.util.tools_sat import (
            mask_and_scale_sat,
            sum_variables_sat,
            filter_obs_sat,
        )
        from glob import glob

        try:
            if self.sat_type == "omps_l3":
                print("Reading OMPS L3")
                try:
                    self.obj = mio.sat.omps_l3.open_dataset(self.file)
                except AttributeError:
                    self.obj = mio.sat._omps_l3_mm.open_dataset(self.file)
            elif self.sat_type == "omps_nm":
                print("Reading OMPS_NM")
                if time_interval is not None:
                    flst = tsub.subset_OMPS_l2(self.file, time_interval)
                else:
                    flst = self.file

                try:
                    self.obj = mio.sat.omps_nadir.read_OMPS_nm(flst)
                except AttributeError:
                    self.obj = mio.sat._omps_nadir_mm.read_OMPS_nm(flst)

                # couple of changes to move to reader
                self.obj = self.obj.swap_dims({"x": "time"})  # indexing needs
                self.obj = self.obj.sortby("time")  # enforce time in order.
                # restrict observation data to time_interval if using
                # additional development to deal with files crossing intervals needed (eg situations where orbit start at 23hrs, ends next day).
                if time_interval is not None:
                    self.obj = self.obj.sel(time=slice(time_interval[0], time_interval[-1]))

            elif self.sat_type == "mopitt_l3":
                print("Reading MOPITT")
                if time_interval is not None:
                    flst = tsub.subset_mopitt_l3(self.file, time_interval)
                else:
                    flst = self.file
                try:
                    self.obj = mio.sat.mopitt_l3.open_dataset(
                        flst,
                        [
                            "column",
                            "pressure_surf",
                            "apriori_col",
                            "apriori_surf",
                            "apriori_prof",
                            "ak_col",
                        ],
                    )
                except AttributeError:
                    self.obj = mio.sat._mopitt_l3_mm.open_dataset(
                        flst,
                        [
                            "column",
                            "pressure_surf",
                            "apriori_col",
                            "apriori_surf",
                            "apriori_prof",
                            "ak_col",
                        ],
                    )

                # Determine if monthly or daily product and set as attribute
                if any(mtype in glob(self.file)[0] for mtype in ("MOP03JM", "MOP03NM", "MOP03TM")):
                    self.obj.attrs["monthly"] = True
                else:
                    self.obj.attrs["monthly"] = False

            elif self.sat_type == "modis_l2":
                # from monetio import modis_l2
                print("Reading MODIS L2")
                flst = tsub.subset_MODIS_l2(self.file, time_interval)
                # self.obj = mio.sat._modis_l2_mm.read_mfdataset(
                #     self.file, self.variable_dict, debug=self.debug)
                try:
                    self.obj = mio.sat.modis_l2.read_mfdataset(
                        flst, self.variable_dict, debug=self.debug
                    )
                except AttributeError:
                    self.obj = mio.sat._modis_l2_mm.read_mfdataset(
                        flst, self.variable_dict, debug=self.debug
                    )
                # self.obj = granules, an OrderedDict of Datasets, keyed by datetime_str,
                #   with variables: Latitude, Longitude, Scan_Start_Time, parameters, ...
            elif self.sat_type == 'tropomi_l2_no2' and (
                    self.sat_method == None or self.sat_method == "replace_apriori"):
                # from monetio import tropomi_l2_no2
                print("Reading TROPOMI L2 NO2")
                try:
                    self.obj = mio.sat.tropomi_l2_no2.read_trpdataset(
                        self.file, self.variable_dict, debug=self.debug
                    )
                except AttributeError:
                    self.obj = mio.sat._tropomi_l2_no2_mm.read_trpdataset(
                        self.file, self.variable_dict, debug=self.debug
                    )
            elif self.sat_type.startswith('tropomi_l2') and self.sat_method == "apply_ak":

                print('Reading TROPOMI L2 with averaging kernel application')
                self.obj = mio.sat.tropomi_l2.open_datasets(self.file, self.variable_dict)        

            elif "tempo_l2" in self.sat_type:
                print("Reading TEMPO L2")
                try:
                    self.obj = mio.sat.tempo_l2.open_dataset(
                        self.file, self.variable_dict, debug=self.debug
                    )
                except AttributeError:
                    self.obj = mio.sat._tempo_l2_no2_mm.open_dataset(
                        self.file, self.variable_dict, debug=self.debug
                    )
            else:
                print("file reader not implemented for {} observation".format(self.sat_type))
                raise ValueError
        except ValueError as e:
            print("something happened opening file:", e)
            return
        mask_and_scale_sat(self)  # mask and scale values from the control values
        sum_variables_sat(self)
        filter_obs_sat(self)

    def filter_obs(self):
        """Filter observations based on filter_dict.

        Returns
        -------
        None
        """
        if self.data_proc is not None:
            if "filter_dict" in self.data_proc:
                filter_dict = self.data_proc["filter_dict"]
                for column in filter_dict.keys():
                    filter_vals = filter_dict[column]["value"]
                    filter_op = filter_dict[column]["oper"]
                    if filter_op == "isin":
                        self.obj = self.obj.where(self.obj[column].isin(filter_vals), drop=True)
                    elif filter_op == "isnotin":
                        self.obj = self.obj.where(~self.obj[column].isin(filter_vals), drop=True)
                    elif filter_op == "==":
                        self.obj = self.obj.where(self.obj[column] == filter_vals, drop=True)
                    elif filter_op == ">":
                        self.obj = self.obj.where(self.obj[column] > filter_vals, drop=True)
                    elif filter_op == "<":
                        self.obj = self.obj.where(self.obj[column] < filter_vals, drop=True)
                    elif filter_op == ">=":
                        self.obj = self.obj.where(self.obj[column] >= filter_vals, drop=True)
                    elif filter_op == "<=":
                        self.obj = self.obj.where(self.obj[column] <= filter_vals, drop=True)
                    elif filter_op == "!=":
                        self.obj = self.obj.where(self.obj[column] != filter_vals, drop=True)
                    else:
                        raise ValueError(f"Filter operation {filter_op!r} is not supported")

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
                    if "obs_min" in d:
                        self.obj[v].data = self.obj[v].where(self.obj[v] >= d["obs_min"])
                    if "obs_max" in d:
                        self.obj[v].data = self.obj[v].where(self.obj[v] <= d["obs_max"])
                    if "nan_value" in d:
                        self.obj[v].data = self.obj[v].where(self.obj[v] != d["nan_value"])

                    # Then apply a correction if needed for the units.
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

                    # Then replace LLOD_value with LLOD_setvalue (after unit conversion)
                    if "LLOD_value" in d:
                        self.obj[v].data = self.obj[v].where(
                            self.obj[v] != d["LLOD_value"], d["LLOD_setvalue"]
                        )

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

    def resample_data(self):
        """Resample the obs df based on the value set in the control file.

        Returns
        -------
        None
        """

        ##Resample the data
        if self.resample is not None:
            self.obj = self.obj.resample(time=self.resample).mean(dim="time")

    def obs_to_df(self):
        """Convert and reformat observation object (:attr:`obj`) to dataframe.

        Returns
        -------
        None
        """
        try:
            self.obj = self.obj.to_dataframe().reset_index().drop(["x", "y"], axis=1)
        except KeyError:
            self.obj = self.obj.to_dataframe().reset_index().drop(["x"], axis=1)
