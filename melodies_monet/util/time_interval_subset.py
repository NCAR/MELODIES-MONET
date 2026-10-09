# SPDX-License-Identifier: Apache-2.0
#
def subset_model_filelist(all_files,timeformat,timestep,timeinterval):
    '''Subset model filelist to within a given time interval. 
    Filename requirements:
    - individual files for each timestep
    - time must be in filename
    '''
    import pandas as pd
    subset_interval = pd.date_range(start=timeinterval[0],end=timeinterval[-1],freq=timestep)
    interval_files = []
    for i in subset_interval:
        flst = [fs for fs in all_files if i.strftime(timeformat) in fs]
        if len(flst) == 1:
            interval_files.append(flst[0])
        elif len(flst) >1:
            print('More than 1 file for {} in listing'.format(i.strftime(timeformat)))
    return interval_files

def subset_OMPS_l2(file_path,timeinterval):
    '''Dependent on filenaming convention
     OMPS-satelliteid_NMTO3-L2_version_startingtimestamp_orbitnumber_endingtimestamp.h5
    '''
    import pandas as pd
    from glob import glob
    import fnmatch
    all_files = glob(file_path)
    interval_files = []
    subset_interval = pd.date_range(start=timeinterval[0],end=timeinterval[-1],freq='D',inclusive='left')
    
    for i in subset_interval:
        fst = fnmatch.filter(all_files,'*OMPS-*_NMTO3-L2_v*_{}*_o*'.format(i.strftime('%Ym%m%d')))
        fst.sort()
        for j in fst:
            interval_files.append(j)
    return interval_files

def subset_mopitt_l3(file_path,timeinterval):
    '''Dependent on filenaming conventions
    MOP03J-YYYYMMDD-
    MOP03JM-201909-
    '''
    import pandas as pd
    from glob import glob
    import fnmatch
    all_files = glob(file_path)
    interval_files = []
    if 'MOP03JM-' in all_files[0]:
        subset_interval = pd.date_range(start=timeinterval[0],end=timeinterval[-1],freq='M')
        strfmt = '%Y%m'
    else:
        subset_interval = pd.date_range(start=timeinterval[0],end=timeinterval[-1],freq='D')
        strfmt = '%Y%m%d'
    for i in subset_interval:
        fst = fnmatch.filter(all_files,'*MOP*-{}*'.format(i.strftime(strfmt)))
        fst.sort()
        for j in fst:
            interval_files.append(j)
    return interval_files

def subset_MODIS_l2(file_path,timeinterval):
    """Subset MODIS L2 files to a specified time interval.

    Filters files based on the timestamp encoded in MODIS filenames
    using hourly granularity. Files are matched using the pattern
    ``'*M?D04_L2.A{YYYYDDD.HH}*.hdf'``.

    Parameters
    ----------
    file_path : str
        Glob pattern for MODIS HDF files
        (e.g., ``'/data/MODIS/MOD04_L2.*.hdf'``).
    timeinterval : list of pandas.Timestamp
        ``[start, end]`` time bounds.

    Returns
    -------
    list of str
        File paths within the time interval.

    Notes
    -----
    Filename convention::

        MOD04_L2.AYYYYDDD.HHMM.collection.timestamp.hdf
        MYD04_L2.AYYYYDDD.HHMM.collection.timestamp.hdf
    """
    import pandas as pd
    from glob import glob
    import fnmatch
    all_files = glob(file_path)
    interval_files = []
    subset_interval = pd.date_range(start=timeinterval[0],end=timeinterval[-1],freq='h',inclusive='left')

    for i in subset_interval:
        fst = fnmatch.filter(all_files,'*M?D04_L2.A{}*.hdf'.format(i.strftime('%Y%j.%H')))
        fst.sort()
        for j in fst:
            interval_files.append(j)
    return interval_files

