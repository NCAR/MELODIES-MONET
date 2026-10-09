# SPDX-License-Identifier: Apache-2.0
#

"""
unstructured model output binding to a uxarray grid 

these util functions only run if a grid file is provided in the YAML, preserving currently existing functionality

https://uxarray.readthedocs.io/en/latest/user-guide/grid-formats.html

Users should be able to provide EXODUS, UGRID, SCRIP, etc. This util file will handle all of those types automatically. 

UGRID; MPAS; SCRIP; EXODUS; ESMF; GEOS CS; ICON; FESOM2; HEALPix

05282026: EXODUS and SCRIP are supported; if ncol = num_element uxarray should handle automatically. If no, CKDTree is triggered for nearest neighbor interpolation. 

"""

import numpy as np
try:
    import uxarray as ux
except ImportError:  # optional dep
    ux = None
import xarray as xr

# Cache clean uxgrids built from SCRIP files (keyed by path). Depadding a
# 174k-face SCRIP takes a few seconds, so build once per process.
_CLEAN_UXGRID_CACHE = {}

def to_neg180(lon):
    """Normalize longitudes to the [-180, 180] convention.

    CESM-SE (and several other models) store longitude in 0..360 while the
    satellite L2 products report -180..180; every overlap/bbox comparison
    must normalize first or a CONUS model and CONUS swath look disjoint.
    """
    return ((np.asarray(lon) + 180.0) % 360.0) - 180.0


def read_scrip_corners(grid_file):
    """Return ``(corner_lon, corner_lat)`` in degrees from a SCRIP file.

    Shape ``(n_face, n_corners)``; radians are converted if the units
    attribute says so. Raises ``KeyError`` for non-SCRIP files (e.g. MPAS
    meshes), which callers treat as "cannot subset, use the full mesh".
    """
    with xr.open_dataset(grid_file) as s:
        clat = np.asarray(s["grid_corner_lat"].values)
        clon = np.asarray(s["grid_corner_lon"].values)
        units = str(s["grid_corner_lat"].attrs.get("units", "")).lower()
    if "rad" in units:
        clat, clon = np.rad2deg(clat), np.rad2deg(clon)
    return clon, clat


def subset_mesh_to_bbox(grid_file, lon_min, lon_max, lat_min, lat_max, pad=0.5):
    """Faces of ``grid_file`` whose centers fall inside the padded bbox.

    Returns ``(keep, subgrid)``: integer indices into the full mesh's face
    dim, and a Grid rebuilt from the kept SCRIP corners with the same
    builder that made the full grid -- so ``keep`` indexes data and corners
    consistently. ``subgrid`` is ``None`` when no subset is useful: the bbox
    keeps nothing (``keep.size == 0`` -- callers usually skip) or everything
    (callers use the full mesh).
    """
    full = open_uxgrid(grid_file)
    flon, flat = _face_centers(full)
    flon = to_neg180(flon)
    keep = np.where(
        (flon >= lon_min - pad) & (flon <= lon_max + pad)
        & (flat >= lat_min - pad) & (flat <= lat_max + pad)
    )[0]
    if keep.size == 0 or keep.size >= int(full.n_face):
        return keep, None
    clon, clat = read_scrip_corners(grid_file)
    return keep, uxgrid_from_corner_bounds(clon[keep], clat[keep])


def subset_model_source(ds, grid_file, lon_min, lon_max, lat_min, lat_max,
                        pad=0.5, label="subset_model_source"):
    """Subset an unstructured model Dataset + its mesh to a bbox for regridding.

    The forward (model -> swath) conservative regrid only needs the model
    faces near the swath; building ESMF weights against the full mesh wastes
    memory (this is the OOM fix). On success returns ``(UxDataset on the
    subset mesh, None)`` ready for ``regrid(src, src_grid=None, ...)``; on
    any failure or full/zero coverage returns ``(ds, grid_file)`` unchanged
    so the caller falls back to the full mesh.
    """
    try:
        keep, subgrid = subset_mesh_to_bbox(
            grid_file, lon_min, lon_max, lat_min, lat_max, pad=pad)
        if subgrid is None:
            return ds, grid_file
        n_face_full = int(open_uxgrid(grid_file).n_face)
        col_dim = next((d for d, n in ds.sizes.items() if n == n_face_full), None)
        if col_dim is None:
            return ds, grid_file
        sub = ds if hasattr(ds, "data_vars") else ds.to_dataset()
        if col_dim != "n_face":
            sub = sub.rename({col_dim: "n_face"})
        print(f"{label}: mesh subset {n_face_full} -> {keep.size} faces",
              flush=True)
        return ux.UxDataset(sub.isel(n_face=keep), uxgrid=subgrid), None
    except Exception as e:  # noqa: BLE001
        print(f"{label}: mesh subset skipped ({e!r}); regridding full mesh.",
              flush=True)
        return ds, grid_file


