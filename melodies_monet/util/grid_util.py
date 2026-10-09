# SPDX-License-Identifier: Apache-2.0
#

"""
file: grid_util.py
"""

import math
import numpy as np
import numba


def update_sparse_data_grid(time_edges, x_edges, y_edges,
                            time_obs, x_obs, y_obs, data_obs,
                            count_grid, data_grid):
    """
    Accumulate obs data on a uniform grid with dimensions (time, x, y)
    Store running counts and sums in dictionaries keyed by grid index tuples (i_time, i_x, i_y)

    Parameters
        time_edges (np.array): grid time edges
        x_edges (np.array): grid x coord edges
        y_edges (np.array): grid y coord edges
        time_obs (np.array): obs times
        x_obs (np.array): obs x coords
        y_obs (np.array): obs y coords
        data_obs (np.array): obs data values
        count_grid (dict): number of obs points in grid cell
        data_grid (dict): sum of data values in grid cell

    Returns
        None
    """
    time_del = time_edges[1] - time_edges[0]
    x_del = x_edges[1] - x_edges[0]
    y_del = y_edges[1] - y_edges[0]
    ntime, nx, ny = len(time_edges) - 1, len(x_edges) - 1, len(y_edges) - 1
    for i in range(len(data_obs)):
        if not np.isnan(data_obs[i]):
            i_time = math.floor((time_obs[i] - time_edges[0]) / time_del)
            i_x = math.floor((x_obs[i] - x_edges[0]) / x_del)
            i_y = math.floor((y_obs[i] - y_edges[0]) / y_del)
            i_time = np.clip(i_time, 0, ntime - 1)
            i_x = np.clip(i_x, 0, nx - 1)
            i_y = np.clip(i_y, 0, ny - 1)
            if (i_time, i_x, i_y) in count_grid.keys():
                count_grid[(i_time, i_x, i_y)] += 1
                data_grid[(i_time, i_x, i_y)] += data_obs[i].values
            else:
                count_grid[(i_time, i_x, i_y)] = 1
                data_grid[(i_time, i_x, i_y)] = data_obs[i].values


def normalize_sparse_data_grid(count_grid, data_grid):
    """
    Normalize accumulated data on a uniform grid

    Parameters
        count_grid (dict): number of obs points in grid cell
        data_grid (dict): sum of data values in grid cell

    Returns
        None
    """
    for index_tuple in count_grid.keys():
        data_grid[index_tuple] /= count_grid[index_tuple]


def sparse_data_to_array(time_edges, x_edges, y_edges,
                         count_grid, data_grid,
                         count_type=np.uint32, data_type=np.float32):
    """
    Convert sparse grid data to numpy arrays

    Parameters
        time_edges (np.array): grid time edges
        x_edges (np.array): grid x coord edges
        y_edges (np.array): grid y coord edges
        count_grid (dict): number of obs points in grid cell
        data_grid (dict): sum of data values in grid cell
        count_type (dtype, default=np.uint32): data type of count_grid_array
        data_type (dtype, default=np.float32): data type of data_grid_array

    Returns
        count_grid_array (np.array): number of obs points in grid cell
        data_grid_array (np.array): sum of data values in grid cell
    """
    ntime, nx, ny = len(time_edges) - 1, len(x_edges) - 1, len(y_edges) - 1
    count_grid_array = np.zeros((ntime, nx, ny), dtype=count_type)
    data_grid_array = np.full((ntime, nx, ny), np.nan, dtype=data_type)
    for index_tuple in count_grid.keys():
        count_grid_array[index_tuple[0], index_tuple[1], index_tuple[2]] = count_grid[index_tuple]
        data_grid_array[index_tuple[0], index_tuple[1], index_tuple[2]] = data_grid[index_tuple]

    return count_grid_array, data_grid_array


