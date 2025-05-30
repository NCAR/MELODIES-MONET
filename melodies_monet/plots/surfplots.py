# SPDX-License-Identifier: Apache-2.0
#
#Code to create plots for surface observations

import monet as monet
import seaborn as sns
import pandas as pd
import numpy as np
import cartopy.crs as ccrs
import matplotlib as mpl
import matplotlib.pyplot as plt
from numpy import corrcoef
sns.set_context('paper')
from monet.plots.taylordiagram import TaylorDiagram as td
from matplotlib.colors import ListedColormap
from monet.util.tools import get_epa_region_bounds as get_epa_bounds 
import math
from ..plots import savefig
from scipy.stats import ttest_ind
from statannotations.Annotator import Annotator

def make_24hr_regulatory(df, col=None):
    """Calculates 24-hour averages
    
    Parameters
    ----------
    df : dataframe
        Model/obs pair of hourly data
    col : str
        Column label of observation variable to apply the calculation 
    Returns
    -------
    dataframe
        dataframe with applied calculation
        
    """
    #return calc_24hr_ave(df, col)
    return calc_24hr_ave_v1(df, col)

def calc_24hr_ave_v1(df, col=None):
    df.index = df.time_local
    # select sites with nobs >=18, 75% completeness
    df_24hr_ave = (df.groupby("siteid")[col].resample("D").sum(min_count=18, numeric_only=True)/df.groupby("siteid")[col].resample("D").count()).reset_index().dropna()
    df = df.reset_index(drop=True)
    return df.merge(df_24hr_ave, on=["siteid", "time_local"])

def make_8hr_regulatory(df, col=None):
    """Calculates 8-hour rolling average daily
    
    Parameters
    ----------
    df : dataframe
        Model/obs pair of hourly data
    col : str
        Column label of observation variable to apply the calculation 
    Returns
    -------
    dataframe
        dataframe with applied calculation
        
    """
    #return calc_8hr_rolling_max(df, col, window=8)
    return calc_8hr_rolling_max_v1(df, col, window=8)

def calc_8hr_rolling_max_v1(df, col=None, window=None):
    df.index = df.time_local
    df_rolling = df.groupby("siteid")[col].rolling(window,min_periods=6,center=True, win_type="boxcar").mean(numeric_only=True).reset_index().dropna()
    # JianHe: select sites with nobs >=18, 75% completeness based on EPA
    df_rolling.index = df_rolling.time_local
    df_rolling_max = df_rolling.groupby("siteid").resample("D").max(min_count=18, numeric_only=True).reset_index().dropna()
    df = df.reset_index(drop=True)
    return df.merge(df_rolling_max, on=["siteid", "time_local"])

def calc_default_colors(p_index):
    """List of default colors, lines, and markers to use if user does not 
    specify them in the input yaml file.
    
    Parameters
    ----------
    p_index : integer
        Number of pairs in analysis class
    
    Returns
    -------
    list
        List of dictionaries containing default colors, lines, and 
        markers to use for plotting for the number of pairs in analysis class
        
    """
    x = [dict(color='b', linestyle='--',marker='x'),
         dict(color='g', linestyle='-.',marker='o'),
         dict(color='r', linestyle=':',marker='v'),
         dict(color='c', linestyle='--',marker='^'),
         dict(color='m', linestyle='-.',marker='s')]
    #Repeat these 5 instances over and over if more than 5 lines.
    return x[p_index % 5]

def new_color_map():
    """Creates new color map for difference plots
    
    Returns
    -------
    colormap
        Orange and blue color map
        
    """
    top = plt.get_cmap("Blues_r", 128)
    bottom = plt.get_cmap("Oranges", 128)

    newcolors = np.vstack((top(np.linspace(0, 1, 128)),
                           bottom(np.linspace(0, 1, 128))))
    return ListedColormap(newcolors, name='OrangeBlue')

# Register the custom cmap
_cmap_name = "OrangeBlue"
try:
    plt.get_cmap(_cmap_name)
except ValueError:
    _cmap = new_color_map()
    try:
        mpl.colormaps.register(_cmap)  # mpl 3.6+
    except AttributeError:
        mpl.cm.register_cmap(cmap=_cmap)  # old method

def map_projection(m, *, model_name=None):
    """Define map projection.
    
    Parameters
    ----------
    m : melodies_monet.driver.model
        Model class instance.
    model_name : str, optional
        For example, ``'rrfs'``. ``m.model.lower()`` used if not provided.
        If provided, will be used to create a new projection
        (i.e., an existing ``m.proj`` projection won't be returned).

    Returns
    -------
    cartopy.crs.Projection
        Projection to be used by cartopy in plotting.
    """
    import cartopy.crs as ccrs

    if model_name is None:
        mod = m.model.lower()
        if m.proj is not None:
            if isinstance(m.proj, str) and m.proj.startswith("model:"):
                mod_name_for_proj = m.proj.split(":")[1].strip()
                return map_projection(m, model_name=mod_name_for_proj)
            elif isinstance(m.proj, ccrs.Projection):
                return m.proj
            else:
                raise TypeError(
                    "`model.proj` should be None or str starting with 'model:' "
                    "or `ccrs.Projection` instance. "
                    f"Got {type(m.proj)}."
                )
    else:
        mod = model_name

    if mod == 'cmaq':
        proj = ccrs.LambertConformal(
            central_longitude=m.obj.XCENT, central_latitude=m.obj.YCENT)
    elif mod in {'wrfchem', 'rapchem'}:
        if m.obj.MAP_PROJ == 1:
            proj = ccrs.LambertConformal(
                central_longitude=m.obj.CEN_LON, central_latitude=m.obj.CEN_LAT)
        elif m.obj.MAP_PROJ == 6:
            #Plate Carree is the equirectangular or equidistant cylindrical
            proj = ccrs.PlateCarree(
                central_longitude=m.obj.CEN_LON)
        else:
            raise NotImplementedError('WRFChem projection not supported. Please add to surfplots.py')         
    # Need to add the projections you want to use for the other models here.
    elif mod == 'rrfs':
        proj = ccrs.LambertConformal(
            central_longitude=m.obj.cen_lon, central_latitude=m.obj.cen_lat)
    elif mod in {"ufschem", 'cesm_fv', 'cesm_se', 'raqms'}: # added ufs-chem here 
        proj = ccrs.PlateCarree()
    elif mod == 'random':
        proj = ccrs.PlateCarree()
    else:
        print(
            f'NOTE: Projection not defined for model {mod!r}. '
            'Please add to surfplots.py. '
            'Setting to `ccrs.PlateCarree()`.'
        )
        proj = ccrs.PlateCarree()
    return proj

def get_utcoffset(lat,lon):
    """get UTC offset in hour based on a point (lat/lon)

    Parameters
    ----------
    lat : 
        Latitude (deg; -90. to 90.)
    lon :
        Longitude (deg; -180. to 180.)
        
    Returns
    -------
    UTC offset in hour

    """
    import datetime
    import pytz
    from timezonefinder import TimezoneFinder

    tf = TimezoneFinder()

    timezone_str = tf.timezone_at(lng=lon, lat=lat)

    if timezone_str is None:
        #print('None timezone: ', lat, lon)
        if lon > -100.0:
            timezone_str = 'America/New_York'
        else:
            timezone_str = 'America/Los_Angeles'

        tz = pytz.timezone(timezone_str)
        d=datetime.utcnow()
        uos = tz.utcoffset(d, is_dst=False)
        utchour = uos.seconds/60.0/60.0
        utcday = uos.days

    elif timezone_str.startswith({'Etc','GMT'}):
        #print('Ocean timezone: ', timezone_str)
        tz = pytz.timezone(timezone_str)
        d=datetime.utcnow()
        uos = tz.utcoffset(d, is_dst=False)
        utchour = uos.seconds/60.0/60.0
        utcday = uos.days

    else:
        #print('Land timezone: ', timezone_str)
        tz = pytz.timezone(timezone_str)
        d=datetime.utcnow()
        uos = tz.utcoffset(d, is_dst=True)
        utchour = uos.seconds/60.0/60.0
        utcday = uos.days

    if utcday < 0:
       utchour = (24-utchour)*(-1) # Local - UTC

    return utchour


