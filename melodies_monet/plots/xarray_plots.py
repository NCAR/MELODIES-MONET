# SPDX-License-Identifier: Apache-2.0
#

import logging

import warnings
import cartopy.crs as ccrs
import matplotlib as mpl
import matplotlib.pyplot as plt
import monet as monet
import numpy as np
import pandas as pd
import seaborn as sns
import xarray as xr
try:
    import uxarray as ux
except ImportError:  # optional dep
    ux = None
from monet.plots.taylordiagram import TaylorDiagram as td
from monet.util.tools import get_epa_region_bounds as get_epa_bounds
from monet.util.tools import get_giorgi_region_bounds as get_giorgi_bounds

from melodies_monet.plots import savefig

plt.set_loglevel(level="warning")
logging.getLogger("PIL").setLevel(logging.WARNING)

sns.set_context("paper")


def time_average(dset, varname=None, period="1D", time_offset=None):
    """Calculates 24-hour averages

    Parameters
    ----------
    dset : dataframe
        Model/obs pair of hourly data
    varname : None | str
        Column label of observation variable to apply the calculation
    period : str
        The period over which to average. Should be noted in Pandas style
        (e.g., '1D', '1h', 'ME', etc.)
    time_offset : None | timedelta
        Whether a time_offset should be applied. Can be useful if accounting
        for time offsets is desirable.

    Returns
    -------
    dataframe
        dataframe with applied calculation
    """
    daily = dset[varname].resample(time=period, offset=time_offset).mean()

    return daily


# TODO:: Add projection support to maps, as optional arguments for the user

# TODO : Add area weighting in make_timeseries and other similar functions (e.g., boxplots)


def make_timeseries(
    dset,
    varname=None,
    label=None,
    ax=None,
    avg_window="h",
    ylabel=None,
    vmin=None,
    vmax=None,
    domain_type=None,
    domain_name=None,
    plot_dict=None,
    fig_dict=None,
    text_dict=None,
    debug=False,
):
    """Creates timeseries plot.

    Parameters
    ----------
    dset : xr.Dataset
        model/obs pair data to plot
    varname : str
        Variable label of variable to plot
    label : str
        Name of variable to use in plot legend
    ax : ax
        matplotlib ax from previous occurrence so can overlay obs and model
        results on the same plot
    avg_window : rule
        Pandas resampling rule (e.g., 'h', 'D')
    ylabel : str
        Title of y-axis
    vmin : real number
        Min value to use on y-axis
    vmax : real number
        Max value to use on y-axis
    domain_type : str
        Domain type specified in input yaml file
    domain_name : str
        Domain name specified in input yaml file
    plot_dict : dictionary
        Dictionary containing information about plotting for each pair
        (e.g., color, linestyle, markerstyle)
    fig_dict : dictionary
        Dictionary containing information about figure
    text_dict : dictionary
        Dictionary containing information about text
    debug : boolean
        Whether to plot interactively (True) or not (False). Flag for
        submitting jobs to supercomputer turn off interactive mode.

    Returns
    -------
    ax
        matplotlib ax such that driver.py can iterate to overlay multiple models on the
        same plot

    """
    if plot_dict is None:
        plot_dict = {}
    if not debug:
        plt.ioff()
    # First define items for all plots
    # set default text size
    def_text = dict(fontsize=14)
    if text_dict is not None:
        text_kwargs = {**def_text, **text_dict}
    else:
        text_kwargs = def_text
    # set ylabel to column if not specified.
    if ylabel is None:
        ylabel = varname
        if "units" in dset[varname].attrs:
            ylabel = f"{ylabel} ({dset[varname].attrs['units']})"
    if label is not None:
        plot_dict["label"] = label
    if (label is None) and (label not in plot_dict.keys()):
        plot_dict["label"] = varname
    # scale the fontsize for the x and y labels by the text_kwargs
    plot_dict["fontsize"] = text_kwargs["fontsize"] * 0.8
    
    # Spatial dims to reduce over per timestep. Hardcoding ("y", "x") only
    # works for structured swath output; unstructured paired data (CESM-SE
    # back_to_modgrid) returns an "n_face" or "ncol" spatial dim 
    # Average over whatever non-time dims are present.
    spatial_dims = [d for d in dset[varname].dims if d != "time"]
    
    # Then, if no plot has been created yet, create a plot and plot the obs.
    if ax is None:
        # First define the colors for the observations.
        obs_dict = dict(color="k", linestyle="-", marker="*", linewidth=1.2, markersize=6.0)
        if plot_dict is not None:
            # Whatever is not defined in the yaml file is filled in with the obs_dict here.
            plot_kwargs = {**obs_dict, **plot_dict}
        else:
            plot_kwargs = obs_dict
        # create the figure
        if fig_dict is not None:
            f, ax = plt.subplots(**fig_dict)
        else:
            f, ax = plt.subplots(figsize=(10, 6))
        # plot the line
        print(plot_kwargs)

        if avg_window is None:
            #dset[varname].mean(dim=("y", "x"), skipna=True).plot.line
            dset[varname].mean(dim=spatial_dims, skipna=True).plot.line(
                x="time",
                ax=ax,
                color=plot_kwargs["color"],
                linestyle=plot_kwargs["linestyle"],
                marker=plot_kwargs["marker"],
                linewidth=plot_kwargs["linewidth"],
                markersize=plot_kwargs["markersize"],
                label=plot_kwargs["label"],
            )
        else:
            #dset[varname].resample(time=avg_window).mean().mean(dim=("y", "x")).plot.line
             dset[varname].resample(time=avg_window).mean().mean(dim=spatial_dims).plot.line(
                x="time",
                ax=ax,
                color=plot_kwargs["color"],
                linestyle=plot_kwargs["linestyle"],
                marker=plot_kwargs["marker"],
                linewidth=plot_kwargs["linewidth"],
                markersize=plot_kwargs["markersize"],
                label=plot_kwargs["label"],
            )

    # If plot has been created add to the current axes.
    else:
        # this means that an axis handle already exists and use it to plot the model output.
        mod_dict = dict(color=None, linestyle="-", marker="*", linewidth=1.2, markersize=6.0)
        if plot_dict is not None:
            # Whatever is not defined in the yaml file is filled in with the mod_dict here.
            plot_kwargs = {**mod_dict, **plot_dict}
        else:
            plot_kwargs = obs_dict
        if avg_window is None:
            dset[varname].mean(dim=spatial_dims).plot.line(
            #dset[varname].mean(dim=("y", "x")).plot.line(
                x="time",
                ax=ax,
                color=plot_kwargs["color"],
                linestyle=plot_kwargs["linestyle"],
                marker=plot_kwargs["marker"],
                linewidth=plot_kwargs["linewidth"],
                markersize=plot_kwargs["markersize"],
                label=plot_kwargs["label"],
            )
        else:
            #dset[varname].resample(time=avg_window).mean().mean(dim=("y", "x")).plot.line(
            dset[varname].resample(time=avg_window).mean().mean(dim=spatial_dims).plot.line(
                x="time",
                ax=ax,
                color=plot_kwargs["color"],
                linestyle=plot_kwargs["linestyle"],
                marker=plot_kwargs["marker"],
                linewidth=plot_kwargs["linewidth"],
                markersize=plot_kwargs["markersize"],
                label=plot_kwargs["label"],
            )

    # Set parameters for all plots
    ax.set_ylabel(ylabel, fontweight="bold", **text_kwargs)
    ax.set_xlabel("time", fontweight="bold", **text_kwargs)
    # ax.legend(frameon=False, fontsize=text_kwargs["fontsize"] * 0.8)
    ax.tick_params(axis="both", length=10.0, direction="inout")
    ax.tick_params(axis="both", which="minor", length=5.0, direction="out")
    ax.set_ylim(vmin, vmax)
    ax.legend(
        frameon=False,
        fontsize=text_kwargs["fontsize"] * 0.8,
        bbox_to_anchor=(1.0, 0.9),
        loc="center left",
    )
    ax.tick_params(axis="both", which="major", labelsize=text_kwargs["fontsize"] * 0.8)
    ax.yaxis.get_offset_text().set_fontsize(text_kwargs["fontsize"] * 0.8)
    ax.xaxis.get_offset_text().set_fontsize(text_kwargs["fontsize"] * 0.8)
    if domain_type is not None and domain_name is not None:
        if domain_type == "epa_region":
            ax.set_title("EPA Region " + domain_name, fontweight="bold", **text_kwargs)
        else:
            ax.set_title(domain_name, fontweight="bold", **text_kwargs)
    return ax