def flatten_to_faces(ds, dims, drop=()):
    """Stack swath spatial dims to an unindexed ``n_face`` dim.

    Prepares swath-shaped data as an xregrid source: geometry vars in
    ``drop`` are removed, and any coord riding the stacked dim is dropped
    (xregrid copies source coords to the output, where a swath-sized coord
    collides with the model-sized output dim).
    """
    flat = (
        ds.drop_vars([v for v in drop if v in ds.variables], errors="ignore")
        .stack(n_face=dims)
        .reset_index("n_face", drop=True)
    )
    return flat.drop_vars(
        [c for c in flat.coords if "n_face" in flat[c].dims], errors="ignore")


def faces_to_grid(out, shape, dims):
    """Reshape each var's face-sized dim back to 2-D swath dims.

    Inverse of :func:`flatten_to_faces` for the regrid output: any variable
    with a dim of length ``shape[0]*shape[1]`` is reshaped (row-major, so
    flatten order must match) to ``dims``; vars without one (grid/node
    artifacts) are skipped.
    """
    n_face = int(np.prod(shape))
    res = xr.Dataset(attrs=dict(out.attrs))
    for v in out.data_vars:
        da = out[v]
        face_dim = next((d for d in da.dims if da.sizes[d] == n_face), None)
        if face_dim is None:
            continue
        t = da.transpose(..., face_dim)
        arr = np.asarray(t.values).reshape(t.shape[:-1] + tuple(shape))
        res[v] = xr.DataArray(arr, dims=t.dims[:-1] + tuple(dims),
                              attrs=dict(da.attrs))
    return res

def clean_uxgrid_from_scrip(scrip_path, fill_value=-1):
    """Build a degeneracy-free uxarray Grid from a SCRIP file.

    SCRIP stores every cell padded to ``grid_corners`` slots by *repeating*
    corners (e.g. a quad in a 10-corner array repeats one corner 6×). Those
    repeated corners are degenerate and make ESMF refuse to build
    conservative weights. This depads each face to its true polygon
    (4/6/8/10-gon for ne0CONUS dual cells) so ESMF/xregrid can do true
    area-weighted conservative regridding.

    Result is cached by ``scrip_path``.

    Parameters
    ----------
    scrip_path : str
        Path to a SCRIP-format grid file (``grid_corner_lat``/
        ``grid_corner_lon`` of shape ``(n_face, n_corners)``).
    fill_value : int
        Sentinel for unused slots in the ragged face-node connectivity.

    Returns
    -------
    uxarray.Grid
        Clean grid with variable-length ``face_node_connectivity``.
    """
    hit = _CLEAN_UXGRID_CACHE.get(scrip_path)
    if hit is not None:
        return hit

    clon, clat = read_scrip_corners(scrip_path)
    grid = uxgrid_from_corner_bounds(clon, clat, fill_value=fill_value)
    _CLEAN_UXGRID_CACHE[scrip_path] = grid
    return grid