def make_spatial_bias(df, df_reg=None, column_o=None, label_o=None, column_m=None, 
                      label_m=None, ylabel = None, ptile = None, vdiff=None,
                      outname = 'plot', 
                      domain_type=None, domain_name=None, fig_dict=None, 
                      text_dict=None,debug=False):
        
    """Creates surface spatial bias plot. 
    
    Parameters
    ----------
    df : pandas.DataFrame
        model/obs paired data to plot
    df_reg : pandas.DataFrame
        model/obs paired regulatory data to plot
    column_o : str
        Column label of observation variable to plot
    label_o : str
        Name of observation variable to use in plot title 
    column_m : str
        Column label of model variable to plot
    label_m : str
        Name of model variable to use in plot title
    ylabel : str
        Title of colorbar axis
    ptile : integer
        Percentile calculation
    vdiff : float
        Min and max value to use on colorbar axis
    outname : str
        file location and name of plot (do not include .png)
    domain_type : str
        Domain type specified in input yaml file
    domain_name : str
        Domain name specified in input yaml file
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
        surface bias plot
        
    """
    if debug is False:
        plt.ioff()
        
    def_map = dict(states=True,figsize=[10, 5])
    if fig_dict is not None:
        map_kwargs = {**def_map, **fig_dict}
    else:
        map_kwargs = def_map
        
    #If not specified use the PlateCarree projection
    if 'crs' not in map_kwargs:
        map_kwargs['crs'] = ccrs.PlateCarree()
  
    #set default text size
    def_text = dict(fontsize=20)
    if text_dict is not None:
        text_kwargs = {**def_text, **text_dict}
    else:
        text_kwargs = def_text
        
    # set ylabel to column if not specified.
    if ylabel is None:
        ylabel = column_o
    if ptile is None:
        ylabel = 'Mean '+ylabel
    else:
        ylabel = '{:02d}'.format(ptile)+'th percentile '+ylabel
 
    if df_reg is not None:
        # JianHe: include options for percentile calculation (set in yaml file)
        if ptile is None:
            df_mean=df_reg.groupby(['siteid'],as_index=False).mean(numeric_only=True)
        else:
            df_mean=df_reg.groupby(['siteid'],as_index=False).quantile(ptile/100., numeric_only=True)

        #Specify val_max = vdiff. the sp_scatter_bias plot in MONET only uses the val_max value
        #and then uses -1*val_max value for the minimum.
        ax = monet.plots.sp_scatter_bias(
            df_mean, col1=column_o+'_reg', col2=column_m+'_reg', map_kwargs=map_kwargs,val_max=vdiff,
            cmap="OrangeBlue", edgecolor='k',linewidth=.8)
    else:
        # JianHe: include options for percentile calculation (set in yaml file)
        if ptile is None:
            df_mean=df.groupby(['siteid'],as_index=False).mean(numeric_only=True)
        else:
            df_mean=df.groupby(['siteid'],as_index=False).quantile(ptile/100., numeric_only=True)
       
        #Specify val_max = vdiff. the sp_scatter_bias plot in MONET only uses the val_max value
        #and then uses -1*val_max value for the minimum.
        ax = monet.plots.sp_scatter_bias(
            df_mean, col1=column_o, col2=column_m, map_kwargs=map_kwargs,val_max=vdiff,
            cmap="OrangeBlue", edgecolor='k',linewidth=.8)

    if domain_type == 'all' and domain_name == 'CONUS':
        latmin= 25.0
        lonmin=-130.0
        latmax= 50.0
        lonmax=-60.0
        plt.title(domain_name + ': ' + label_m + ' - ' + label_o,fontweight='bold',**text_kwargs)
    elif domain_type == 'epa_region' and domain_name is not None:
        latmin,lonmin,latmax,lonmax,acro = get_epa_bounds(index=None,acronym=domain_name)
        plt.title('EPA Region ' + domain_name + ': ' + label_m + ' - ' + label_o,fontweight='bold',**text_kwargs)
    else:
        latmin= math.floor(min(df.latitude))
        lonmin= math.floor(min(df.longitude))
        latmax= math.ceil(max(df.latitude))
        lonmax= math.ceil(max(df.longitude))
        plt.title(domain_name + ': ' + label_m + ' - ' + label_o,fontweight='bold',**text_kwargs)

    if 'extent' not in map_kwargs:
        map_kwargs['extent'] = [lonmin,lonmax,latmin,latmax]  
    ax.axes.set_extent(map_kwargs['extent'],crs=ccrs.PlateCarree())
    
    #Update colorbar
    f = plt.gcf()
    model_ax = f.get_axes()[0]
    cax = f.get_axes()[1]
    #get the position of the plot axis and use this to rescale nicely the color bar to the height of the plot.
    position_m = model_ax.get_position()
    position_c = cax.get_position()
    cax.set_position([position_c.x0, position_m.y0, position_c.x1 - position_c.x0, (position_m.y1-position_m.y0)*1.1])
    cax.set_ylabel(ylabel,fontweight='bold',**text_kwargs)
    cax.tick_params(labelsize=text_kwargs['fontsize']*0.8,length=10.0,width=2.0,grid_linewidth=2.0)    
    
    #plt.tight_layout(pad=0)
    savefig(outname + '.png', loc=4, logo_height=120)
    
def make_timeseries(df, df_reg=None, column=None, label=None, ax=None, avg_window=None, ylabel=None,
                    vmin = None, vmax = None,
                    domain_type=None, domain_name=None,
                    plot_dict=None, fig_dict=None, text_dict=None,debug=False):
    """Creates timeseries plot. 
    
    Parameters
    ----------
    df : pandas.DataFrame
        model/obs paired data to plot
    df_reg : pandas.DataFrame
        model/obs paired regulatory data to plot
    column : str
        Column label of variable to plot
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
    if debug is False:
        plt.ioff()
    #First define items for all plots
    #set default text size
    def_text = dict(fontsize=14)
    if text_dict is not None:
        text_kwargs = {**def_text, **text_dict}
    else:
        text_kwargs = def_text
    # set ylabel to column if not specified.
    if ylabel is None:
        ylabel = column
    if label is not None:
        plot_dict['label'] = label
    if vmin is not None and vmax is not None:
        plot_dict['ylim'] = [vmin,vmax]
    #scale the fontsize for the x and y labels by the text_kwargs
    plot_dict['fontsize'] = text_kwargs['fontsize']*0.8
    #Then, if no plot has been created yet, create a plot and plot the obs.
    if ax is None: 
        #First define the colors for the observations.
        obs_dict = dict(color='k', linestyle='-',marker='*', linewidth=1.2, markersize=6.)
        if plot_dict is not None:
            #Whatever is not defined in the yaml file is filled in with the obs_dict here.
            plot_kwargs = {**obs_dict, **plot_dict}
        else:
            plot_kwargs = obs_dict
        # create the figure
        if fig_dict is not None:
            f,ax = plt.subplots(**fig_dict)    
        else: 
            f,ax = plt.subplots(figsize=(10,6))
        # plot the line
        if df_reg is not None:
            ax = df_reg.set_index("time_local")[column+'_reg'].resample('D').mean().plot(ax=ax, legend=True, **plot_kwargs)
        else:
            if avg_window is None:
                ax = df[column].plot(ax=ax, **plot_kwargs)  
            else:
                ax = df[column].resample(avg_window).mean().plot(ax=ax, legend=True, **plot_kwargs) 

    # If plot has been created add to the current axes.
    else:
        # this means that an axis handle already exists and use it to plot the model output.
        if df_reg is not None:
            ax = df_reg.set_index("time_local")[column+'_reg'].resample('D').mean().plot(ax=ax, legend=True, **plot_dict)
        else:
            if avg_window is None:
                ax = df[column].plot(ax=ax, legend=True, **plot_dict)
            else:
                ax = df[column].resample(avg_window).mean().plot(ax=ax, legend=True, **plot_dict) 
    
    #Set parameters for all plots
    ax.set_ylabel(ylabel,fontweight='bold',**text_kwargs)
    ax.set_xlabel(ax.get_xlabel(),fontweight='bold',**text_kwargs)
    ax.legend(frameon=False,fontsize=text_kwargs['fontsize']*0.8)
    ax.tick_params(axis='both',length=10.0,direction='inout')
    ax.tick_params(axis='both',which='minor',length=5.0,direction='out')
    ax.legend(frameon=False,fontsize=text_kwargs['fontsize']*0.8,
              bbox_to_anchor=(1.0, 0.9), loc='center left')
    if domain_type is not None and domain_name is not None:
        if domain_type == 'epa_region':
            ax.set_title('EPA Region ' + domain_name,fontweight='bold',**text_kwargs)
        else:
            ax.set_title(domain_name,fontweight='bold',**text_kwargs)
    return ax

def make_slr_plot(obs_x, mod_y, column = None, ax = None, ylabel=None,
                    plot_dict=None, fig_dict=None, text_dict=None,debug=False, **kwargs):
    """Creates a SLR plot with the dependent variable on the y-axis and independent variable on the x-axis

    Parameters
    ----------
    """

    if debug is False:
        plt.ioff()
    #First define items for all plots
    #set default text size
    def_text = dict(fontsize=14)
    if text_dict is not None:
        text_kwargs = {**def_text, **text_dict}
    else:
        text_kwargs = def_text
    # set ylabel to column if not specified.
    if ylabel is None:
        ylabel = column
    if label is not None:
        plot_dict['label'] = label

    #scale the fontsize for the x and y labels by the text_kwargs
    plot_dict['fontsize'] = text_kwargs['fontsize']*0.8
    #Then, if no plot has been created yet, create a plot and plot the obs.
    if ax is None: 
        #First define the colors for the observations.
        obs_dict = dict(color='k', linestyle='-',marker='*', linewidth=1.2, markersize=6.)
        if plot_dict is not None:
            #Whatever is not defined in the yaml file is filled in with the obs_dict here.
            plot_kwargs = {**obs_dict, **plot_dict}
        else:
            plot_kwargs = obs_dict
        # create the figure
        if fig_dict is not None:
            f,ax = plt.subplots(**fig_dict)    
        else: 
            f,ax = plt.subplots(figsize=(10,6))
        # plot the line
    else:
        plot_kwargs = { **dict(linestyle='-', marker='*', linewidth=1.2, markersize=6.), **plot_dict}
    time = df.index
    df_plot_group = df.groupby(time.hour)

    
    
def make_diurnal_cycle(df, column=None, label=None, ax=None, avg_window=None, ylabel=None,
                    vmin = None, vmax = None,
                    domain_type=None, domain_name=None,
                    plot_dict=None, fig_dict=None, text_dict=None,debug=False, **kwargs):
    """Creates timeseries plot. 
    
    Parameters
    ----------
    df : pandas.DataFrame
        model/obs paired data to plot
    column : str
        Column label of variable to plot
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
    if debug is False:
        plt.ioff()
    #First define items for all plots
    #set default text size
    def_text = dict(fontsize=14)
    if text_dict is not None:
        text_kwargs = {**def_text, **text_dict}
    else:
        text_kwargs = def_text
    # set ylabel to column if not specified.
    if ylabel is None:
        ylabel = column
    if label is not None:
        plot_dict['label'] = label
    if vmin is not None and vmax is not None:
        plot_dict['ylim'] = [vmin,vmax]

    #scale the fontsize for the x and y labels by the text_kwargs
    plot_dict['fontsize'] = text_kwargs['fontsize']*0.8
    #Then, if no plot has been created yet, create a plot and plot the obs.
    if ax is None: 
        #First define the colors for the observations.
        obs_dict = dict(color='k', linestyle='-',marker='*', linewidth=1.2, markersize=6.)
        if plot_dict is not None:
            #Whatever is not defined in the yaml file is filled in with the obs_dict here.
            plot_kwargs = {**obs_dict, **plot_dict}
        else:
            plot_kwargs = obs_dict
        # create the figure
        if fig_dict is not None:
            f,ax = plt.subplots(**fig_dict)    
        else: 
            f,ax = plt.subplots(figsize=(10,6))
        # plot the line
    else:
        plot_kwargs = { **dict(linestyle='-', marker='*', linewidth=1.2, markersize=6.), **plot_dict}
    time = df.index
    df_plot_group = df.groupby(time.hour)
    df_plot = df_plot_group.median(numeric_only=True)
    ax = df_plot[column].plot(ax=ax, legend=True, **plot_kwargs) 
    shading_range = kwargs.get("shading_range", "IQR")
    if shading_range is not None:
        if shading_range not in ["IQR", "std", "total_range"]:
            raise ValueError (
                f"shading_range = {shading_range}. IQR, std or total_range expected."
            )
        if "IQR" == shading_range:
            df_max = df_plot_group.quantile(q=0.75, numeric_only=True)
            df_min = df_plot_group.quantile(q=0.25, numeric_only=True)
        elif "std" == shading_range:
            std = df_plot_group.std(numeric_only=True)
            df_max = df_plot + std
            df_min = df_plot - std
        elif "total_range" == shading_range:
            df_max = df_plot_group.max(numeric_only=True)
            df_min = df_plot_group.min(numeric_only=True)
        ax.fill_between(x=df_plot.index, y1=df_max[column], y2=df_min[column], color=ax.get_lines()[-1].get_color(), alpha=0.3)

    
    #Set parameters for all plots
    ax.set_ylabel(ylabel,fontweight='bold',**text_kwargs)
    ax.set_xlabel("Hour",fontweight='bold',**text_kwargs)
    ax.legend(frameon=False,fontsize=text_kwargs['fontsize']*0.8)
    ax.tick_params(axis='both',length=10.0,direction='inout')
    ax.tick_params(axis='both',which='minor',length=5.0,direction='out')
    ax.legend(frameon=False,fontsize=text_kwargs['fontsize']*0.8,
              bbox_to_anchor=(1.0, 0.9), loc='center left')
    if domain_type is not None and domain_name is not None:
        if domain_type == 'epa_region':
            ax.set_title('EPA Region ' + domain_name,fontweight='bold',**text_kwargs)
        else:
            ax.set_title(domain_name,fontweight='bold',**text_kwargs)
    return ax