# TODO : Add ax.text() for negative correlations
def make_taylor(
    dset,
    varname_o=None,
    label_o="Obs",
    varname_m=None,
    label_m="Model",
    mean_criteria=None,
    dia=None,
    ylabel=None,
    ty_scale=1.5,
    domain_type=None,
    domain_name=None,
    plot_dict=None,
    fig_dict=None,
    text_dict=None,
    debug=False,
    normalize=False,
    scale_factor=1,
):
    """Creates taylor plot. Note sometimes model values are off the scale
    on this plot. This will be fixed soon.

    Parameters
    ----------
    dset : xr.Dataset
        model/obs pair data to plot
    column_o : str
        Column label of observational variable to plot
    label_o : str
        Name of observational variable to use in plot legend
    column_m : str
        Column label of model variable to plot
    label_m : str
        Name of model variable to use in plot legend
    mean_criteria : str
        'None', 'space', 'time'. If None, values and correlations are compared
        over all dimensions (x, y and time). If 'space', the spatial mean over the
        comain is calculated before doing the comparison. If 'time', the temporal
        mean is calculated before doing the comparison.
    dia : dia
        matplotlib ax from previous occurrence so can overlay obs and model
        results on the same plot
    ylabel : str
        Title of x-axis
    ty_scale : real
        Scale to apply to taylor plot to control the plotting range
    domain_type : str
        Domain type specified in input yaml file
    domain_name : str
        Domain name specified in input yaml file
    plot_dict : dictionary
        Dictionary containing information about plotting for each pair
        (e.g., color, linestyle, markerstyle)
    fig_dict : dictionary
        Dictionary containing information about figure
    text_dict : dictionary
        Dictionary containing information about text
    debug : boolean
        Whether to plot interactively (True) or not (False). Flag for
        submitting jobs to supercomputer turn off interactive mode.

    Returns
    -------
    class
        Taylor diagram class defined in MONET

    """
    # import pdb; pdb.set_trace()

    if mean_criteria == "space":
        dset_forplot = dset.mean(dim=("x", "y"))
    elif mean_criteria == "time":
        dset_forplot = dset.mean(dim="time")
    else:
        dset_forplot = dset
    # import pdb; pdb.set_trace()

    # First define items for all plots
    if not debug:
        plt.ioff()

    # set default text size
    def_text = dict(fontsize=14.0)
    if text_dict is not None:
        text_kwargs = {**def_text, **text_dict}
    else:
        text_kwargs = def_text
    # set ylabel to column if not specified.
    if ylabel is None:
        ylabel = varname_o
    # Then, if no plot has been created yet, create a plot and plot the first pair.
    refstd = dset_forplot[varname_o].std().values

    if dia is None:
        # create the figure
        if fig_dict is not None:
            f = plt.figure(**fig_dict)
        else:
            f = plt.figure(figsize=(12, 10))
        sns.set_style("ticks")
        # plot the line
        cc = xr.corr(
            dset_forplot[varname_o].stack(tempdim=[...]).dropna(dim="tempdim"),
            dset_forplot[varname_m].stack(tempdim=[...]).dropna(dim="tempdim"),
        )
        if normalize:
            print(f"Base standard deviation: {refstd: 1.3g}")
            scale_factor = refstd
            dia = td(1, scale=ty_scale, fig=f, rect=111, label=label_o)
            dia.add_sample(
                dset_forplot[varname_m].std().values / scale_factor,
                cc,
                zorder=9,
                label=label_m,
                **plot_dict,
            )
        elif scale_factor != 1:
            dset_forplot[varname_m].attrs[
                "units"
            ] = f"{scale_factor} {dset_forplot[varname_m].attrs['units']}"

        else:
            dia = td(refstd, scale=ty_scale, fig=f, rect=111, label=label_o)
            dia.add_sample(
                dset_forplot[varname_m].std().values,
                cc,
                zorder=9,
                label=label_m,
                **plot_dict,
            )
        plt.grid(linewidth=1, alpha=0.5)

    # If plot has been created add to the current axes.
    else:
        # this means that an axis handle already exists and use it to plot another model
        cc = xr.corr(
            dset_forplot[varname_o].stack(tempdim=[...]).dropna(dim="tempdim"),
            dset_forplot[varname_m].stack(tempdim=[...]).dropna(dim="tempdim"),
        )
        if normalize:
            scale_factor = refstd
            dia.add_sample(
                dset_forplot[varname_m].std().values / scale_factor,
                cc,
                zorder=9,
                label=label_m,
                **plot_dict,
            )

        else:
            dia.add_sample(
                dset_forplot[varname_m].std().values,
                cc,
                zorder=9,
                label=label_m,
                **plot_dict,
            )
    # Set parameters for all plots
    contours = dia.add_contours(colors="0.5")
    # control the clabel format for very high values (e.g., NO2 columns), M.Li
    # plt.clabel(contours, inline=1, fontsize=text_kwargs['fontsize']*0.8)
    plt.clabel(contours, inline=1, fontsize=text_kwargs["fontsize"] * 0.8, fmt="(%1.5g)")

    plt.grid(alpha=0.5)
    plt.legend(
        frameon=False,
        fontsize=text_kwargs["fontsize"] * 0.8,
        bbox_to_anchor=(0.75, 0.93),
        loc="center left",
    )
    if domain_type is not None and domain_name is not None:
        if domain_type == "epa_region":
            plt.title("EPA Region " + domain_name, fontweight="bold", **text_kwargs)
        else:
            plt.title(domain_name, fontweight="bold", **text_kwargs)

    ax = plt.gca()
    ax.axis["left"].label.set_text("Standard Deviation: " + ylabel)
    ax.axis["top"].label.set_text("Correlation")
    ax.axis["left"].label.set_fontsize(text_kwargs["fontsize"])
    ax.axis["top"].label.set_fontsize(text_kwargs["fontsize"])
    ax.axis["left"].label.set_fontweight("bold")
    ax.axis["top"].label.set_fontweight("bold")
    ax.axis["top"].major_ticklabels.set_fontsize(text_kwargs["fontsize"] * 0.8)
    ax.axis["left"].major_ticklabels.set_fontsize(text_kwargs["fontsize"] * 0.8)
    ax.axis["right"].major_ticklabels.set_fontsize(text_kwargs["fontsize"] * 0.8)
    return dia