def uxgrid_from_corner_bounds(corner_lon, corner_lat, fill_value=-1):
    """Build a degeneracy-free uxarray Grid from per-face corner bounds.

    Generalizes the SCRIP depad to any source of per-cell corner arrays —
    including a TEMPO swath whose pixel corners come from
    ``longitude_bounds``/``latitude_bounds``. Each face's repeated/padded
    corners are collapsed to its true polygon (so ESMF accepts the mesh for
    conservative regridding), and nodes shared between faces are deduped to
    a single global node list.

    NOT cached — callers with a static mesh (e.g. a model SCRIP) should
    cache the result themselves; swath grids change per granule.

    Parameters
    ----------
    corner_lon, corner_lat : array-like
        Corner coordinates in **degrees**, shape ``(n_face, n_corners)``.
        (Flatten any ``(x, y, n_corners)`` swath bounds to this first.)
    fill_value : int
        Sentinel for unused slots in the ragged face-node connectivity.

    Returns
    -------
    uxarray.Grid
        Clean grid with variable-length ``face_node_connectivity``.
    """
    
    clon = np.asarray(corner_lon, dtype=float)
    clat = np.asarray(corner_lat, dtype=float)
    if clon.shape != clat.shape or clon.ndim != 2:
        raise ValueError(
            "uxgrid_from_corner_bounds: corner_lon/corner_lat must both be "
            f"2-D (n_face, n_corners). Got {clon.shape}, {clat.shape}."
        )
    nf, mc = clon.shape

    # Global node dedup via a rounded (lon, lat) key.
    key = np.round(np.stack([clon.ravel(), clat.ravel()], axis=1), 4)
    uniq, inv = np.unique(key, axis=0, return_inverse=True)
    node_lon = uniq[:, 0].astype(float)
    node_lat = uniq[:, 1].astype(float)
    inv = inv.reshape(nf, mc)

    # Per-face consecutive dedup (corners are padded by repetition); drop a
    # closing duplicate if last kept == first.
    face_conn = np.full((nf, mc), fill_value, dtype=np.int64)
    for i in range(nf):
        row = inv[i]
        keep = [int(row[0])]
        for j in range(1, mc):
            if int(row[j]) != keep[-1]:
                keep.append(int(row[j]))
        if len(keep) > 1 and keep[-1] == keep[0]:
            keep.pop()
        face_conn[i, : len(keep)] = keep

    return ux.Grid.from_topology(
        node_lon=node_lon,
        node_lat=node_lat,
        face_node_connectivity=face_conn,
        fill_value=fill_value,
    )

def open_uxgrid(grid_file, fill_value=-1):
    """Open any unstructured grid file as a clean uxarray Grid (cached).

    Dispatches by format so callers don't care whether the model ships a
    padded SCRIP (ne0CONUS / CESM-SE) or a native mesh (MPAS):

    - **SCRIP** (has ``grid_corner_lat``/``grid_corner_lon``): the corners are
      padded to a fixed width by *repeating* nodes, which ESMF rejects for
      conservative regridding. Depad them via :func:`clean_uxgrid_from_scrip`.
    - **MPAS / UGRID / EXODUS**: uxarray reads these natively
      (``ux.open_grid``) -- clean Voronoi/polygon cells, no padding, lon/lat
      unit handling (e.g. MPAS radians) done internally. No depad needed.

    Parameters
    ----------
    grid_file : str
        Path to a SCRIP, MPAS, UGRID, or EXODUS grid/mesh file.
    fill_value : int
        Fill sentinel for the SCRIP depad path.

    Returns
    -------
    uxarray.Grid
    """
    hit = _CLEAN_UXGRID_CACHE.get(grid_file)
    if hit is not None:
        return hit

    with xr.open_dataset(grid_file) as ds:
        is_scrip = (
            "grid_corner_lat" in ds.variables
            and "grid_corner_lon" in ds.variables
        )

    if is_scrip:
        # clean_uxgrid_from_scrip caches under the same key as well.
        grid = clean_uxgrid_from_scrip(grid_file, fill_value=fill_value)
    else:
        # MPAS / UGRID / EXODUS -> uxarray auto-detects and gives clean cells.
        grid = ux.open_grid(grid_file)

    _CLEAN_UXGRID_CACHE[grid_file] = grid
    return grid

def _coord(obj, names):
    """Return ``(name, coord)`` for the first of ``names`` present on ``obj``.

    Works for both ``xarray.Dataset`` and ``xarray.DataArray``; longitude /
    latitude may live in coords or (for a Dataset) data_vars.
    """
    for name in names:
        if name in obj.coords:
            return name, obj.coords[name]
        if name in getattr(obj, "data_vars", {}):
            return name, obj[name]
    return None, None