def make_taylor(df, df_reg=None, column_o=None, label_o='Obs', column_m=None, label_m='Model', 
                dia=None, ylabel=None, ty_scale=1.5,
                domain_type=None, domain_name=None,
                plot_dict=None, fig_dict=None, text_dict=None,debug=False):
    """Creates taylor plot. Note sometimes model values are off the scale 
    on this plot. This will be fixed soon.
    
    Parameters
    ----------
    df : pandas.DataFrame
        model/obs paired data to plot
    df_reg : pandas.DataFrame
        model/obs paired regulatory data to plot
    column_o : str
        Column label of observational variable to plot
    label_o : str
        Name of observational variable to use in plot legend
    column_m : str
        Column label of model variable to plot
    label_m : str
        Name of model variable to use in plot legend 
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
    #First define items for all plots
    if debug is False:
        plt.ioff()
        
    #set default text size
    def_text = dict(fontsize=14.0)
    if text_dict is not None:
        text_kwargs = {**def_text, **text_dict}
    else:
        text_kwargs = def_text
    # set ylabel to column if not specified.
    if ylabel is None:
        ylabel = column_o
    #Then, if no plot has been created yet, create a plot and plot the first pair.

    if dia is None:
        # create the figure
        if fig_dict is not None:
            f = plt.figure(**fig_dict)
        else:
            f = plt.figure(figsize=(12,10))
        sns.set_style('ticks')
        # plot the line
        if df_reg is not None:
            dia = td(df_reg[column_o+'_reg'].std(), scale=ty_scale, fig=f,
                               rect=111, label=label_o)
            plt.grid(linewidth=1, alpha=.5)
            cc = corrcoef(df_reg[column_o+'_reg'].values, df_reg[column_m+'_reg'].values)[0, 1]
            dia.add_sample(df_reg[column_m+'_reg'].std(), cc, zorder=9, label=label_m, **plot_dict)
        else:
            dia = td(df[column_o].std(), scale=ty_scale, fig=f,
                               rect=111, label=label_o)
            plt.grid(linewidth=1, alpha=.5)
            cc = corrcoef(df[column_o].values, df[column_m].values)[0, 1]
            dia.add_sample(df[column_m].std(), cc, zorder=9, label=label_m, **plot_dict)

    else:
        # If plot has been created add to the current axes.
        if df_reg is not None:
            # this means that an axis handle already exists and use it to plot another model
            cc = corrcoef(df_reg[column_o+'_reg'].values, df_reg[column_m+'_reg'].values)[0, 1]
            dia.add_sample(df_reg[column_m+'_reg'].std(), cc, zorder=9, label=label_m, **plot_dict)
        else:
            cc = corrcoef(df[column_o].values, df[column_m].values)[0, 1]
            dia.add_sample(df[column_m].std(), cc, zorder=9, label=label_m, **plot_dict)

    #Set parameters for all plots
    contours = dia.add_contours(colors='0.5')
    plt.clabel(contours, inline=1, fontsize=text_kwargs['fontsize']*0.8)
    plt.grid(alpha=.5)
    plt.legend(frameon=False,fontsize=text_kwargs['fontsize']*0.8,
               bbox_to_anchor=(0.75, 0.93), loc='center left')
    if domain_type is not None and domain_name is not None:
        if domain_type == 'epa_region':
            plt.title('EPA Region ' + domain_name,fontweight='bold',**text_kwargs)
        else:
            plt.title(domain_name,fontweight='bold',**text_kwargs)
    ax = plt.gca()
    ax.axis["left"].label.set_text('Standard Deviation: '+ylabel)
    ax.axis["top"].label.set_text('Correlation')
    ax.axis["left"].label.set_fontsize(text_kwargs['fontsize'])
    ax.axis["top"].label.set_fontsize(text_kwargs['fontsize'])
    ax.axis["left"].label.set_fontweight('bold')
    ax.axis["top"].label.set_fontweight('bold')
    ax.axis["top"].major_ticklabels.set_fontsize(text_kwargs['fontsize']*0.8)
    ax.axis["left"].major_ticklabels.set_fontsize(text_kwargs['fontsize']*0.8)
    ax.axis["right"].major_ticklabels.set_fontsize(text_kwargs['fontsize']*0.8)
    return dia

def make_spatial_overlay(df, vmodel, column_o=None, label_o=None, column_m=None, 
                      label_m=None, ylabel = None, vmin=None,
                      vmax = None, nlevels = None, proj = None, outname = 'plot', 
                      domain_type=None, domain_name=None, fig_dict=None, 
                      text_dict=None,debug=False):
        
    """Creates spatial overlay plot. 
    
    Parameters
    ----------
    df : dataframe
        model/obs pair data to plot
    vmodel: dataarray
        slice of model data to plot
    column_o : str
        Column label of observation variable to plot
    label_o : str
        Name of observation variable to use in plot title 
    column_m : str
        Column label of model variable to plot
    label_m : str
        Name of model variable to use in plot title
    ylabel : str
        Title of colorbar axis
    vmin : real number
        Min value to use on colorbar axis
    vmax : real number
        Max value to use on colorbar axis
    nlevels: integer
        Number of levels used in colorbar axis
    proj: cartopy projection
        cartopy projection to use in plot
    outname : str
        file location and name of plot (do not include .png)
    domain_type : str
        Domain type specified in input yaml file
    domain_name : str
        Domain name specified in input yaml file
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
        spatial overlay plot
        
    """
    if debug is False:
        plt.ioff()
        
    def_map = dict(states=True,figsize=[15, 8])
    if fig_dict is not None:
        map_kwargs = {**def_map, **fig_dict}
    else:
        map_kwargs = def_map
  
    #set default text size
    def_text = dict(fontsize=20)
    if text_dict is not None:
        text_kwargs = {**def_text, **text_dict}
    else:
        text_kwargs = def_text
        
    # set ylabel to column if not specified.
    if ylabel is None:
        ylabel = column_o
    
    #Take the mean for each siteid
    df_mean=df.groupby(['siteid'],as_index=False).mean(numeric_only=True)
    
    #Take the mean over time for the model output
    vmodel_mean = vmodel[column_m].mean(dim='time').squeeze()
    
    #Determine the domain
    if domain_type == 'all' and domain_name == 'CONUS':
        latmin= 25.0
        lonmin=-130.0
        latmax= 50.0
        lonmax=-60.0
        title_add = domain_name + ': '
    elif domain_type == 'epa_region' and domain_name is not None:
        latmin,lonmin,latmax,lonmax,acro = get_epa_bounds(index=None,acronym=domain_name)
        title_add = 'EPA Region ' + domain_name + ': '
    elif domain_type.startswith('custom:') or domain_type.startswith('auto-region:'):
        valid_data = vmodel.notnull()
        lons = vmodel.longitude.where(valid_data)
        lats = vmodel.latitude.where(valid_data)
        latmin, lonmin, latmax, lonmax = lats.min(), lons.min(), lats.max(), lons.max()
        title_add = domain_name + ': '
    else:
        latmin= math.floor(min(df.latitude))
        lonmin= math.floor(min(df.longitude))
        latmax= math.ceil(max(df.latitude))
        lonmax= math.ceil(max(df.longitude))
        title_add = domain_name + ': '
    
    #Map the model output first.
    cbar_kwargs = dict(aspect=15,shrink=.8)
    
    #Add options that this could be included in the fig_kwargs in yaml file too.
    if 'extent' not in map_kwargs:
        map_kwargs['extent'] = [lonmin,lonmax,latmin,latmax] 
    if 'crs' not in map_kwargs:
        map_kwargs['crs'] = proj
    
    #With pcolormesh, a Warning shows because nearest interpolation may not work for non-monotonically increasing regions.
    #Because I do not want to pull in the edges of the lat lon for every model I switch to contourf.
    #First determine colorbar, so can use the same for both contourf and scatter
    if vmin is None and vmax is None:
        vmin = np.min((vmodel_mean.quantile(0.01), df_mean[column_o].quantile(0.01)))
        vmax = np.max((vmodel_mean.quantile(0.99), df_mean[column_o].quantile(0.99)))
        
    if nlevels is None:
        nlevels = 21
    
    clevel = np.linspace(vmin,vmax,nlevels)
    cmap = plt.get_cmap('Spectral_r',nlevels-1)
    norm = mpl.colors.BoundaryNorm(clevel, ncolors=cmap.N, clip=False)
        
    # For unstructured grid, we need a more advanced plotting code
    # Call an external function (Plot_2D)
    if vmodel.attrs.get('mio_has_unstructured_grid',False):
        from .Plot_2D import Plot_2D
        
        fig = plt.figure( figsize=fig_dict['figsize'] )
        ax = fig.add_subplot(1,1,1,projection=proj)
        
        _ = Plot_2D( vmodel_mean, scrip_file=vmodel.mio_scrip_file, cmap=cmap, #colorticks=clevel, colorlabels=clevel,
                       cmin=vmin, cmax=vmax, lon_range=[lonmin,lonmax], lat_range=[latmin,latmax],
                       ax=ax, state=fig_dict['states'] )
    else:
        #I add extend='both' here because the colorbar is setup to plot the values outside the range
        ax = vmodel_mean.monet.quick_contourf(cbar_kwargs=cbar_kwargs, figsize=map_kwargs['figsize'], map_kws=map_kwargs,
                                    robust=True, norm=norm, cmap=cmap, levels=clevel, extend='both') 
    
    
    plt.gcf().canvas.draw() 
    plt.tight_layout(pad=0)
    plt.title(title_add + label_o + ' overlaid on ' + label_m,fontweight='bold',**text_kwargs)
     
    ax.axes.scatter(df_mean.longitude.values, df_mean.latitude.values,s=30,c=df_mean[column_o], 
                    transform=ccrs.PlateCarree(), edgecolor='b', linewidth=.50, norm=norm, 
                    cmap=cmap)
    ax.axes.set_extent(map_kwargs['extent'],crs=ccrs.PlateCarree())    
    
    #Uncomment these lines if you update above just to verify colorbars are identical.
    #Also specify plot above scatter = ax.axes.scatter etc.
    #cbar = ax.figure.get_axes()[1] 
    #plt.colorbar(scatter,ax=ax)
    
    #Update colorbar
    # Call below only for structured grid cases
    if not vmodel.attrs.get('mio_has_unstructured_grid',False):
        f = plt.gcf()
        model_ax = f.get_axes()[0]
        cax = f.get_axes()[1]
        #get the position of the plot axis and use this to rescale nicely the color bar to the height of the plot.
        position_m = model_ax.get_position()
        position_c = cax.get_position()
        cax.set_position([position_c.x0, position_m.y0, position_c.x1 - position_c.x0, (position_m.y1-position_m.y0)*1.1])
        cax.set_ylabel(ylabel,fontweight='bold',**text_kwargs)
        cax.tick_params(labelsize=text_kwargs['fontsize']*0.8,length=10.0,width=2.0,grid_linewidth=2.0)    
    
    #plt.tight_layout(pad=0)
    savefig(outname + '.png', loc=4, logo_height=100, dpi=150)
    return ax
    

def calculate_boxplot(df, df_reg=None, column=None, label=None, plot_dict=None, comb_bx = None, label_bx = None):
    """Combines data into acceptable format for box-plot

    Parameters
    ----------
    df : pandas.DataFrame
        model/obs paired data to plot
    df_reg : pandas.DataFrame
        model/obs paired regulatory data to plot
    column : str
        Column label of variable to plot
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
        #First define the colors for the observations.
        obs_dict = dict(color='gray', linestyle='-',marker='x', linewidth=1.2, markersize=6.)
        if plot_dict is not None:
            #Whatever is not defined in the yaml file is filled in with the obs_dict here.
            plot_kwargs = {**obs_dict, **plot_dict}
        else:
            plot_kwargs = obs_dict
    else:
        plot_kwargs = plot_dict
    #For all, a column to the dataframe and append the label info to the list.
    plot_kwargs['column'] = column
    plot_kwargs['label'] = label
    if df_reg is not None:
        comb_bx[label] = df_reg[column+'_reg']
    else:
        comb_bx[label] = df[column]
    label_bx.append(plot_kwargs)

    return comb_bx, label_bx