def calculate_boxplot(
    dset,
    varname=None,
    label=None,
    plot_dict=None,
    comb_bx=None,
    label_bx=None,
):
    """Combines data into acceptable format for box-plot

    Parameters
    ----------
    dset : xr.Dataset
         model/obs pair data to plot
    varname : str
        Dataset label of variable to plot
    label : str
        Name of variable to use in plot legend
    comb_bx: dataframe
        dataframe containing information to create box-plot from previous
        occurrence so can overlay multiple model results on plot
    label_bx: list
        list of string labels to use in box-plot from previous occurrence so
        can overlay multiple model results on plot
    Returns
    -------
    dataframe, list
        dataframe containing information to create box-plot
        list of string labels to use in box-plot

    """
    if comb_bx is None and label_bx is None:
        comb_bx = pd.DataFrame()
        label_bx = []
        # First define the colors for the observations.
        obs_dict = dict(color="gray", linestyle="-", marker="x", linewidth=1.2, markersize=6.0)
        if plot_dict is not None:
            # Whatever is not defined in the yaml file is filled in with the obs_dict here.
            plot_kwargs = {**obs_dict, **plot_dict}
        else:
            plot_kwargs = obs_dict
    else:
        plot_kwargs = plot_dict
    # For all, a column to the dataframe and append the label info to the list.
    plot_kwargs["varname"] = varname
    plot_kwargs["label"] = label
    # BUG : this shouldn't be using that mean. Flatten with var.stack(tempdim=[...]) and fix
    comb_bx[label] = dset[varname].mean(dim=("x", "y")).to_dataframe()
    label_bx.append(plot_kwargs)

    return comb_bx, label_bx


def make_boxplot(
    comb_bx,
    label_bx,
    ylabel=None,
    vmin=None,
    vmax=None,
    outname="plot",
    domain_type=None,
    domain_name=None,
    plot_dict=None,
    fig_dict=None,
    text_dict=None,
    debug=False,
):
    """Creates box-plot.

    Parameters
    ----------
    comb_bx: dataframe
        dataset containing information to create box-plot from
        calculate_boxplot
    label_bx: list
        list of string labels to use in box-plot from calculate_boxplot
    ylabel : str
        Title of y-axis
    vmin : real number
        Min value to use on y-axis
    vmax : real number
        Max value to use on y-axis
    outname : str
        file location and name of plot (do not include .png)
    domain_type : str
        Domain type specified in input yaml file
    domain_name : str
        Domain name specified in input yaml file
    plot_dict : dictionary
        Dictionary containing information about plotting for each pair
        (e.g., color, linestyle, markerstyle)
    fig_dict : dictionary
        Dictionary containing information about figure
    text_dict : dictionary
        Dictionary containing information about text
    debug : boolean
        Whether to plot interactively (True) or not (False). Flag for
        submitting jobs to supercomputer turn off interactive mode.

    Returns
    -------
    plot
        box plot

    """
    if not debug:
        plt.ioff()
    # First define items for all plots
    # set default text size
    def_text = dict(fontsize=14)
    if text_dict is not None:
        text_kwargs = {**def_text, **text_dict}
    else:
        text_kwargs = def_text
    # set ylabel to column if not specified.
    if ylabel is None:
        ylabel = label_bx[0]["label"]

    # Fix the order and palate colors
    order_box = []
    pal = {}
    for i in range(len(label_bx)):
        order_box.append(label_bx[i]["label"])
        pal[label_bx[i]["label"]] = label_bx[i]["color"]

    # Make plot
    if fig_dict is not None:
        f, ax = plt.subplots(**fig_dict)
    else:
        f, ax = plt.subplots(figsize=(8, 8))
    # Define characteristics of boxplot.
    boxprops = {"edgecolor": "k", "linewidth": 1.5}
    lineprops = {"color": "k", "linewidth": 1.5}
    boxplot_kwargs = {
        "boxprops": boxprops,
        "medianprops": lineprops,
        "whiskerprops": lineprops,
        "capprops": lineprops,
        "fliersize": 2.0,
        "flierprops": dict(
            marker="*", markerfacecolor="blue", markeredgecolor="none", markersize=6.0
        ),
        "width": 0.75,
        "palette": pal,
        "order": order_box,
        "showmeans": True,
        "meanprops": {
            "marker": ".",
            "markerfacecolor": "black",
            "markeredgecolor": "black",
            "markersize": 20.0,
        },
    }
    sns.set_style("whitegrid")
    sns.set_style("ticks")
    sns.boxplot(
        ax=ax,
        x="variable",
        y="value",
        hue="variable",
        data=pd.melt(comb_bx),
        **boxplot_kwargs,
    )
    ax.set_xlabel("")
    ax.set_ylabel(ylabel, fontweight="bold", **text_kwargs)
    ax.tick_params(labelsize=text_kwargs["fontsize"] * 0.8)
    ax.yaxis.get_offset_text().set_fontsize(text_kwargs["fontsize"] * 0.8)
    if domain_type is not None and domain_name is not None:
        if domain_type == "epa_region":
            ax.set_title("EPA Region " + domain_name, fontweight="bold", **text_kwargs)
        else:
            ax.set_title(domain_name, fontweight="bold", **text_kwargs)
    if vmin is not None and vmax is not None:
        ax.set_ylim(ymin=vmin, ymax=vmax)

    plt.tight_layout()
    savefig(
        outname + ".png",
        #    loc=4,
        logo_height=100,
        bbox_inches="tight",
        dpi=200,
    )
    if debug is False:
        plt.close(plt.gcf())