def _spatial_dim(obj):
    """Return ``(dim_name, lon_coord_name)`` for the unstructured column dim.

    Located via the longitude coordinate, which is 1-D along the column
    dimension for unstructured (e.g. CESM-SE ``ncol``) output.
    """
    name, lon = _coord(obj, ("longitude", "lon", "Longitude"))
    if lon is None or lon.ndim != 1:
        raise ValueError(
            "Could not locate a 1-D 'longitude' coordinate to identify the "
            "unstructured spatial dimension."
        )
    return lon.dims[0], name


def _lat_name(obj):
    name, lat = _coord(obj, ("latitude", "lat", "Latitude"))
    if lat is None:
        raise ValueError("Could not locate a 'latitude' coordinate.")
    return name


def _face_centers(uxgrid):
    """Return (lon, lat) face centers.

    Uses uxarray's built-in, vectorized face-center coordinates rather than a
    Python loop over faces (much faster on large grids). Falls back to a
    connectivity-based mean only if those properties are unavailable.
    """
    try:
        return np.asarray(uxgrid.face_lon.values), np.asarray(uxgrid.face_lat.values)
    except (AttributeError, ValueError):
        face_node = uxgrid.face_node_connectivity.values
        node_lon = uxgrid.node_lon.values
        node_lat = uxgrid.node_lat.values
        masked = np.where(face_node >= 0, face_node, 0)
        valid = (face_node >= 0).astype(float)
        counts = valid.sum(axis=1)
        center_lon = (node_lon[masked] * valid).sum(axis=1) / counts
        center_lat = (node_lat[masked] * valid).sum(axis=1) / counts
        return center_lon, center_lat


def _face_for_columns(uxgrid, mlon, mlat):
    """Nearest grid face for each model column (mirrors the Plot_2D cKDTree)."""
    from scipy.spatial import cKDTree

    center_lon, center_lat = _face_centers(uxgrid)
    mlon = np.asarray(mlon)
    mlon = np.where(mlon > 180, mlon - 360, mlon)
    flon = np.where(center_lon > 180, center_lon - 360, center_lon)

    tree = cKDTree(np.column_stack([flon, center_lat]))
    _, face_for_col = tree.query(np.column_stack([mlon, np.asarray(mlat)]))
    return face_for_col


def _bin_to_faces(obj, uxgrid, spatial_dim, face_for_col):
    """Average values on ``spatial_dim`` into faces, preserving other dims.

    Faces with no column map to NaN, matching the prior Plot_2D behavior.
    Accepts a Dataset or DataArray and returns the same type with the column
    dimension replaced by ``n_face``.
    """
    n_face = uxgrid.n_face
    return (
        obj.assign_coords(_face=(spatial_dim, face_for_col))
        .groupby("_face")
        .mean(skipna=True)
        .reindex(_face=np.arange(n_face))
        .rename({"_face": "n_face"})
    )


def model_to_uxdataset(obj, grid_file):
    """Bind a model Dataset to a uxarray Grid, aligned to the grid's faces.

    Parameters
    ----------
    obj : xarray.Dataset
        Model output on an unstructured column dimension (e.g. CESM-SE
        ``ncol``) with 1-D ``longitude``/``latitude`` coordinates.
    grid_file : str
        Path to a uxarray-readable grid file (e.g. EXODUS).

    Returns
    -------
    uxarray.UxDataset
        Dataset whose spatial dimension is the grid's ``n_face`` and whose
        ordering matches the grid faces. ``obj`` is not modified.
    """
    uxgrid = ux.open_grid(grid_file)
    spatial_dim, lon_name = _spatial_dim(obj)
    lat_name = _lat_name(obj)

    if obj.sizes[spatial_dim] == uxgrid.n_face:
        aligned = obj.rename({spatial_dim: "n_face"})
    else:
        face_for_col = _face_for_columns(
            uxgrid, obj[lon_name].values, obj[lat_name].values
        )
        spatial_vars = [v for v in obj.data_vars if spatial_dim in obj[v].dims]
        aligned = _bin_to_faces(obj[spatial_vars], uxgrid, spatial_dim, face_for_col)

    return ux.UxDataset(aligned, uxgrid=uxgrid)