def calculate_slr(df, df_reg=None, column=None, label=None, plot_dict=None, obs_x = None, mod_y = None, label_x = None, label_y = None):
    """Puts df in an acceptable format for SLR calculations
    """

def calculate_multi_boxplot(df, df_reg=None, region_name= None,column=None, label=None, plot_dict=None, comb_bx = None, label_bx = None): 
    """Combines data into acceptable format for box-plot
    
    Parameters
    ----------
    df : pandas.DataFrame
        model/obs paired data to plot
    df_reg : pandas.DataFrame
        model/obs paired regulatory data to plot
    region_name : list of str
        user input regions of interets to plot
    column : str
        Column label of variable to plot
    label : str
        Name of variable to use in plot legend
    comb_bx : dataframe
        dataframe containing information to create box-plot from previous 
        occurrence so can overlay multiple model results on plot
    label_bx : list
        list of string labels to use in box-plot from previous occurrence so 
        can overlay multiple model results on plot
    Returns
    -------
    dataframe, list, dataframe           
        dataframe containing information to create box-plot
        list of string labels to use in box-plot
        dataframe containing information for regions to help create multi-box-plot
        
    """
    region_bx = pd.DataFrame()
    df_reg_epa = pd.DataFrame()
    df_short =  pd.DataFrame()

    if comb_bx is None and label_bx is None:
        comb_bx = pd.DataFrame()
        label_bx = [] 
        #First define the colors for the observations.
        obs_dict = dict(color='gray', linestyle='-',marker='x', linewidth=1.2, markersize=6.)
        if plot_dict is not None:
            #Whatever is not defined in the yaml file is filled in with the obs_dict here.
            plot_kwargs = {**obs_dict, **plot_dict}
        else:
            plot_kwargs = obs_dict
    else:
        plot_kwargs = plot_dict
    #For all, a column to the dataframe and append the label info to the list.
    plot_kwargs['column'] = column
    plot_kwargs['label'] = label
    if df_reg is not None:
        comb_bx[label] = df_reg[column+'_reg']

        df_short = df[['siteid','epa_region']].drop_duplicates()
        df_reg_epa = df_reg.merge(df_short[['siteid','epa_region']],how='left',on='siteid')
        region_bx['set_regions'] = df_reg_epa["epa_region"]

    else:
        comb_bx[label] = df[column] 
        region_bx['set_regions']=df[region_name[0]]   
    label_bx.append(plot_kwargs)
    
    return comb_bx, label_bx,region_bx             