def make_spatial_dist(
    dset,
    varname=None,
    label=None,
    ylabel=None,
    vmin=None,
    vmax=None,
    nlevels=None,
    proj=None,
    outname="plot",
    domain_type=None,
    domain_name=None,
    fig_dict=None,
    text_dict=None,
    uxgrid = None,
    debug=False,
):
    """Creates a plot for satellite or model data.

    Parameters
    ----------
    dset : xr.Dataset
        Dataset containing the paired data

    """

    # detect unstructured input from cesm-se. 
    is_unstructured = uxgrid is not None or any(
        d in dset[varname].dims for d in ("n_face", "ncol")
    )

    if is_unstructured and uxgrid is None:
        grid_file = dset.attrs.get("mio_scrip_file") or dset.attrs.get("mio_mesh_file")
        if not grid_file:
            raise ValueError(
                "make_spatial_dist: unstructured input but no uxgrid passed "
                "and no mio_scrip_file/mio_mesh_file attr on dset."
            )

        uxgrid = ux.open_grid(grid_file)
    
    if not debug:
        plt.ioff()

    def_map = dict(states=True, figsize=[15, 8])
    if fig_dict is not None:
        map_kwargs = {**def_map, **fig_dict}
    else:
        map_kwargs = def_map

    # set default text size
    def_text = dict(fontsize=20)
    if text_dict is not None:
        text_kwargs = {**def_text, **text_dict}
    else:
        text_kwargs = def_text

    # set ylabel to column if not specified.
    if ylabel is None:
        ylabel = varname
        if "units" in dset[varname].attrs:
            ylabel = f"{ylabel} ({dset[varname].attrs['units']})"

    # Take the difference for the model output - the sat output

    #  hand the renderer a single 2-D map
    # (pcolormesh) or 1-D column field (uxarray polygons). h
    # structured (time, lat, lon) and unstructured (time, n_face) shapes
    
    var2plot = dset[varname]
    if "time" in var2plot.dims:
        var2plot = var2plot.mean("time")
    var2plot = var2plot.squeeze()
    
    # if len(var2plot.dims) == 3:
    #     var2plot = var2plot.mean("time")

    #  hand the renderer a single 2-D map
    # (pcolormesh) or 1-D column field (uxarray polygons). Works for both
    # structured (time, lat, lon) and unstructured (time, n_face)
    var2plot = dset[varname]
    if "time" in var2plot.dims:
        var2plot = var2plot.mean("time")
    var2plot = var2plot.squeeze()
    
    # Determine the domain
    if domain_type == "all" and domain_name == "CONUS":
        latmin = 25.0
        lonmin = -130.0
        latmax = 50.0
        lonmax = -60.0
        title_add = domain_name + ": "
    elif domain_type == "epa_region" and domain_name is not None:
        latmin, lonmin, latmax, lonmax, acro = get_epa_bounds(index=None, acronym=domain_name)
        title_add = "EPA Region " + domain_name + ": "
    elif domain_type == "giorgi_region" and domain_name is not None:
        latmin, lonmin, latmax, lonmax, acro = get_giorgi_bounds(index=None, acronym=domain_name)
        title_add = "Giorgi Region " + domain_name + ": "
    elif domain_name == "model":
        latmin, latmax = dset["latitude"].min(), dset["latitude"].max()
        lonmin, lonmax = dset["longitude"].min(), dset["longitude"].max()
        title_add = ""
    elif domain_type and (str(domain_type).startswith("auto-region:")
                      or str(domain_type).startswith("custom:")):
        # zoom to where the field has data (the region the driver subset to),
        # so a global/CONUS grid doesn't render worldwide.
        _finite = var2plot.notnull()
        _lat = dset["latitude"].where(_finite)
        _lon = dset["longitude"].where(_finite)
        latmin, latmax = float(_lat.min()), float(_lat.max())
        lonmin, lonmax = float(_lon.min()), float(_lon.max())
        title_add = domain_name + ": "
    else:
        latmin = -90
        lonmin = -180
        latmax = 90
        lonmax = 180
        title_add = domain_name + ": "

    # Map the model output first.
    cbar_kwargs = dict(aspect=15, shrink=0.8)

    # Add options that this could be included in the fig_kwargs in yaml file too.
    if "extent" not in map_kwargs:
        map_kwargs["extent"] = [lonmin, lonmax, latmin, latmax]
    if "crs" not in map_kwargs:
        map_kwargs["crs"] = proj

    # First determine colorbar
    if vmin is None and vmax is None:
        # vmin = vmodel_mean.quantile(0.01)
        vmax = np.max((np.abs(var2plot.quantile(0.99)), np.abs(var2plot.quantile(0.01))))
        vmin = -vmax

    if nlevels is None:
        nlevels = 21
    print(vmin, vmax)
    clevel = np.linspace(vmin, vmax, nlevels)
    cmap = mpl.cm.get_cmap("plasma", nlevels - 1)
    norm = mpl.colors.BoundaryNorm(clevel, ncolors=cmap.N, clip=False)

    # I add extend='both' here because the colorbar is setup to plot the values outside the range
    states = fig_dict.get("states", True)
    counties = fig_dict.get("counties", False)
    ax = monet.plots.mapgen.draw_map(
        crs=map_kwargs["crs"], extent=map_kwargs["extent"], states=states, counties=counties
    )
    # draw scatter plot of model and satellite differences
    # c = ax.axes.scatter(dset.longitude, dset.latitude, c=var2plot, cmap=cmap, s=2, norm=norm)
    #c = ax.axes.pcolormesh(dset.longitude, dset.latitude, var2plot, cmap=cmap, norm=norm)

    # structured grids can use pccolormesh. unstructured use uxarray polygons
    if is_unstructured:
        from melodies_monet.plots.uxarray_render import render_unstructured_field

        c = render_unstructured_field(
            ax.axes, var2plot, uxgrid,
            cmap=cmap, norm=norm,
            extent=map_kwargs["extent"],
            coast=False, borders=False, states=False, gridlines=False,
            colorbar=False,)
    else:
        c = ax.axes.pcolormesh(
            dset.longitude, dset.latitude, var2plot, cmap=cmap, norm=norm,)
    
    plt.gcf().canvas.draw()
    plt.tight_layout(pad=0)
    timestamps = (
        f" {dset['time'][0].values.astype(str)[:16]}$-${dset['time'][-1].values.astype(str)[:16]}"
    )
    plt.title(title_add + label + timestamps, fontweight="bold", **text_kwargs)
    ax.axes.set_extent(map_kwargs["extent"], crs=ccrs.PlateCarree())

    # Uncomment these lines if you update above just to verify colorbars are identical.
    # Also specify plot above scatter = ax.axes.scatter etc.
    # cbar = ax.figure.get_axes()[1]
    plt.colorbar(c, ax=ax, extend="both", **cbar_kwargs)

    # Update colorbar
    f = plt.gcf()

    model_ax = f.get_axes()[0]
    cax = f.get_axes()[1]

    # get the position of the plot axis and use this to rescale nicely the color bar to the height of the plot.
    position_m = model_ax.get_position()
    position_c = cax.get_position()
    cax.set_position(
        [
            position_c.x0,
            position_m.y0,
            position_c.x1 - position_c.x0,
            (position_m.y1 - position_m.y0) * 1.1,
        ]
    )
    cax.set_ylabel(ylabel, fontweight="bold", **text_kwargs)
    cax.tick_params(
        labelsize=text_kwargs["fontsize"] * 0.8,
        length=10.0,
        width=2.0,
        grid_linewidth=2.0,
    )

    cax.yaxis.get_offset_text().set_fontsize(text_kwargs["fontsize"] * 0.8)

    # plt.tight_layout(pad=0)
    savefig(
        outname + ".png",
        #    loc=4,
        logo_height=100,
        bbox_inches="tight",
        dpi=150,
    )
    if debug is False:
        plt.close(plt.gcf())
    return ax