def uxda_from_columns(da, uxgrid):
    """Build a face-aligned :class:`uxarray.UxDataArray` from a 1-D column field.

    ``da`` is a model field on the unstructured column dimension with 1-D
    ``longitude``/``latitude`` coordinates (e.g. a time-mean CESM-SE slice,
    possibly already region-cropped). Returns a UxDataArray over the grid's
    ``n_face`` dimension, ready for uxarray plotting. ``da`` is not modified.
    """
    spatial_dim, lon_name = _spatial_dim(da)
    lat_name = _lat_name(da)
    name = da.name if da.name is not None else "_v"
    n_face = uxgrid.n_face

    if da.sizes[spatial_dim] == n_face:
        aligned = da.rename({spatial_dim: "n_face"})
        return ux.UxDataArray(aligned, uxgrid=uxgrid)

    face_for_col = _face_for_columns(
        uxgrid, da[lon_name].values, da[lat_name].values)

    if da.ndim == 1:
        values = np.asarray(da.values, dtype=float)
        fc = np.asarray(face_for_col)
        valid = ~np.isnan(values)
        face_sum = np.bincount(fc[valid], weights=values[valid], minlength=n_face)
        face_cnt = np.bincount(fc[valid], minlength=n_face)
        binned = np.where(face_cnt > 0, face_sum / np.maximum(face_cnt, 1), np.nan)
        aligned = xr.DataArray(binned, dims=["n_face"], name=name)
        
    else:
        aligned = _bin_to_faces(
            da.to_dataset(name=name), uxgrid, spatial_dim, face_for_col
        )[name]

    return ux.UxDataArray(aligned, uxgrid=uxgrid)