def make_boxplot(comb_bx, label_bx, ylabel = None, vmin = None, vmax = None, outname='plot',
                 domain_type=None, domain_name=None,
                 plot_dict=None, fig_dict=None,text_dict=None,debug=False, set_stat_sig=False):

    """Creates box-plot. 

    Parameters
    ----------
    comb_bx: dataframe
        dataframe containing information to create box-plot from 
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
    if debug is False:
        plt.ioff()
    #First define items for all plots
    #set default text size
    def_text = dict(fontsize=14)
    if text_dict is not None:
        text_kwargs = {**def_text, **text_dict}
    else:
        text_kwargs = def_text
    # set ylabel to column if not specified.
    if ylabel is None:
        ylabel = label_bx[0]['column']

    #Fix the order and palette colors
    order_box = []
    pal = {}
    for i in range(len(label_bx)):
        order_box.append(label_bx[i]['label'])
        pal[label_bx[i]['label']] = label_bx[i]['color']

    #Make plot
    if fig_dict is not None:
        f,ax = plt.subplots(**fig_dict)
    else:
        f,ax = plt.subplots(figsize=(8,8))
    #Define characteristics of boxplot.
    boxprops = {'edgecolor': 'k', 'linewidth': 1.5}
    lineprops = {'color': 'k', 'linewidth': 1.5}
    boxplot_kwargs = {'boxprops': boxprops, 'medianprops': lineprops,
                  'whiskerprops': lineprops, 'capprops': lineprops,
                  'fliersize' : 2.0,
                  'flierprops': dict(marker='*',
                                     markerfacecolor='blue',
                                     markeredgecolor='none',
                                     markersize = 6.0),
                  'width': 0.75, 'palette': pal,
                  'order': order_box,
                  'showmeans': True,
                  'meanprops': {'marker': ".", 'markerfacecolor': 'black',
                                'markeredgecolor': 'black',
                               'markersize': 20.0}}
    sns.set_style("whitegrid")
    sns.set_style("ticks")
    sns.boxplot(ax=ax,x="variable", y="value",data=pd.melt(comb_bx), hue="variable", **boxplot_kwargs)
    ax.set_xlabel('')
    ax.set_ylabel(ylabel,fontweight='bold',**text_kwargs)
    ax.tick_params(labelsize=text_kwargs['fontsize']*0.8)

    if set_stat_sig is not None:
        # statistical significance of the means 
        p_values = []
        
        pairs = [(g1, g2) for i, g1 in enumerate(order_box) for g2 in order_box[i+1:]]
    
        for g1, g2 in pairs: 
            vals1 = pd.melt(comb_bx)[pd.melt(comb_bx)["variable"] == g1]["value"]
            vals2 = pd.melt(comb_bx)[pd.melt(comb_bx)["variable"] == g2]["value"]
           # print(vals1)
           # print(vals2)
            stat, p = ttest_ind(vals1, vals2) #Calculate the T-test for the means of two independent samples of scores.
            p_values.append(p)
            print(p_values)
        
        # add *, **, and *** 
        ax = plt.gca()
        annotator = Annotator(ax, pairs, data=pd.melt(comb_bx), x='variable', y='value', order=order_box)
        # for more than 2 violin plots/boxplots, you can use pairs = [] to specify how the stat sig test is done.
        
        annotator.configure(test=None, text_format='star', loc='inside', verbose=2, line_offset_to_group=-0.15, fontsize = text_kwargs["fontsize"]) 
        annotator.set_pvalues_and_annotate(p_values) 
    
    if domain_type is not None and domain_name is not None:
        if domain_type == 'epa_region':
            ax.set_title('EPA Region ' + domain_name,fontweight='bold',**text_kwargs)
        else:
            ax.set_title(domain_name,fontweight='bold',**text_kwargs)
    if vmin is not None and vmax is not None:
        ax.set_ylim(ymin = vmin, ymax = vmax)

    plt.tight_layout()
    savefig(outname + '.png', loc=4, logo_height=100)
  
def make_multi_boxplot(comb_bx, label_bx,region_bx,region_list = None, model_name_list=None,ylabel = None, vmin = None, vmax = None, outname='plot',  
                       domain_type=None, domain_name=None,
                       plot_dict=None, fig_dict=None,text_dict=None,debug=False):
    
    """Creates box-plot. 
    
    Parameters
    ----------
    comb_bx : dataframe
        dataframe containing information to create box-plot from 
        calculate_boxplot
    label_bx : list
        list of string labels to use in box-plot from calculate_boxplot
    region_bx : dataframe
        dataframe containing information of stations to help create multi-box-plot
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
    if debug is False:
        plt.ioff()
    #First define items for all plots
    #set default text size
    def_text = dict(fontsize=14)
    if text_dict is not None:
        text_kwargs = {**def_text, **text_dict}
    else:
        text_kwargs = def_text
    # set ylabel to column if not specified.
    if ylabel is None:
        ylabel = label_bx[0]['column']
    
    #Fix the order and palette colors
    order_box = []
    pal = {}
    for i in range(len(label_bx)):
        order_box.append(label_bx[i]['label'])
        pal[label_bx[i]['label']] = label_bx[i]['color']
    #Use model_name_list names instead if we have
    if model_name_list is None:
        model_name_list = order_box
    else:
        for old_label, new_label in zip(order_box, model_name_list):
            pal[new_label] = pal.pop(old_label)
        order_box = model_name_list

    #Make plot
    if fig_dict is not None:
        f,ax = plt.subplots(**fig_dict)    
    else: 
        f,ax = plt.subplots(figsize=(8,8))
    #Define characteristics of boxplot.
    boxprops = {'edgecolor': 'k', 'linewidth': 1.5}
    lineprops = {'color': 'k', 'linewidth': 1.5}
    boxplot_kwargs = {'boxprops': boxprops, 'medianprops': lineprops,
                  'whiskerprops': lineprops, 'capprops': lineprops,
                  'fliersize' : 2.0, 
                  'flierprops': dict(marker='*', 
                                     markerfacecolor='blue', 
                                     markeredgecolor='none',
                                     markersize = 6.0),
                  'width': 0.75, 'palette': pal,
                  'hue_order': order_box,
                  'showmeans': True, 
                  'meanprops': {'marker': ".", 'markerfacecolor': 'black', 
                                'markeredgecolor': 'black',
                               'markersize': 20.0}}
    sns.set_style("whitegrid")
    sns.set_style("ticks")
    len_combx = len(comb_bx.columns)
    
    data_obs = comb_bx[comb_bx.columns[0]].to_frame().rename({comb_bx.columns[0]:'Value'},axis=1)
    data_obs['model'] = model_name_list[0]
    data_obs['Regions'] = region_bx['set_regions'].values
    to_concat = []
    to_concat.append(data_obs[['Value','model','Regions']])

    for i in range(1,len_combx):
        data_model = comb_bx[comb_bx.columns[i]].to_frame().rename({comb_bx.columns[i]:'Value'},axis=1)
        data_model['model'] = model_name_list[i]
        data_model['Regions'] = region_bx['set_regions'].values
        to_concat.append(data_model[['Value','model','Regions']])

    tdf =pd.concat(to_concat)
    acro = region_list
    sns.boxplot(x='Regions',y='Value',hue='model',data=tdf.loc[tdf.Regions.isin(acro)],order=acro,showfliers=False,**boxplot_kwargs)
    ax.set_xlabel('')
    ax.set_ylabel(ylabel,fontweight='bold',**text_kwargs)
    ax.tick_params(labelsize=text_kwargs['fontsize']*0.8)
    plt.legend(fontsize=text_kwargs['fontsize']*0.8)
    if domain_type is not None and domain_name is not None:
        if domain_type == 'epa_region':
            ax.set_title('EPA Region ' + domain_name,fontweight='bold',**text_kwargs)
        else:
            ax.set_title(domain_name,fontweight='bold',**text_kwargs)
    if vmin is not None and vmax is not None:
        ax.set_ylim(ymin = vmin, ymax = vmax)

    plt.tight_layout()
    savefig(outname + '.png', loc=4, logo_height=100)