def make_spatial_bias_gridded(
    dset,
    varname_o=None,
    label_o=None,
    varname_m=None,
    label_m=None,
    ylabel=None,
    vdiff=None,
    nlevels=None,
    proj=None,
    outname="plot",
    domain_type=None,
    domain_name=None,
    fig_dict=None,
    text_dict=None,
    debug=False,
    uxgrid=None,
    **kwargs
):
    """Creates difference plot for satellite and model data.
    For data in swath format, overplots all differences
    For data on regular grid, mean difference.

    Parameters
    ----------
    dset : xr.Dataset
        model/obs paired data to plot
    varname_o : str
        Name of observation variable to plot
    label_o : str
        Name of observation variable to use in plot title
    varname_m : str
        Name of model variable to plot
    label_m : str
        Name of model variable to use in plot title
    cblabel : str
        Title of colorbar axis
    vdiff : float
        Min and max value to use on colorbar axis
    nlevels : float
        number of levels to break colorbar map into
    proj : cartopy projection
        cartopy projection to use in plot

    Returns
    -------
    plot
        satellite spatial bias plot

    """

    # Detect unstructured input (CESM-SE et al). only the
    # actual data->geometry step differs (PolyCollection vs pcolormesh).
    is_unstructured = uxgrid is not None or any(
        d in dset[varname_m].dims for d in ("n_face", "ncol"))
    
    if is_unstructured and uxgrid is None:
        grid_file = dset.attrs.get("mio_scrip_file") or dset.attrs.get("mio_mesh_file")
        if not grid_file:
            raise ValueError(
                "make_spatial_bias_gridded: unstructured input but no uxgrid "
                "passed and no mio_scrip_file/mio_mesh_file attr on dset.")

        uxgrid = ux.open_grid(grid_file)
    if not debug:
        plt.ioff()

    def_map = dict(states=True, figsize=[15, 8])
    if fig_dict is not None:
        map_kwargs = {**def_map, **fig_dict}
    else:
        map_kwargs = def_map

    # set default text size
    def_text = dict(fontsize=20)
    if text_dict is not None:
        text_kwargs = {**def_text, **text_dict}
    else:
        text_kwargs = def_text

    # set ylabel to column if not specified.
    if ylabel is None:
        ylabel = varname_o
        if "units" in dset[varname_o].attrs:
            ylabel = f"{ylabel} ({dset[varname_o].attrs['units']})"

    # Take the difference for the model output - the sat output

    diff_mod_min_obs = (dset[varname_m] - dset[varname_o]).squeeze()
    # # Take mean over time,
    # if len(diff_mod_min_obs.dims) == 3:
    #     diff_mod_min_obs = diff_mod_min_obs.mean("time")

    # Reduce away time so the renderer (uxarray polygons or pcolormesh)
    # gets a single 1-D / 2-D map. 
    
    diff_mod_min_obs = dset[varname_m] - dset[varname_o]
    if "time" in diff_mod_min_obs.dims:
        diff_mod_min_obs = diff_mod_min_obs.mean("time")
    diff_mod_min_obs = diff_mod_min_obs.squeeze()

    # Determine the domain
    if domain_type == "all" and domain_name == "CONUS":
        latmin = 25.0
        lonmin = -130.0
        latmax = 50.0
        lonmax = -60.0
        title_add = domain_name + ": "
    elif domain_type == "epa_region" and domain_name is not None:
        latmin, lonmin, latmax, lonmax, _ = get_epa_bounds(index=None, acronym=domain_name)
        title_add = "EPA Region " + domain_name + ": "
    elif domain_type == "giorgi_region" and domain_name is not None:
        latmin, lonmin, latmax, lonmax, _ = get_giorgi_bounds(index=None, acronym=domain_name)
        title_add = "Giorgi Region " + domain_name + ": "
    elif domain_name == "model":
        latmin, latmax = dset["latitude"].min(), dset["latitude"].max()
        lonmin, lonmax = dset["longitude"].min(), dset["longitude"].max()
        title_add = ""
    elif domain_type and (str(domain_type).startswith("auto-region:")
                          or str(domain_type).startswith("custom:")):
        # zoom to where the difference has data (the region the driver subset
        # to), so a global/CONUS grid doesn't render worldwide.
        _finite = diff_mod_min_obs.notnull()
        _lat = dset["latitude"].where(_finite)
        _lon = dset["longitude"].where(_finite)
        latmin, latmax = float(_lat.min()), float(_lat.max())
        lonmin, lonmax = float(_lon.min()), float(_lon.max())
        title_add = domain_name + ": "    
    else:
        latmin = -90
        lonmin = -180
        latmax = 90
        lonmax = 180
        title_add = domain_name + ": "

    # Map the model output first.
    cbar_kwargs = dict(aspect=15, shrink=0.8)

    # Add options that this could be included in the fig_kwargs in yaml file too.
    if "extent" not in map_kwargs:
        map_kwargs["extent"] = [lonmin, lonmax, latmin, latmax]
    if "crs" not in map_kwargs:
        map_kwargs["crs"] = proj

    # First determine colorbar
    if vdiff is None:
        vdiff = np.max(
            (
                np.abs(diff_mod_min_obs.quantile(0.99)),
                np.abs(diff_mod_min_obs.quantile(0.01)),
            )
        )

    if nlevels is None:
        clevel = np.linspace(-vdiff, vdiff, 256)          # dense, for cbar ticks
        cmap = plt.get_cmap("RdBu_r")                     # continuous
        norm = mpl.colors.Normalize(vmin=-vdiff, vmax=vdiff)
    else:
        clevel = np.linspace(-vdiff, vdiff, nlevels)
        cmap = mpl.cm.get_cmap("RdBu_r", nlevels - 1)
        norm = mpl.colors.BoundaryNorm(clevel, ncolors=cmap.N, clip=False)

    clevel = np.linspace(-vdiff, vdiff, nlevels)
    cmap = mpl.cm.get_cmap("RdBu_r", nlevels - 1)
    norm = mpl.colors.BoundaryNorm(clevel, ncolors=cmap.N, clip=False)

    # I add extend='both' here because the colorbar is setup to plot the values outside the range
    states = fig_dict.get("states", True)
    counties = fig_dict.get("counties", False)
    ax = monet.plots.mapgen.draw_map(
        crs=map_kwargs["crs"], extent=map_kwargs["extent"], states=states, counties=counties
    )

    # Draw the diff field. Structured -> pcolormesh; unstructured -> uxarray
    if is_unstructured:
        from melodies_monet.plots.uxarray_render import render_unstructured_field

        c = render_unstructured_field(
            ax.axes, diff_mod_min_obs, uxgrid,
            cmap=cmap, norm=norm,
            extent=map_kwargs["extent"],
            coast=False, borders=False, states=False, gridlines=False,
            colorbar=False,
        )
    else:
        c = ax.axes.pcolormesh(
            dset.longitude, dset.latitude, diff_mod_min_obs, cmap=cmap, norm=norm,
        )
        
    # draw scatter plot of model and satellite differences
    # c = ax.axes.scatter(
    #     dset.longitude, dset.latitude, c=diff_mod_min_obs, cmap=cmap, s=2, norm=norm
    # )
    #c = ax.axes.pcolormesh(dset.longitude, dset.latitude, diff_mod_min_obs, cmap=cmap, norm=norm)
    
    plt.gcf().canvas.draw()
    plt.tight_layout(pad=0)
    timestamps = (
        f" {dset['time'][0].values.astype(str)[:16]}$-${dset['time'][-1].values.astype(str)[:16]}"
    )
    plt.title(title_add + label_m + " - " + label_o + timestamps, fontweight="bold", **text_kwargs)
    ax.axes.set_extent(map_kwargs["extent"], crs=ccrs.PlateCarree())

    # Uncomment these lines if you update above just to verify colorbars are identical.
    # Also specify plot above scatter = ax.axes.scatter etc.
    # cbar = ax.figure.get_axes()[1]
    plt.colorbar(c, ax=ax, extend="both", **cbar_kwargs)

    # Update colorbar
    f = plt.gcf()

    model_ax = f.get_axes()[0]
    cax = f.get_axes()[1]

    # get the position of the plot axis and use this to rescale nicely the color bar to the height of the plot.
    position_m = model_ax.get_position()
    position_c = cax.get_position()
    cax.set_position(
        [
            position_c.x0,
            position_m.y0,
            position_c.x1 - position_c.x0,
            (position_m.y1 - position_m.y0) * 1.1,
        ]
    )
    cax.set_ylabel(r"$\Delta$" + ylabel, fontweight="bold", **text_kwargs)
    cax.tick_params(
        labelsize=text_kwargs["fontsize"] * 0.8,
        length=10.0,
        width=2.0,
        grid_linewidth=2.0,
    )

    cax.yaxis.get_offset_text().set_fontsize(text_kwargs["fontsize"] * 0.8)

    # plt.tight_layout(pad=0)
    savefig(
        outname + ".png",
        loc=4,
        logo_height=100,
        bbox_inches="tight",
        dpi=150,
    )
    if debug is False:
        plt.close(plt.gcf())
    return ax