@numba.jit(nopython=True)
def update_data_grid(time_edges, x_edges, y_edges,
                     time_obs, x_obs, y_obs, data_obs,
                     count_grid, data_grid):
    """
    Accumulate obs data on a uniform grid with dimensions (time, x, y)
    Store running counts and sums in numpy arrays

    Parameters
        time_edges (np.array): grid time edges
        x_edges (np.array): grid x coord edges
        y_edges (np.array): grid y coord edges
        time_obs (np.array): obs times
        x_obs (np.array): obs x coords
        y_obs (np.array): obs y coords
        data_obs (np.array): obs data values
        count_grid (np.array): number of obs points in grid cell
        data_grid (np.array): sum of data values in grid cell

    Returns
        None
    """
    time_del = time_edges[1] - time_edges[0]
    x_del = x_edges[1] - x_edges[0]
    y_del = y_edges[1] - y_edges[0]
    ntime, nx, ny = data_grid.shape
    for i in range(len(data_obs)):
        if not np.isnan(data_obs[i]):
            i_time = math.floor((time_obs[i] - time_edges[0]) / time_del)
            i_x = math.floor((x_obs[i] - x_edges[0]) / x_del)
            i_y = math.floor((y_obs[i] - y_edges[0]) / y_del)
            """
            i_time = np.clip(i_time, 0, ntime - 1)
            i_x = np.clip(i_x, 0, nx - 1)
            i_y = np.clip(i_y, 0, ny - 1)
            """
            if i_time < 0:
                i_time = 0
            elif i_time >= ntime:
                i_time = ntime - 1
            if i_x < 0:
                i_x = 0
            elif i_x >= nx:
                i_x = nx - 1
            if i_y < 0:
                i_y = 0
            elif i_y >= ny:
                i_y = ny - 1
            count_grid[i_time, i_x, i_y] += 1
            data_grid[i_time, i_x, i_y] += data_obs[i]


def normalize_data_grid(count_grid, data_grid):
    """
    Normalize accumulated data on a uniform grid

    Parameters
        count_grid (np.array): number of obs points in grid cell
        data_grid (np.array): sum of data values in grid cell

    Returns
        None
    """
    mask = (count_grid > 0)
    data_grid[count_grid == 0] = np.nan
    data_grid[mask] /= count_grid[mask]


def generate_uniform_grid(start, end, ntime, nlat, nlon):
    """Generate a uniform latitude-longitude-time grid.

    Parameters
    ----------
    start : str or datetime
        Start time (ISO format string or datetime).
    end : str or datetime
        End time (ISO format string or datetime).
    ntime : int
        Number of time bins.
    nlat : int
        Number of latitude bins (range: -90 to 90).
    nlon : int
        Number of longitude bins (range: -180 to 180).

    Returns
    -------
    grid : dict
        Grid center coordinates with keys ``'longitude'``, ``'latitude'``,
        and ``'time'`` (Unix timestamps).
    edges : dict
        Grid cell boundaries with keys ``'lon_edges'``, ``'lat_edges'``,
        and ``'time_edges'``.
    """
    import pandas as pd
    start_timestamp = pd.to_datetime(start).timestamp()
    end_timestamp = pd.to_datetime(end).timestamp()

    ntime = ntime
    nlat = nlat
    nlon = nlon
    lon0 = -180

    # generate uniform grid
    time_edges = np.linspace(start_timestamp, end_timestamp, ntime+1, endpoint=True, dtype=float)
    time_grid = 0.5 * (time_edges[0:ntime] + time_edges[1:ntime+1])
    lat_edges = np.linspace(-90, 90, nlat+1, endpoint=True, dtype=float)
    lat_grid = 0.5 * (lat_edges[0:nlat] + lat_edges[1:nlat+1])
    # lat_min, lat_max = lat_edges[0:nlat], lat_edges[1:nlat+1]
    lon_edges = np.linspace(lon0, lon0 + 360, nlon+1, endpoint=True, dtype=float)
    lon_grid = 0.5 * (lon_edges[0:nlon] + lon_edges[1:nlon+1])

    grid = {'longitude':lon_grid,
            'latitude':lat_grid,
            'time':time_grid}  
    edges = {'time_edges':time_edges,'lon_edges':lon_edges,'lat_edges':lat_edges}

    return grid, edges