def scorecard_step1_combine_df(df, df_reg=None, region_name=None, urban_rural_name=None,column=None, label=None, plot_dict=None, comb_bx = None, label_bx = None):
    """Combines data into acceptable format for box-plot

    Parameters
    ----------
    df : pandas.DataFrame
        model/obs paired data to plot
    df_reg : pandas.DataFrame
        model/obs paired regulatory data to plot
    column : str
        Column label of variable to plot
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
    dataframe, list, dataframe  
        dataframe containing information to create box-plot
        list of string labels to use in box-plot
        dataframe containing information for regions to help create multi-box-plot

    """
    region_bx = pd.DataFrame()                   
    msa_bx = pd.DataFrame()                      
    time_bx = pd.DataFrame()               
    if comb_bx is None and label_bx is None:
        comb_bx = pd.DataFrame()
        label_bx = []
        #First define the colors for the observations.
        obs_dict = dict(color='gray', linestyle='-',marker='x', linewidth=1.2, markersize=6.)
        if plot_dict is not None:
            #Whatever is not defined in the yaml file is filled in with the obs_dict here.
            plot_kwargs = {**obs_dict, **plot_dict}
        else:
            plot_kwargs = obs_dict
    else:
        plot_kwargs = plot_dict

    #For all, a column to the dataframe and append the label info to the list.
    plot_kwargs['column'] = column
    plot_kwargs['label'] = label
    if df_reg is not None:
        comb_bx[label] = df_reg[column+'_reg']
    else:
        comb_bx[label] = df[column]
        region_bx['set_regions']=df[region_name[0]]                
        msa_bx['set_urban_rural'] = df[urban_rural_name[0]]            
        time_bx['set_time'] = df['time']                                 
   
    label_bx.append(plot_kwargs)
    return comb_bx, label_bx,region_bx,msa_bx,time_bx            

def scorecard_step2_prepare_individual_df(comb_bx,region_bx,msa_bx,time_bx,model_name_list=None): 

    # len_combx = len(comb_bx.columns)
    data_obs = comb_bx[comb_bx.columns[0]].to_frame().rename({comb_bx.columns[0]:'Value'},axis=1)
    data_model1 = comb_bx[comb_bx.columns[1]].to_frame().rename({comb_bx.columns[1]:'Value'},axis=1)
    data_model2 = comb_bx[comb_bx.columns[2]].to_frame().rename({comb_bx.columns[2]:'Value'},axis=1)

    data_obs['model']    = model_name_list[0]
    data_model1['model'] = model_name_list[1]
    data_model2['model'] = model_name_list[2]

    data_obs['Regions'] = region_bx['set_regions'].values
    data_model1['Regions'] = region_bx['set_regions'].values
    data_model2['Regions'] = region_bx['set_regions'].values

    data_obs['urban_rural'] = msa_bx['set_urban_rural'].values
    data_model1['urban_rural'] = msa_bx['set_urban_rural'].values
    data_model2['urban_rural'] = msa_bx['set_urban_rural'].values

    data_obs['Time'] = time_bx['set_time'].values
    data_model1['Time'] = time_bx['set_time'].values
    data_model2['Time'] = time_bx['set_time'].values

    output_obs = data_obs.to_xarray().groupby('Regions')        
    output_model1 = data_model1.to_xarray().groupby('Regions')  
    output_model2 = data_model2.to_xarray().groupby('Regions') 

    return output_obs, output_model1, output_model2

def GetDateList(start_time_input,end_time_input):
    from datetime import datetime, timedelta

    start_date_str = str(start_time_input).split(' ')[0]
    end_date_str = str(end_time_input).split(' ')[0]
    FMT='%Y-%m-%d'
    start_date = datetime.strptime(start_date_str,FMT)
    end_date = datetime.strptime(end_date_str,FMT)
    datelist_output = []
    for i in range(10000):
        date_here = start_date + timedelta(days=i)
        date_here_str = str(date_here).split(' ')[0]
        if date_here <= end_date:
           datelist_output.append(date_here_str)
        else:
            break
    return datelist_output

def scorecard_step3_getLUC(region_name_input,ds_name,urban_rural_differentiate_value):
    msa_here = ds_name[region_name_input]['urban_rural']   #len is (time*#site)
    msa_here_array = np.array(msa_here).reshape((1,len(msa_here)))
 
    rural_index_list = []
    urban_index_list = []
    for i in range(len(msa_here_array[0])):
        if msa_here_array[0][i] == urban_rural_differentiate_value:    
            rural_index_list.append(i)
        else:
            urban_index_list.append(i)
    return rural_index_list, urban_index_list

def scorecard_step4_GetRegionLUCDate(ds_name=None,region_list=None,datelist=None,urban_rural_differentiate_value=None):
    from datetime import datetime

    Region_Date_Urban_list = [] #(region * date)
    Region_Date_Rural_list = [] #(region * date)

    for region in region_list:  #region == 'R1'
        region_here = ds_name[region] #ds1_new['R1'] ~(time*#site)
     
        #get urban/rural index for this region
        rural_index_list_here = scorecard_step3_getLUC(region,ds_name,urban_rural_differentiate_value)[0]

        #get by date split
        Date_Urban_List = []
        Date_Rural_List = []
        for date in datelist:
            date_start_here = datetime.strptime(date+' 00:00:00','%Y-%m-%d %H:%M:%S')
            date_end_here   = datetime.strptime(date+' 23:59:59','%Y-%m-%d %H:%M:%S')
       
            region_date_rural_here = []
            region_date_urban_here = []
            for i in range(len(region_here['Time'])):
                date_here1 = region_here['Time'].values[i]
                timestamp = ((date_here1 - np.datetime64('1970-01-01T00:00:00'))/ np.timedelta64(1, 's'))
                date_here = datetime.utcfromtimestamp(timestamp)  #this function== 1970,1,1 + timestamp(in seconds)
                if date_here >= date_start_here and date_here <= date_end_here:
                    if i in rural_index_list_here:
                        region_date_rural_here.append(region_here['Value'][i])
                    else:
                        region_date_urban_here.append(region_here['Value'][i])

            region_date_rural_here_array = np.array(region_date_rural_here).reshape((1,len(region_date_rural_here)))    
            region_date_urban_here_array = np.array(region_date_urban_here).reshape((1,len(region_date_urban_here))) 

            Date_Urban_List.append(region_date_urban_here_array)  # all date pm2.5
            Date_Rural_List.append(region_date_rural_here_array)  # all date pm2.5

        Region_Date_Urban_list.append(Date_Urban_List) # all region & data pm2.5
        Region_Date_Rural_list.append(Date_Rural_List) # all region & data pm2.5
    return Region_Date_Urban_list, Region_Date_Rural_list

def scorecard_step5_KickNan(obs_input=None,model_input_1=None,model_input_2=None):
    OBS_Region_Date_list_noNan = []
    MODEL1_Region_Date_list_noNan = [] #(region, date)
    MODEL2_Region_Date_list_noNan = []
    for kk in range(len(obs_input)):
        OBS_Region_Date_list_noNan_Date = []
        MODEL1_Region_Date_list_noNan_Date = []
        MODEL2_Region_Date_list_noNan_Date = []

        for jj in range(len(obs_input[kk])):
            obs_here_array = obs_input[kk][jj]
            model1_here_array = model_input_1[kk][jj]
            model2_here_array = model_input_2[kk][jj]

            obs_output = []
            model1_output = []
            model2_output = []
            for i in range(len(obs_here_array[0])):
                if math.isnan(float(obs_here_array[0][i])) is False:
                    if math.isnan(float(model1_here_array[0][i])) is False:
                        obs_output.append(obs_here_array[0][i])
                        model1_output.append(model1_here_array[0][i])
                        model2_output.append(model2_here_array[0][i])

            OBS_Region_Date_list_noNan_Date.append(obs_output)
            MODEL1_Region_Date_list_noNan_Date.append(model1_output)
            MODEL2_Region_Date_list_noNan_Date.append(model2_output)
        OBS_Region_Date_list_noNan.append(OBS_Region_Date_list_noNan_Date)
        MODEL1_Region_Date_list_noNan.append(MODEL1_Region_Date_list_noNan_Date)
        MODEL2_Region_Date_list_noNan.append(MODEL2_Region_Date_list_noNan_Date)
    return OBS_Region_Date_list_noNan,MODEL1_Region_Date_list_noNan,MODEL2_Region_Date_list_noNan

def CalcIOA(v2,v1): #v1 is observation, v2 is prediction
    ioa_num = np.sum(np.subtract(v1,v2)**2)
    ioa_det = np.sum((np.abs(np.subtract(v2,np.mean(v1))) + np.abs(np.subtract(v1,np.mean(v1))))**2)
    ioa = 1 - ioa_num/ioa_det
    return ioa  