def sample_unstructured_at_points(
    modobj, target_lon, target_lat, max_distance=None, radius=None,):
    """Sample a model on a 1-D unstructured column dim at arbitrary
    ``(lon, lat)`` target points.

    Two aggregation modes:

    - **Nearest neighbor** (default, ``radius=None``): each target gets the
      single nearest source value. Optionally capped by ``max_distance``.
    - **Within-radius mean** (``radius=<float deg>``): each target gets the
      *mean* of all sources within ``radius`` of it. Poor-man's area-weighted
      aggregation -- use in the swath -> unstructured-model direction when
      you'd rather average all swath pixels that fall near a model cell than
      snap to the single nearest. Targets with no source in range -> NaN.

    Reusable beyond the satellite pipeline: any caller with a list of target
    points (swath pixels, AirNow stations, sondes, ...) can sample an unstructured model at those locations without xESMF.

    Parameters
    ----------
    modobj : xarray.Dataset
    Model on a 1-D unstructured column dim with 1-D ``longitude``/
    ``latitude`` coordinates.
    target_lon, target_lat : 1-D array-like
    Target points. Convention-agnostic; both sides normalized to
        ``-180..180`` before the KDTree query.
    max_distance : float, optional
        Only used when ``radius`` is None. Distance cap for nearest-neighbor;
        targets with no source within this distance NaN out.
    radius : float, optional
        If set, switches to within-radius averaging mode. Distance in
        degrees, Euclidean in lon/lat space.

    Returns
    -------
    xarray.Dataset
        Same data_vars as ``modobj`` but with the column dim replaced by a
        1-D ``target`` dim of length ``len(target_lon)``. Other dims
        (time, z, ...) and attrs are preserved.
    """

    from scipy.spatial import cKDTree

    modobj = modobj.load()
    
    mlon = np.asarray(modobj["longitude"].values)
    mlat = np.asarray(modobj["latitude"].values)
    mlon = ((mlon + 180.0) % 360.0) - 180.0

    tlon = np.asarray(target_lon, dtype=float)
    tlat = np.asarray(target_lat, dtype=float)
    tlon = ((tlon + 180.0) % 360.0) - 180.0

    # cKDTree.query rejects NaN/Inf inputs. Real swath data has them on edge
    # pixels / fill values; query only finite targets and mask the rest below.
    # valid = np.isfinite(tlon) & np.isfinite(tlat)

    svalid = np.isfinite(mlon) & np.isfinite(mlat)
    if not svalid.any():
        raise ValueError(
            "sample_unstructured_at_points: no finite source points to build "
            "the KDTree from."
        )
    src_orig_idx = np.where(svalid)[0]
    tree = cKDTree(np.column_stack([mlon[svalid], mlat[svalid]]))

    tvalid = np.isfinite(tlon) & np.isfinite(tlat)

    col_dim = modobj["longitude"].dims[0]
    n_target = tlon.shape[0]

    # === Within-radius averaging path (poor-man's area-weighted) ===
    if radius is not None:
        # Restrict the (expensive) ball query to targets inside the source
        smin_lon, smax_lon = np.nanmin(mlon[svalid]), np.nanmax(mlon[svalid])
        smin_lat, smax_lat = np.nanmin(mlat[svalid]), np.nanmax(mlat[svalid])
        inbox = (
            (tlon >= smin_lon - radius) & (tlon <= smax_lon + radius)
            & (tlat >= smin_lat - radius) & (tlat <= smax_lat + radius)
        )
        tquery = tvalid & inbox
        
        neighbor_lists = tree.query_ball_point(
            np.column_stack([tlon[tquery], tlat[tquery]]), r=radius
        )
        tvalid_pos = np.where(tquery)[0]
        out = xr.Dataset(attrs=dict(modobj.attrs))
        for v in modobj.data_vars:
            da = modobj[v]
            if col_dim not in da.dims:
                out[v] = da
                continue
            transposed = da.transpose(..., col_dim)
            arr = np.asarray(transposed.values)
            new_dims = transposed.dims[:-1] + ("target",)
            out_arr = np.full(arr.shape[:-1] + (n_target,), np.nan, dtype=float)
            for ti, neigh in zip(tvalid_pos, neighbor_lists):
                if len(neigh) == 0:
                    continue
                sources = src_orig_idx[np.asarray(neigh, dtype=np.intp)]
                with np.errstate(invalid="ignore"):
                    out_arr[..., ti] = np.nanmean(arr[..., sources], axis=-1)
            out[v] = xr.DataArray(out_arr, dims=new_dims, attrs=dict(da.attrs))
        out = out.assign_coords(
            longitude=("target", np.asarray(tlon)),
            latitude=("target", np.asarray(tlat)),
        )
        return out

    # === Nearest-neighbor path ===
    idx = np.zeros(tlon.shape[0], dtype=np.intp)
    # Track which targets actually got a real nearest source within reach.
    # Targets without one stay False and get masked to NaN below.
    paired = np.zeros(tlon.shape[0], dtype=bool)
    
    if tvalid.any():
        query_kwargs = {}
        if max_distance is not None:
            query_kwargs["distance_upper_bound"] = max_distance
        dist, idx_in_valid = tree.query(
            np.column_stack([tlon[tvalid], tlat[tvalid]]), **query_kwargs
        )
        # cKDTree returns idx == n (i.e. len(src_orig_idx)) for "no neighbor
        # within distance_upper_bound". Treat those as unpaired.
        n_src = len(src_orig_idx)
        within = idx_in_valid < n_src
        # Avoid out-of-range indexing for unpaired entries
        safe_idx = np.where(within, idx_in_valid, 0)
        idx[tvalid] = src_orig_idx[safe_idx]
        tvalid_pos = np.where(tvalid)[0]
        paired[tvalid_pos[within]] = True
    
    sampled = modobj.isel({col_dim: idx}).rename({col_dim: "target"})
    # Mask: target keeps its sampled value only if it was both (a) finite and
    # (b) within the distance cap of an actual source point. Everything else
    # NaNs out -- this is what stops the "nearest-neighbor smear" of distant
    # swath pixels across the whole CONUS grid when only a single swath is
    # available.
    keep = tvalid & paired
    if not keep.all():
        sampled = sampled.where(xr.DataArray(keep, dims=["target"]))

    return sampled


    