def make_multi_boxplot(
    comb_bx,
    label_bx,
    region_bx,
    region_list=None,
    model_name_list=None,
    ylabel=None,
    vmin=None,
    vmax=None,
    outname="plot",
    domain_type=None,
    domain_name=None,
    plot_dict=None,
    fig_dict=None,
    text_dict=None,
    debug=False,
):
    """Creates box-plot.

    Parameters
    ----------
    comb_bx : dataframe
        dataframe containing information to create box-plot from
        calculate_boxplot
    label_bx : list
        list of string labels to use in box-plot from calculate_boxplot
    region_bx : dataframe
        dataframe containing information of boxes to help create multi-box-plot
        from calculate_boxplot
    model_name_list : list of str
        list of models and observation sources used for x-labels in plot
    ylabel : str
        Title of y-axis
    vmin : real number
        Min value to use on y-axis
    vmax : real number
        Max value to use on y-axis
    outname : str
        file location and name of plot (do not include .png)
    domain_type : str
        Domain type specified in input yaml file
    domain_name : str
        Domain name specified in input yaml file
    plot_dict : dictionary
        Dictionary containing information about plotting for each pair
        (e.g., color, linestyle, markerstyle)
    fig_dict : dictionary
        Dictionary containing information about figure
    text_dict : dictionary
        Dictionary containing information about text
    debug : boolean
        Whether to plot interactively (True) or not (False). Flag for
        submitting jobs to supercomputer turn off interactive mode.

    Returns
    -------
    plot
        multi-box plot

    """
    if not debug:
        plt.ioff()
    # First define items for all plots
    # set default text size
    def_text = dict(fontsize=14)
    if text_dict is not None:
        text_kwargs = {**def_text, **text_dict}
    else:
        text_kwargs = def_text
    # set ylabel to column if not specified.
    if ylabel is None:
        ylabel = label_bx[0]["column"]

    # Fix the order and palate colors
    order_box = []
    pal = {}
    for i in range(len(label_bx)):
        order_box.append(label_bx[i]["label"])
        pal[label_bx[i]["label"]] = label_bx[i]["color"]

    # Make plot
    if fig_dict is not None:
        f, ax = plt.subplots(**fig_dict)
    else:
        f, ax = plt.subplots(figsize=(8, 8))
    # Define characteristics of boxplot.
    sns.set_style("whitegrid")
    sns.set_style("ticks")
    len_combx = len(comb_bx.columns)

    data_obs = comb_bx[comb_bx.columns[0]].to_frame().rename({comb_bx.columns[0]: "Value"}, axis=1)
    data_obs["model"] = model_name_list[0]
    data_obs["Regions"] = region_bx["set_regions"].values
    to_concat = []
    to_concat.append(data_obs[["Value", "model", "Regions"]])

    for i in range(1, len_combx):
        data_model = (
            comb_bx[comb_bx.columns[i]].to_frame().rename({comb_bx.columns[i]: "Value"}, axis=1)
        )
        data_model["model"] = model_name_list[i]
        data_model["Regions"] = region_bx["set_regions"].values
        to_concat.append(data_model[["Value", "model", "Regions"]])

    tdf = pd.concat(to_concat)
    acro = region_list
    sns.boxplot(
        x="Regions",
        y="Value",
        hue="model",
        data=tdf.loc[tdf.Regions.isin(acro)],
        order=acro,
        showfliers=False,
    )
    ax.set_xlabel("")
    ax.set_ylabel(ylabel, fontweight="bold", **text_kwargs)
    ax.tick_params(labelsize=text_kwargs["fontsize"] * 0.8)
    if domain_type is not None and domain_name is not None:
        if domain_type == "epa_region":
            ax.set_title("EPA Region " + domain_name, fontweight="bold", **text_kwargs)
        elif domain_type == "giorgi_region":
            ax.set_title("Giorgi Region" + domain_name, fontweight="bold", **text_kwargs)
        else:
            ax.set_title(domain_name, fontweight="bold", **text_kwargs)
    if vmin is not None and vmax is not None:
        ax.set_ylim(ymin=vmin, ymax=vmax)

    plt.tight_layout()
    savefig(outname + ".png", loc=4, logo_height=100)
    if debug is False:
        plt.close(plt.gcf())