def scorecard_step6_BetterOrWorse(obs_input=None,model1_input=None, model2_input=None,better_or_worse_method=None):
    v1 = obs_input   #AirNow OBS
    v2 = model1_input#CMAQ v5.4
    v3 = model2_input#CMAQ v5.2

    key_word = ''
    rms_test1 = math.sqrt(np.square(np.subtract(v1,v2)).mean())
    rms_test2 = math.sqrt(np.square(np.subtract(v1,v3)).mean())
    
    nmb_test1 = np.subtract(v2,v1).sum()/np.sum(v1)
    nmb_test2 = np.subtract(v3,v1).sum()/np.sum(v1)

    nme_test1 = np.sum(np.abs(np.subtract(v2,v1)))/np.sum(v1)
    nme_test2 = np.sum(np.abs(np.subtract(v3,v1)))/np.sum(v1)

    ioa_test1 = CalcIOA(v2,v1)
    ioa_test2 = CalcIOA(v3,v1)

    if better_or_worse_method == 'RMSE':
        if rms_test1 < rms_test2:
            key_word= 'better'
        elif rms_test1 > rms_test2:
            key_word = 'worse'
        else:
            key_word = 'equal'

    elif better_or_worse_method == 'IOA':
        if ioa_test1 > ioa_test2:
            key_word = 'better'
        elif ioa_test1 < ioa_test2:
            key_word = 'worse'
        else:
            key_word = 'equal'

    elif better_or_worse_method == 'NMB':
        if np.abs(nmb_test1) < np.abs(nmb_test2):
            key_word = 'better'
        elif np.abs(nmb_test1) > np.abs(nmb_test2):
            key_word = 'worse'
        else:
            key_word = 'equal'

    elif better_or_worse_method == 'NME':
        if nme_test1 < nme_test2:
            key_word = 'better'
        elif nme_test1 > nme_test2:
            key_word = 'worse'
        else:
            key_word = 'equal'
    return key_word

def scorecard_step7_SigLevel(model1_input=None,model2_input=None):
    X1=  np.array(model1_input)
    X2=  np.array(model2_input)

    #confidence interval 95% for model 1
    mean_X1 = np.mean(X1)
    STD_X1  = np.std(X1)
    lower_bd_X1_95 = mean_X1 - 1.96*(STD_X1/(len(X1))**0.5)
    upper_bd_X1_95 = mean_X1 + 1.96*(STD_X1/(len(X1))**0.5)

    #confidence interval 95% for model 2
    mean_X2 = np.mean(X2)
    STD_X2  = np.std(X2)
    lower_bd_X2_95 = mean_X2 - 1.96*(STD_X2/(len(X2))**0.5)
    upper_bd_X2_95 = mean_X2 + 1.96*(STD_X2/(len(X2))**0.5)

    #confidence interval 99% for model 1
    lower_bd_X1_99 = mean_X1 - 2.576*(STD_X1/(len(X1))**0.5)
    upper_bd_X1_99 = mean_X1 + 2.576*(STD_X1/(len(X1))**0.5)

    #confidence interval 99% for model 2
    lower_bd_X2_99 = mean_X2 - 2.576*(STD_X2/(len(X2))**0.5)
    upper_bd_X2_99 = mean_X2 + 2.576*(STD_X2/(len(X2))**0.5)

    #confidence interval 99.9% for model 1
    lower_bd_X1_999 = mean_X1 - 3.291*(STD_X1/(len(X1))**0.5)
    upper_bd_X1_999 = mean_X1 + 3.291*(STD_X1/(len(X1))**0.5)
 
    #confidence interval 99.9% for model 2
    lower_bd_X2_999 = mean_X2 - 3.291*(STD_X2/(len(X2))**0.5)
    upper_bd_X2_999 = mean_X2 + 3.291*(STD_X2/(len(X2))**0.5)

    key_word = ''
    if (upper_bd_X1_95 -lower_bd_X2_95)* (upper_bd_X2_95 -lower_bd_X1_95) >= 0:
        key_word = 'No significant difference'
    else: #NOT overlap,signidicant difference'
        if (upper_bd_X1_99 -lower_bd_X2_99)* (upper_bd_X2_99 -lower_bd_X1_99) >= 0:
            key_word = 'significant difference, with 95% confident'
        else:
            if (upper_bd_X1_999 -lower_bd_X2_999)* (upper_bd_X2_999 -lower_bd_X1_999) >= 0:
                key_word = 'significant difference, with 99% confident'
            else:
                key_word = 'significant difference, with 99.9% confident'
    return key_word

def scorecard_step8_OutputMatrix(obs_urban_input=None, model1_urban_input=None,model2_urban_input=None,
                                 obs_rural_input=None, model1_rural_input=None,model2_rural_input=None,better_or_worse_method =None):

    output_matrix = np.zeros((len(obs_urban_input)+len(obs_rural_input),len(obs_urban_input[0])))
    for i in range(len(obs_urban_input)+len(obs_rural_input)):# i is region
        for j in range(len(obs_urban_input[0])):# j is date
            if i%2 == 0: # this is urban
                model2_here = model2_urban_input[int(i/2)][j]
                model1_here = model1_urban_input[int(i/2)][j]
                OBS_here    = obs_urban_input[int(i/2)][j]
            else:   # this is rural
                model2_here = model2_rural_input[int((i-1)/2)][j]
                model1_here = model1_rural_input[int((i-1)/2)][j]
                OBS_here    = obs_rural_input[int((i-1)/2)][j]

            if OBS_here == []:
                output_matrix[i][j] = np.nan  # no values, use Nan
            else:
                key_word_BW = scorecard_step6_BetterOrWorse(OBS_here,model1_here, model2_here,better_or_worse_method)  #ORDER: airnow, cmaq_54, cmaq_52
                key_word_SL = scorecard_step7_SigLevel(model1_here, model2_here)                #ORDER: cmaq_54, cmaq_52

                if key_word_SL == 'No significant difference':
                    output_matrix[i][j] = 0   #'no significant difference'

                elif key_word_SL == 'significant difference, with 95% confident':
                    if key_word_BW == 'better':
                        output_matrix[i][j] = 20  #'95% better'
                    elif key_word_BW == 'worse':
                        output_matrix[i][j] = -20 #'95% worse'
                    else:
                        output_matrix[i][j] = 0  #'95% equal'

                elif key_word_SL == 'significant difference, with 99% confident':
                    if key_word_BW == 'better':
                        output_matrix[i][j] = 50  #'99% better'
                    elif key_word_BW == 'worse':
                        output_matrix[i][j] = -50 #'99% worse'
                    else:
                        output_matrix[i][j] = 0  #'99% equal'

                else:
                    if key_word_BW == 'better':
                        output_matrix[i][j] = 100  #'99.9% better'
                    elif key_word_BW == 'worse':
                        output_matrix[i][j] = -100 #'99.9% worse'
                    else:
                        output_matrix[i][j] = 0   #'99.9% equal'   
    return output_matrix

def scorecard_step9_makeplot(output_matrix=None,column=None,region_list=None,model_name_list=None,outname=None,
                             domain_type=None, domain_name=None, fig_dict=None,text_dict=None,datelist=None,better_or_worse_method = None):
    if fig_dict is not None:
        f,ax = plt.subplots(**fig_dict)
    else:
        f,ax = plt.subplots(figsize=(18,10))

    def_text = dict(fontsize=20)
    if text_dict is not None:
        text_kwargs = {**def_text, **text_dict}
    else:
        text_kwargs = def_text

    #set title and x,y-labels
    ax.set_xlabel('')
    ax.set_ylabel('Regions',**text_kwargs)  
    ax.set_title(column+' '+ model_name_list[1]+' vs. '+model_name_list[2]+' Evaluated against '+model_name_list[0]+
                 ' OBS \n based on '+better_or_worse_method+' & Signigicant Level', fontweight='bold',**text_kwargs)  
    #add ticks
    ax.tick_params(labelsize=20) 

    x_labels = []
    for i in range(len(datelist)):
        datelist_x_label = datelist[i][-5:]
        x_labels.append(datelist_x_label)
    xtick_location_list = []
    for i in range(len(datelist)):
        xtick_location_list.append(i+0.5)
    ax.set_xticks(xtick_location_list,x_labels,rotation=70)

    y_labels =  region_list 
    yticks_location_list = []
    for i in range(len(region_list)):
        yticks_location_list.append(2*i+1)
    ax.set_yticks(yticks_location_list,y_labels)
    plt.gca().invert_yaxis()  #to verse Y axis

    #add another y-axis
    ax2=ax.secondary_yaxis('right')
    ax2.tick_params(labelsize=20) 
    y2_labels =[]
    for i in range(len(region_list)):
        y2_labels.append('urban')
        y2_labels.append('rural')
    ax2.set_yticks([i+0.5 for i in range(len(region_list)*2)],y2_labels)  

    #plot and set colorbar
    plot1= plt.pcolormesh(output_matrix,cmap='coolwarm',edgecolor='k',vmin=-100,vmax=100)
    cb = f.colorbar(plot1,ticks=[-100,-50,-20,0,20,50,100],pad=0.1)
    cb.ax.set_yticklabels(['99.9% Worse','99% Worse','95% Worse','No Significant Difference',
                           '95% Better','99% Better','99.9% Better'])
    cb.ax.tick_params(labelsize=20)

    #save figure
    plt.tight_layout()
    savefig(outname + '.png', loc=4, logo_height=100)


