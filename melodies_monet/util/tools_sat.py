# SPDX-License-Identifier: Apache-2.0
#
import xarray as xr
from melodies_monet.driver._observation import observation


def mask_and_scale_sat(obs):
    """Applies masking and scaling to satellite observation data.
    It opperates separately if the data is a dictionary or
    xarrray.Dataset. It acts in place

    Parameters
    ----------
    obs : driver._observation.observation
        The observation object containing satellite data.

    Returns
    -------
    None
        The function modifies the observation data in place.

    Raises
    ------
    TypeError
        If obs.obj is neither an xarray.Dataset nor a dictionary of xarray.Datasets.
    """
    if isinstance(obs.obj, xr.Dataset):
        obs.mask_and_scale()
    elif isinstance(obs.obj, dict):
        for key in obs.obj:
            obs_tmp = observation()
            obs_tmp.obj = obs.obj[key]
            obs_tmp.variable_dict = obs.variable_dict.copy()
            if isinstance(obs_tmp.obj, list):
                new_list = []
                for item in obs_tmp.obj:
                    obs_item = observation()
                    obs_item.obj = item
                    obs_item.variable_dict = obs_tmp.variable_dict.copy()
                    obs_item.mask_and_scale()
                    new_list.append(obs_item.obj)
                obs_tmp.obj = new_list
            else:
                obs_tmp.mask_and_scale()
                obs.obj[key] = obs_tmp.obj
    else:
        raise TypeError("obs.obj must be either an xarray.Dataset or a dict of xarray.Datasets.")


def sum_variables_sat(obs):
    """Sum any variables noted that should be summed to create new variables.
    This occurs after any unit scaling. It opperates separately if the data 
    is a dictionary or xarrray.Dataset. It acts in place.

    Parameters
    ----------
    obs : driver._observation.observation
        The observation object containing satellite data.

    Returns
    -------
    None
        The function modifies the observation data in place.

    Raises
    ------
    TypeError
        If obs.obj is neither an xarray.Dataset nor a dictionary of xarray.Datasets.
    """
    if obs.variable_summing is None:
        return
    if isinstance(obs.obj, xr.Dataset):
        obs.sum_variables()
    elif isinstance(obs.obj, dict):
        for key in obs.obj:
            obs_tmp = observation()
            obs_tmp.obj = obs.obj[key]
            obs_tmp.variable_dict = obs.variable_dict.copy()
            obs_tmp.variable_summing = obs.variable_summing.copy()
            if isinstance(obs_tmp.obj, list):
                new_list = []
                for item in obs_tmp.obj:
                    obs_item = observation()
                    obs_item.obj = item
                    obs_item.variable_dict = obs_tmp.variable_dict.copy()
                    obs_item.variable_summing = obs_tmp.variable_summing.copy()
                    obs_item.sum_variables()
                    new_list.append(obs_item.obj)
                obs_tmp.obj = new_list
            else:
                obs_tmp.sum_variables()
                obs.obj[key] = obs_tmp.obj
    else:
        raise TypeError("obs.obj must be either an xarray.Dataset or a dict of xarray.Datasets.")


def filter_obs_sat(obs):
    """Filter observations based on filter_dict. It opperates separately
    if the data is a dictionary or xarrray.Dataset. It acts in place.

    Parameters
    ----------
    obs : driver._observation.observation
        The observation object containing satellite data.

    Returns
    -------
    None
        The function modifies the observation data in place.

    Raises
    ------
    TypeError
        If obs.obj is neither an xarray.Dataset nor a dictionary of xarray.Datasets.
    """
    if obs.data_proc is None or 'filter_dict' not in obs.data_proc:
        return
    if isinstance(obs.obj, xr.Dataset):
        obs.filter_obs()
    elif isinstance(obs.obj, dict):
        for key in obs.obj:
            obs_tmp = observation()
            obs_tmp.obj = obs.obj[key]
            obs_tmp.variable_dict = obs.variable_dict.copy()
            obs_tmp.data_proc = obs.data_proc.copy()
            if isinstance(obs_tmp.obj, list):
                new_list = []
                for item in obs_tmp.obj:
                    obs_item = observation()
                    obs_item.obj = item
                    obs_item.variable_dict = obs_tmp.variable_dict.copy()
                    obs_item.data_proc = obs_tmp.data_proc.copy()
                    obs_item.filter_obs(drop=False)
                    new_list.append(obs_item.obj)
                obs_tmp.obj = new_list
            else:
                obs_tmp.filter_obs(drop=False)
                obs.obj[key] = obs_tmp.obj
    else:
        raise TypeError("obs.obj must be either an xarray.Dataset or a dict of xarray.Datasets.")