def make_diurnal_cycle(dset, varname, ax=None, **kwargs):
    """Calculates diurnal cycle for region and does the timeseries

    Parameters
    ----------
    dset : xr.Dataset
        Dataset with paired data
    time_offset : int | float
        Offset (in hours) to apply to the diurnal cycle
    ax : ax
        matplotlib ax from previous occurrence so can overlay obs and
        model results on the same plot
    **kwargs
        Other plotting arguments.
        Optional arguments are:

        * time_offset : int | float, optional
            Time offset in hours. E. g., if you are at UTC-7, and wish
            to have the plot at local time, do time_offset=-7.
            Default = 0.
        * ylabel : str, optional
            Title of y-axis
            Default = varname
        * vmin : real number, optional
            Min value to use on y-axis
        * vmax : real number, optional
            Max value to use on y-axis
        * domain_type : str, optional
            Domain type specified in input yaml file
        * domain_name : str, optional
            Domain name specified in input yaml file
        * plot_dict : dict, optional
            Dictionary containing information about plotting for
            each pair (e.g., color, linestyle, markerstyle)
        * fig_dict : dict, optional
            Dictionary containing information about figure
        * text_dict : dict, optional
            Dictionary containing information about text
        * range_shading : str, optional
            Whether to shade the range obtained for each hour.
            options: "no", "total", "std", "pct:number".
            If "no", no range shading if performed.
            if "total", the total range obtained is shaded.
            If "std", the standard deviation is shaded.
            if "pct:number", then the percentile chosen is shaded
            (e. g., "pct:98")
        * debug : bool, optional
            Whether to plot interactively (True) or not (False). Flag
            for submitting jobs to supercomputer turn off interactive
            mode.

    Returns
    -------
    ax
        matplotlib ax such that driver.py can iterate to overlay
        multiple models on the same plot
    """
    dset_copy = dset.copy()
    time_offset = kwargs.get("time_offset", 0)
    # dset_copy["time"] = dset_copy["time"] + np.timedelta64(time_offset, "h")
    # pd.to_timedelt so fractional hour offsets work 
    dset_copy["time"] = dset_copy["time"] + pd.to_timedelta(time_offset, unit="h")

    # Collapse all spatial dims (x/y swath, n_face/ncol unstructured, ...)
    # so only time remains for the diurnal grouping.
    spatial_dims = [d for d in dset_copy[varname].dims if d != "time"]
    if spatial_dims:
        dset_copy = dset_copy.mean(dim=spatial_dims)
    dset_diurnal_group = dset_copy[[varname]].groupby("time.hour")
    dset_diurnal = dset_diurnal_group.median()

    n_hours = dset_diurnal.sizes.get("hour", 0)
    if n_hours <= 3:
        warnings.warn(
            f"Diurnal cycle for '{varname}' only has data in {n_hours} distinct "
            "hour(s) of the day. Your observation type may not have diurnal "
            "resolution (e.g., a polar-orbiting satellite like TROPOMI samples "
            "each location ~once per day)."
        )

    # Set some defaults
    text_kwargs = {"fontsize": 14}
    style_dict = {"linestyle": "-", "marker": "*", "linewidth": "1.2", "markersize": "6.0"}
    if ax is None:
        style_dict["color"] = "k"
        fig_dict = kwargs.get("fig_dict", {"figsize": (10, 6)})
        f, ax = plt.subplots(**fig_dict)

    if "text_dict" in kwargs:
        text_kwargs = {**text_kwargs, **kwargs["text_dict"]}

    ylabel = kwargs.get("ylabel", varname)
    if "units" in kwargs:
        ylabel = f"{ylabel} ({kwargs['units']})"
    elif "units" in dset[varname].attrs:
        ylabel = f"{ylabel} ({dset[varname].attrs['units']})"

    label = kwargs.get("label", None)
    p = ax.plot(
        dset_diurnal["hour"],
        dset_diurnal[varname],
        label=label,
        **{**style_dict, **(kwargs.get("plot_dict") or {})},
    )
    ax.set_xlabel(kwargs.get("xlabel", "hour"), **text_kwargs)
    ax.set_ylabel(ylabel, **text_kwargs)
    ax.legend(fontsize=text_kwargs["fontsize"] * 0.8)

    range_shading = kwargs.get("range_shading", "IQR")
    range_shading = kwargs["range_shading"]
    if range_shading == "no":
        pass
    elif (range_shading not in ["total", "std", "IQR"]) and ("pct:" not in range_shading):
        warnings.warn(
            f"range_shading is {range_shading}, not in ['no', 'total', 'std', 'IQR'] nor 'pct:'."
            + " Ignoring."
        )
    else:
        if range_shading == "total":
            range_max = dset_diurnal_group.max()[varname]
            range_min = dset_diurnal_group.min()[varname]
        elif range_shading == "std":
            std = dset_diurnal_group.std()[varname]
            range_max = dset_diurnal[varname] + std
            range_min = dset_diurnal[varname] - std
        elif range_shading == "IQR":
            range_max = dset_diurnal_group.quantile(q=0.75)[varname]
            range_min = dset_diurnal_group.quantile(q=0.25)[varname]
        elif "pct:" in range_shading:
            quantile = float(range_shading[4:]) / 100
            upper_range = quantile + (1 - quantile) / 2
            lower_range = (1 - quantile) / 2
            range_max = dset_diurnal_group.quantile(upper_range)[varname]
            range_min = dset_diurnal_group.quantile(lower_range)[varname]
        color = p[-1].get_color()
        ax.fill_between(dset_diurnal["hour"], range_min, range_max, alpha=0.2, color=color)
    vmax = kwargs.get("vmax", None)
    vmin = kwargs.get("vmin", None)
    vmax = float(vmax) if vmax is not None else None
    vmin = float(vmin) if vmin is not None else None
    ax.set_ylim(top=vmax, bottom=vmin)

    if kwargs.get("domain_name"):
        ax.set_title(f"{kwargs['domain_name']}", fontsize=text_kwargs["fontsize"])
    return ax