from monet.util.stats import scores as scores_function
def Calc_Score(score_name_input,threshold_input, model_input, obs_input):
    a,b,c,d = scores_function(obs_input,model_input,threshold_input,maxval=1.0e5)
    CSI = np.nan
    FAR = np.nan
    HR  = np.nan
    sum_1 = a+c
    sum_2 = a+b+c
    if sum_1 != 0:  #a+c != 0
        CSI = a/(a+b+c)
        FAR = c/(a+c)
        HR  = a/(a+c)
    else:           #a+c = 0
        if sum_2 != 0:  #a+b+c != 0
            CSI = a/(a+b+c)
    if score_name_input == 'Critical Success Index':
        output_score = CSI
    elif score_name_input == 'False Alarm Rate':
        output_score = FAR
    elif score_name_input == 'Hit Rate':
        output_score = HR
   
    return output_score

def Plot_CSI(column,score_name_input,threshold_list_input, comb_bx_input,plot_dict,fig_dict,text_dict,domain_type,domain_name,model_name_list,threshold_tick_style):

    CSI_output = []  #(2, threshold len)
    threshold_list = threshold_list_input
   
    obs_input = comb_bx_input[comb_bx_input.columns[0]].to_list()
    len_model = np.shape(comb_bx_input)[1]  # == 3
   
    for i in range(1,len_model):
        csi_output_model = []
        model_input = comb_bx_input[comb_bx_input.columns[i]].to_list()

        for j in range(len(threshold_list )):
            csi_here = Calc_Score(score_name_input,threshold_list[j], model_input, obs_input)
            csi_output_model.append(csi_here)

        CSI_output.append(csi_output_model)
    #set default figure size
    if fig_dict is not None:
        f,ax = plt.subplots(**fig_dict)   
    else: 
        f,ax = plt.subplots(figsize=(8,8))
    
    #set default text size
    def_text = dict(fontsize=20)
    if text_dict is not None:
        text_kwargs = {**def_text, **text_dict}
    else:
        text_kwargs = def_text

    #Make Plot
    for i in range(len(CSI_output)):
        if threshold_tick_style == 'nonlinear':
           plt.plot(range(len(threshold_list)),CSI_output[i],'-*',label=model_name_list[i])
        else:
           plt.plot(threshold_list,CSI_output[i],'-*',label=model_name_list[i])
        ax.set_xlabel('Threshold',fontsize = text_kwargs['fontsize']*0.8)
        ax.set_ylabel(score_name_input,fontsize = text_kwargs['fontsize']*0.8)
        ax.tick_params(labelsize=text_kwargs['fontsize']*0.8)
        plt.ylim(0,1)
        plt.legend(fontsize=text_kwargs['fontsize']*0.6)
        plt.grid()
     
    #add '>' to xticks
    if threshold_tick_style == 'nonlinear':
       threshold_string_array = [str(x) for x in threshold_list]
       labels = ['>'+item for item in threshold_string_array]
       ax.set_xticks(range(len(threshold_list)),labels=labels)
    else:
       labels = ['>'+item.get_text() for item in ax.get_xticklabels()]
       ax.set_xticklabels(labels)

    if domain_type is not None and domain_name is not None:
        if domain_type == 'epa_region':
            ax.set_title(column+' EPA Region ' + domain_name,fontweight='bold',**text_kwargs)
        else:
            ax.set_title(column+' '+domain_name,fontweight='bold',**text_kwargs)
 


def make_spatial_bias_exceedance(df, column_o=None, label_o=None, column_m=None,
                      label_m=None, ylabel = None,  vdiff=None,
                      outname = 'plot',
                      domain_type=None, domain_name=None, fig_dict=None,
                      text_dict=None,debug=False):

    """Creates surface spatial bias plot. 
    
    Parameters
    ----------
    df : pandas.DataFrame
        model/obs paired data to plot
    column_o : str
        Column label of observation variable to plot
    label_o : str
        Name of observation variable to use in plot title 
    column_m : str
        Column label of model variable to plot
    label_m : str
        Name of model variable to use in plot title
    ylabel : str
        Title of colorbar axis
    vdiff : float
        Min and max value to use on colorbar axis
    outname : str
        file location and name of plot (do not include .png)
    domain_type : str
        Domain type specified in input yaml file
    domain_name : str
        Domain name specified in input yaml file
    fig_dict : dict
        Dictionary containing information about figure
    text_dict : dict
        Dictionary containing information about text
    debug : bool
        Whether to plot interactively (True) or not (False). Flag for 
        submitting jobs to supercomputer turn off interactive mode.
        
    Returns
    -------
    plot 
        surface bias plot
    """
    if debug is False:
        plt.ioff()

    def_map = dict(states=True,figsize=[10, 5])
    if fig_dict is not None:
        map_kwargs = {**def_map, **fig_dict}
    else:
        map_kwargs = def_map

    #If not specified use the PlateCarree projection
    if 'crs' not in map_kwargs:
        map_kwargs['crs'] = ccrs.PlateCarree()

    #set default text size
    def_text = dict(fontsize=20)
    if text_dict is not None:
        text_kwargs = {**def_text, **text_dict}
    else:
        text_kwargs = def_text

    # set ylabel to column if not specified.
    if ylabel is None:
        ylabel = column_o

    # calculate exceedance
    if column_o == 'OZONE_reg':
        df_mean=df.groupby(['siteid'],as_index=False).quantile(0.95, numeric_only=True) #concentrations not used in plotting, get the correct format for plotting
        # get the exceedance days for each site
        df_counto = df[df[column_o]> 70.].groupby(['siteid'],as_index=False)[column_o].count()
        df_countm = df[df[column_m]> 70.].groupby(['siteid'],as_index=False)[column_m].count()     
        ylabel2 = 'O3'  
 
    elif column_o == 'PM2.5_reg':
        df_mean=df.groupby(['siteid'],as_index=False).mean(numeric_only=True) #concentrations not used in plotting, get the correct format for plotting
        # get the exceedance days for each site
        df_counto = df[df[column_o]> 35.].groupby(['siteid'],as_index=False)[column_o].count()
        df_countm = df[df[column_m]> 35.].groupby(['siteid'],as_index=False)[column_m].count()
        ylabel2 = 'PM2.5'

    else:
        print('Error: unable to calculate exceedance for '+column_o)

    # combine dataframes
    df_combine = df_counto.set_index(['siteid']).join(df_countm.set_index(['siteid']),on=(['siteid']),how='outer').reset_index()
    df_combine[column_o]=df_combine[column_o].fillna(0)
    df_combine[column_m]=df_combine[column_m].fillna(0)
    
    # get the format correct in df_reg for the plotting 
    df_reg = (
        df_mean.merge(df_combine, on='siteid')
        .rename(index=str, columns={column_o+'_y': column_o+'_day', column_m+'_y': column_m+'_day'})
        .reset_index(drop=True)
    )

    if not df_reg.empty:
        #Specify val_max = vdiff. the sp_scatter_bias plot in MONET only uses the val_max value
        #and then uses -1*val_max value for the minimum.
        ax = monet.plots.sp_scatter_bias(
            df_reg, col1=column_o+'_day', col2=column_m+'_day', map_kwargs=map_kwargs,val_max=vdiff,
            cmap="OrangeBlue", edgecolor='k',linewidth=.8)

        if domain_type == 'all' and domain_name == 'CONUS':
            latmin= 25.0
            lonmin=-130.0
            latmax= 50.0
            lonmax=-60.0
            plt.title(domain_name + ': ' + label_m + ' - ' + label_o,fontweight='bold',**text_kwargs)
        elif domain_type == 'epa_region' and domain_name is not None:
            latmin,lonmin,latmax,lonmax,acro = get_epa_bounds(index=None,acronym=domain_name)
            plt.title('EPA Region ' + domain_name + ': ' + label_m + ' - ' + label_o,fontweight='bold',**text_kwargs)
        else:
            latmin= math.floor(min(df.latitude))
            lonmin= math.floor(min(df.longitude))
            latmax= math.ceil(max(df.latitude))
            lonmax= math.ceil(max(df.longitude))
            plt.title(domain_name + ': ' + label_m + ' - ' + label_o,fontweight='bold',**text_kwargs)

        if 'extent' not in map_kwargs:
            map_kwargs['extent'] = [lonmin,lonmax,latmin,latmax]
        ax.axes.set_extent(map_kwargs['extent'],crs=ccrs.PlateCarree())

        #Update colorbar
        f = plt.gcf()
        model_ax = f.get_axes()[0]
        cax = f.get_axes()[1]
        #get the position of the plot axis and use this to rescale nicely the color bar to the height of the plot.
        position_m = model_ax.get_position()
        position_c = cax.get_position()
        cax.set_position([position_c.x0, position_m.y0, position_c.x1 - position_c.x0, (position_m.y1-position_m.y0)*1.1])
        cax.set_ylabel(ylabel2+ ' exceedance days',fontweight='bold',**text_kwargs)
        cax.tick_params(labelsize=text_kwargs['fontsize']*0.8,length=10.0,width=2.0,grid_linewidth=2.0)

        #plt.tight_layout(pad=0)
        savefig(outname + '_exceedance.png', loc=4, logo_height=120)
    else:
        print('No exceedance found!')