def sel_region(domain_type=None, domain_name=None, domain_box=None):
    """Selects box for region.
    If the region has a domain name, it is selected using
    get_epa_bounds or get_giorgi_bounds.
    Otherwise, if there is a domain_box, it is selected as
    a whole. The current implementation cannot deal with
    domain boxes containing the antimeridian.

    Parameters
    ----------
    domain_type: str
        'all', 'epa_region', 'giorgi_region', 'auto-region:giorgi',
        'auto-region:CNA', 'custom'
    domain_name: str
        EPA or Giorgi region acronym
    domain_box: list[int|float, int|float, int|float, int|float]
        domain box containing the region to be plotted. Only read if
        region is 'custom'. Expected order: latmin, lonmin, latmax, lonmax

    Returns
    -------
    Boundaries for the plotting
    """
    title_add = ""
    if domain_type == "all" and domain_name == "CONUS":
        latmin = 25.0
        lonmin = -130.0
        latmax = 50.0
        lonmax = -60.0
        title_add = domain_name + ": "
    elif "epa" in domain_type and domain_name is not None:
        latmin, lonmin, latmax, lonmax, acro = get_epa_bounds(index=None, acronym=domain_name)
        title_add = "EPA Region " + domain_name + ": "
    elif "giorgi" in domain_type and domain_name is not None:
        latmin, lonmin, latmax, lonmax, acro = get_giorgi_bounds(index=None, acronym=domain_name)
        title_add = "Giorgi Region " + domain_name + ": "
    elif domain_type == "custom":
        assert lonmax <= 180, "Longitude must be in range -180, 180"
        latmin, lonmin, latmax, lonmax = domain_box
    elif domain_type == "all":
        latmin = -90
        lonmin = -180
        latmax = 90
        lonmax = 180
        title_add = domain_name + ": "
    return latmin, lonmin, latmax, lonmax, title_add
