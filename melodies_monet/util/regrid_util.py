# SPDX-License-Identifier: Apache-2.0
#
"""
file: regrid_util.py

MM regridding utilities 

1. **Config-driven xESMF regridder** (:func:`setup_regridder`,
   :func:`filename_regrid`): builds xESMF regridders from the analysis
   YAML's ``regrid`` blocks. Used by the structured obs/model regridding
   path in the driver.
   
2. **Model-agnostic regridder** (:func:`regrid`): a single entry point
   that dispatches on method to one of two backends:

   - **ckdtree** (``nearest_s2d`` / ``nearest_d2s`` / ``radius_mean``):
     point sampling of an unstructured source at arbitrary target points
     via a cached :class:`scipy.spatial.cKDTree`. Fast; does NOT conserve
     mass. 
     
   - **xregrid** (``conservative`` / ``bilinear`` / ``patch``): true
     area-weighted (or interpolated) regridding via ESMF. Conservative
     conserves mass. Unstructured sources (e.g. ne0CONUS) are read from a
     SCRIP mesh whose padded/degenerate corners are depadded into a clean
     UGRID first (see
     :func:`melodies_monet.util.uxarray_util.clean_uxgrid_from_scrip`).

Usage of :func:`regrid`
-----------------------
Nearest-neighbor sample of an unstructured model at swath pixels:

>>> from melodies_monet.util.regrid_util import regrid
>>> out = regrid(
...     modobj,
...     target={"lon": obs["lon"].values, "lat": obs["lat"].values},
...     method="nearest_s2d",
...     target_dims=("x", "y"),
... )

Conservative (mass-preserving) regrid of an unstructured model to a
rectilinear grid:

>>> out = regrid(
...     modobj,
...     target={"lon": np.arange(-130, -60, 0.1), "lat": np.arange(20, 55, 0.1)},
...     method="conservative",
...     src_grid="/path/to/ne0CONUS_ne30x8_np4_SCRIP.nc",
... )

"""

import os
import gc
import xarray as xr
import numpy as np
try:
    import uxarray as ux
except ImportError:  # optional dep
    ux = None
try:
    from xregrid import Regridder
except ImportError:  # optional dep
    Regridder = None

_LON_NAMES = ("longitude", "lon", "Longitude")
_LAT_NAMES = ("latitude", "lat", "Latitude")

_CKDTREE_METHODS = ("nearest_s2d", "nearest_d2s", "radius_mean")
_XREGRID_METHODS = ("conservative", "conservative_normed", "bilinear", "patch")

# One-shot notice flag for the xregrid weight-row-sum workaround.
_COVERAGE_NOTICE_SHOWN = False

# Optional Dask-parallel xregrid weight generation (env-gated, default OFF so
# existing runs are unchanged).
_XREGRID_PARALLEL = os.environ.get("MM_XREGRID_PARALLEL", "").strip().lower() in (
    "1", "on", "true", "yes")
_XREGRID_CLIENT = None

def _patch_ux_isel_slices():
    """Teach UxDataset.isel to accept slice indexers (idempotent).

    xregrid's parallel weight generation chunks the source grid with
    ``ds.isel(n_face=slice(a, b))``; uxarray's Grid.isel only takes explicit
    index arrays (``_slice_face_indices`` does ``np.asarray(indices, int)`` ->
    "TypeError: int() argument ... not 'slice'"). Expand any slice indexer to
    ``np.arange`` before delegating to the original isel.
    """
    if getattr(ux.UxDataset.isel, "_mm_slice_ok", False):
        return
    _orig_isel = ux.UxDataset.isel

    def _isel_slices_ok(self, indexers=None, **kwargs):
        merged = dict(indexers or {}); merged.update(kwargs)
        for dim, idx in list(merged.items()):
            if isinstance(idx, slice) and dim in self.sizes:
                merged[dim] = np.arange(*idx.indices(self.sizes[dim]))
        return _orig_isel(self, **merged)

    _isel_slices_ok._mm_slice_ok = True
    ux.UxDataset.isel = _isel_slices_ok
    
def _ensure_xregrid_client():
    """Lazily create (once per process) a right-sized dask.distributed client for
    xregrid's parallel weight generation. No-op / None if parallel is off or dask
    is unavailable (xregrid then just runs serial)."""
    global _XREGRID_CLIENT
    if not _XREGRID_PARALLEL:
        return None
    _patch_ux_isel_slices()          # main process (xregrid chunks source here)
    if _XREGRID_CLIENT is not None:
        return _XREGRID_CLIENT
    try:
        import dask.distributed as dd
    except ImportError:
        print("regrid: MM_XREGRID_PARALLEL set but dask.distributed is missing; "
              "running serial.", flush=True)
        return None
    try:
        _XREGRID_CLIENT = dd.get_client()                 # reuse existing client
    except ValueError:
        n = int(os.environ.get("MM_XREGRID_WORKERS",
                os.environ.get("PBS_NCPUS", os.environ.get("NCPUS", "4"))))
        cluster = dd.LocalCluster(n_workers=n, threads_per_worker=1, processes=True)
        _XREGRID_CLIENT = dd.Client(cluster)
        print(f"regrid: dask LocalCluster with {n} workers for xregrid parallel "
              "weight generation.", flush=True)
    try:
        # workers may also isel shipped UxDatasets -- patch them too
        _XREGRID_CLIENT.run(_patch_ux_isel_slices)
    except Exception:
        pass
    return _XREGRID_CLIENT

def _release_esmf(rg):
    """Best-effort release of ESMF-side memory held by an xregrid Regridder.

    ESMF (esmpy) allocates meshes/routehandles in a Fortran heap that Python's
    GC does NOT reclaim when the Regridder goes out of scope. In the TEMPO
    pairing loop a new Regridder is built per granule per direction (forward
    and backward), each constructing ESMF meshes for the 174k-face model and
    ~270k-cell swath -- so without explicit destruction the process leaks
    hundreds of MB per granule (observed: 150+ GB over a multi-day run).

    We try every destroy hook xregrid/esmpy might expose, drop the heavy
    attributes (sparse weight matrices), then force a GC pass.
    """
    if rg is None:
        return

    def _safe_get(obj, name):
        try:
            return getattr(obj, name, None)
        except Exception:
            return None

    # Destroy ESMF objects the Regridder may hold (names vary across versions).
    objs = [rg, _safe_get(rg, "regrid"), _safe_get(rg, "_regrid"),
            _safe_get(rg, "esmf_regrid")]
    for obj in objs:
        if obj is None:
            continue
        for attr in ("destroy", "_destroy", "free", "release"):
            fn = _safe_get(obj, attr)
            if callable(fn):
                try:
                    fn()
                except Exception:
                    pass
    # Drop heavy cached arrays by clearing the INSTANCE dict directly
    inst = getattr(rg, "__dict__", {})
    for attr in ("_weights_matrix", "_total_weights", "_regrid", "regrid",
                 "esmf_regrid"):
        if attr in inst:
            try:
                inst[attr] = None
            except Exception:
                pass
    del rg
    gc.collect()

# ==========================================================================
# Config-driven xESMF regridder (structured obs/model path)
# ==========================================================================

def setup_regridder(config, config_group='obs', target_grid=None):
    """
    Setup regridder for observations or model

    Parameters
        config (dict): configuration dictionary

    Returns
        regridder (dict of xe.Regridder): dictionary of regridder instances
    """
    try:
        import xesmf as xe
    except ImportError:
        print('regrid_util: xesmf module not found')
        raise

    print('setup_regridder.target_grid')
    print(target_grid)

    if target_grid is not None:
        ds_target = target_grid
    else:
        target_file = os.path.expandvars(config['analysis']['target_grid'])
        ds_target = xr.open_dataset(target_file)

    regridder_dict = dict()

    for name in config[config_group]:
        base_file = os.path.expandvars(config[config_group][name]['regrid']['base_grid'])
        ds_base = xr.open_dataset(base_file)
        method = config[config_group][name]['regrid']['method']
        regridder = xe.Regridder(ds_base, ds_target, method)
        regridder_dict[name] = regridder

    return regridder_dict


def filename_regrid(filename, regridder):
    """
    Construct modified filename for regridded dataset

    Parameters
        filename (str): filename of dataset
        regridder (xe.Regridder): regridder instance

    Returns
        filename_regrid (str): filename of regridded dataset
    """
    filename_regrid = filename.replace('.nc', '_regrid.nc')

    return filename_regrid

# ==========================================================================
# Model-agnostic regridder (dispatches to ckdtree or xregrid)
# ==========================================================================

def regrid(
    src,
    target = None,
    method="nearest_s2d",
    src_lon=None,
    src_lat=None,
    src_grid=None,
    target_grid=None,
    target_dims=None,
    max_distance=None,
    radius=None,
    backend="auto",
):
    """Model-agnostic regrid dispatcher.

    - **ckdtree** (``nearest_s2d`` / ``nearest_d2s`` / ``radius_mean``):
      point sampling. ``target`` is scattered points; no cell geometry
      needed. Does NOT conserve mass.
      
    - **xregrid** (``conservative`` / ``bilinear`` / ``patch``): true
      area-weighted (or interpolated) regridding via ESMF. Requires the
      source's mesh (``src_grid``) and a target that defines cells. The
      conservative method **conserves mass**.

    Parameters
    ----------
    src : xr.Dataset or ux.UxDataset
        Source data. For ckdtree: must carry 1-D longitude/latitude coords
        on its column dim. For xregrid: either a UxDataset, or a plain
        Dataset whose column dim length matches the ``src_grid`` mesh.
    target : dict
        Target spec, ``{"lon": ..., "lat": ...}``.

        - ckdtree: lon/lat are point arrays of identical shape.
        - xregrid: lon/lat are **1-D** coordinate axes of a rectilinear
          grid (lengths may differ). Cell bounds are inferred by xregrid.
    method : str, default "nearest_s2d"
        See backend list above.
    src_lon, src_lat : str, optional
        Names of source longitude/latitude coords (ckdtree only).
        Auto-detected if not given.
    src_grid : str or uxarray.Grid, optional
        Source mesh for unstructured xregrid sources: a SCRIP path (depadded
        into a clean UGRID via
        :func:`melodies_monet.util.uxarray_util.clean_uxgrid_from_scrip`) or a
        pre-built ``uxarray.Grid``. Required for conservative/bilinear unless
        ``src`` is already a UxDataset.
    target_grid : uxarray.Grid, optional
        Unstructured **target** mesh (xregrid only). Use this for a curvilinear
        target like a TEMPO swath: build a ``uxarray.Grid`` from the pixel
        corner bounds (see
        :func:`melodies_monet.util.uxarray_util.uxgrid_from_corner_bounds`)
        and pass it here. Output lands on that grid's ``n_face`` dim. When
        given, ``target`` is ignored.
    target_dims : tuple of str, optional
        Output spatial dim names (ckdtree only).
    max_distance : float, optional
        Nearest-neighbor distance cap, degrees (ckdtree nearest only).
    radius : float, optional
        Averaging radius, degrees (ckdtree ``radius_mean`` only).
    backend : str, default "auto"
        ``"auto"`` picks ckdtree for nearest/radius methods and xregrid
        for conservative/bilinear. Force with ``"ckdtree"`` / ``"xregrid"``.

    Returns
    -------
    xr.Dataset
        Source data on the target grid.
    """
    
    if backend == "auto":
        if method in _CKDTREE_METHODS:
            backend = "ckdtree"
        elif method in _XREGRID_METHODS:
            backend = "xregrid"
        else:
            raise NotImplementedError(
                f"regrid: unknown method {method!r}. ckdtree: {_CKDTREE_METHODS}; "
                f"xregrid: {_XREGRID_METHODS}."
            )

    if backend == "ckdtree":
        src_lon = _resolve_coord_name(src, src_lon, _LON_NAMES, "longitude")
        src_lat = _resolve_coord_name(src, src_lat, _LAT_NAMES, "latitude")
        if not isinstance(target, dict) or "lon" not in target or "lat" not in target:
            raise TypeError(
                "regrid: target must be a dict with 'lon' and 'lat' array-likes. "
                f"Got: {type(target).__name__}"
            )
        tlon = np.asarray(target["lon"])
        tlat = np.asarray(target["lat"])
        if tlon.shape != tlat.shape:
            raise ValueError(
                f"regrid: target lon shape {tlon.shape} != lat shape {tlat.shape}"
            )
        return _regrid_ckdtree(
            src, src_lon, src_lat, tlon, tlat, target_dims,
            method=method, max_distance=max_distance, radius=radius,
        )

    if backend == "xregrid":
        return _regrid_xregrid(
            src, target, method, src_grid=src_grid, target_grid=target_grid,
        )

    raise NotImplementedError(
        f"regrid: backend={backend!r} not implemented. "
        "Available: 'ckdtree', 'xregrid'."
    )

def _as_src_uxds(src, src_grid):
    """Resolve a source to a UxDataset (clean uxgrid + data on n_face)."""
    import uxarray as ux

    if hasattr(src, "uxgrid") and src_grid is None:
        return src

    if src_grid is None:
        raise ValueError(
            "regrid (xregrid backend): conservative/bilinear on an "
            "unstructured source needs src_grid=<SCRIP path or uxarray.Grid>, "
            "or pass a UxDataset as src."
        )
    if isinstance(src_grid, str):
        from melodies_monet.util.uxarray_util import open_uxgrid
        uxgrid = open_uxgrid(src_grid)
    else:
        uxgrid = src_grid  # assume a uxarray.Grid

    # Find the column dim whose length matches the mesh's n_face.
    col_dim = None
    for d, n in src.sizes.items():
        if n == uxgrid.n_face:
            col_dim = d
            break
    if col_dim is None:
        raise ValueError(
            f"regrid (xregrid backend): no src dim matches mesh n_face="
            f"{uxgrid.n_face}. src dims: {dict(src.sizes)}."
        )
    src_ds = src if hasattr(src, "data_vars") else src.to_dataset()
    if col_dim != "n_face":
        src_ds = src_ds.rename({col_dim: "n_face"})
    return ux.UxDataset(src_ds, uxgrid=uxgrid)

def _coverage_normalize(out):
    """Divide every regridded variable by the regridded ones-field.

    The installed xregrid's conservative weights row-sum to ~2 instead of 1
    (verified with two unit squares regridded onto themselves: a constant 1
    comes back as exactly 2). Sigma(w*v)/Sigma(w*1) is the correct
    area-weighted mean whatever the row scaling, so this is exact -- and a
    harmless divide-by-1.0 if/when xregrid is fixed. Cells the source does
    not reach get coverage 0/NaN and come out NaN, as they should.
    """
    global _COVERAGE_NOTICE_SHOWN
    if "_mm_cov" not in getattr(out, "data_vars", {}):
        return out
    cov = out["_mm_cov"]
    covd = cov.where(np.isfinite(cov) & (cov != 0))
    _cm = float(np.nanmean(np.asarray(covd.values, dtype=float)))
    if abs(_cm - 1.0) > 0.05 and not _COVERAGE_NOTICE_SHOWN:
        _COVERAGE_NOTICE_SHOWN = True
        print(f"regrid: xregrid weight row-sums ~{_cm:.2f} (known xregrid "
              "0.1.0 bug); coverage-normalizing every conservative regrid "
              "to a true area-weighted mean. Shown once per run.", flush=True)
    for v in out.data_vars:
        if v == "_mm_cov":
            continue
        attrs = out[v].attrs
        out[v] = out[v] / covd
        out[v].attrs = attrs
    return out.drop_vars("_mm_cov")


def _regrid_xregrid(src, target, method, src_grid=None, target_grid=None):
    """xregrid/ESMF backend for conservative & bilinear regridding.

    Source is resolved to a clean UxDataset. Target is either an
    unstructured mesh (``target_grid``, e.g. a swath built from pixel
    corner bounds) or a rectilinear grid from 1-D ``target`` lon/lat axes.
    """
    src_uxds = _as_src_uxds(src, src_grid)

    # crash and say bilinear and patch cannot work with unstructured source
    if method in ("bilinear", "patch") and hasattr(src_uxds, "uxgrid"):
        raise ValueError(
            f"regrid: method={method!r} is not supported for an unstructured "
            "(cell-data) source. ESMF bilinear/patch interpolate from mesh "
            "nodes, but the source values are on cell faces. Use "
            "'conservative' (mass-conserving) instead, or a nearest method "
            "via the ckdtree backend."
        )

    # --- Unstructured target (e.g. TEMPO swath). ---
    if target_grid is not None:
        # xregrid places output on whatever location the target carries data.
        # An EMPTY UxDataset target makes it default to NODES (n_node), which
        # is wrong for cell/face values. Seed the target with a face-located
        # placeholder so the result lands on n_face; drop it afterward.
        n_face = int(target_grid.n_face)
        tgt_uxds = ux.UxDataset(
            {"_mm_face_loc": (("n_face",), np.zeros(n_face, dtype="float32"))},
            uxgrid=target_grid,
        )
        # A caller may pre-seed its OWN "_mm_cov" ones-field when it wants
        # the raw (un-normalized) conservative sums plus the regridded
        # coverage back -- e.g. _conservative_swath2mod_scan accumulates
        # sum(raw_g)/sum(cov_g) across granules, a ratio that cancels the
        # weight row scaling by itself. In that case skip both the
        # injection and the internal normalization.
        caller_cov = "_mm_cov" in src_uxds.data_vars
        if not caller_cov:
            src_uxds["_mm_cov"] = (
                ("n_face",),
                np.ones(int(src_uxds.sizes["n_face"]), dtype="float64"),
            )
            
        try:
            _ensure_xregrid_client()
            rg = Regridder(src_uxds, tgt_uxds, method=method,
                           parallel=_XREGRID_PARALLEL)
            out = rg(src_uxds)
            
        # free memory
            out = out.compute()
            _release_esmf(rg)
        finally:
            if not caller_cov:
                del src_uxds["_mm_cov"]

        if hasattr(out, "data_vars") and "_mm_face_loc" in out.data_vars:
            out = out.drop_vars("_mm_face_loc")
        return out if caller_cov else _coverage_normalize(out)

    # --- Rectilinear target from 1-D lon/lat axes. ---
    if target is None:
        raise ValueError(
            "regrid (xregrid backend): provide either target_grid (mesh) or "
            "target={'lon': 1d, 'lat': 1d} (rectilinear)."
        )
    tlon = np.asarray(target["lon"])
    tlat = np.asarray(target["lat"])
    
    if tlon.ndim != 1 or tlat.ndim != 1:
        raise NotImplementedError(
            "regrid (xregrid backend): rectilinear target lon/lat must be 1-D "
            f"(got shapes {tlon.shape}, {tlat.shape}). For a curvilinear "
            "target, build a uxarray.Grid and pass target_grid instead."
        )
    target_ds = xr.Dataset(coords={"lon": ("lon", tlon), "lat": ("lat", tlat)})
    caller_cov = "_mm_cov" in src_uxds.data_vars
    if not caller_cov:
        src_uxds["_mm_cov"] = (
            ("n_face",), np.ones(int(src_uxds.sizes["n_face"]), dtype="float64")
        )
    try:
        _ensure_xregrid_client()
        rg = Regridder(src_uxds, target_ds, method=method, periodic=True,
                       parallel=_XREGRID_PARALLEL)
        out = rg(src_uxds).compute()
        _release_esmf(rg)
    finally:
        if not caller_cov:
            del src_uxds["_mm_cov"]
    return out if caller_cov else _coverage_normalize(out)


def _resolve_coord_name(obj, given, candidates, kind):
    """Find a coord by name. Use ``given`` if set, else first candidate present."""
    if given is not None:
        if given not in obj.variables:
            raise KeyError(
                f"regrid: requested {kind} name {given!r} not in dataset. "
                f"Available: {list(obj.variables)}"
            )
        return given
    for c in candidates:
        if c in obj.variables:
            return c
    raise KeyError(
        f"regrid: no source {kind} found. Looked for {candidates}. "
        f"Available: {list(obj.variables)}")


def _regrid_ckdtree(
    src, src_lon, src_lat, tlon, tlat, target_dims,
    method="nearest_s2d", max_distance=None, radius=None,):
    
    """cKDTree backend.

    Reuses :func:`melodies_monet.util.uxarray_util.sample_unstructured_at_points`,
    which carries the cached KDTree (the same source grid hit across many
    target queries — e.g. per-granule TEMPO loops — pays the build cost
    once).
    """
    from melodies_monet.util.uxarray_util import sample_unstructured_at_points

    # The helper hardcodes "longitude"/"latitude" internally. Rename src's
    # coords if they use a different convention; restore on exit.
    rename_in = {}
    if src_lon != "longitude":
        rename_in[src_lon] = "longitude"
    if src_lat != "latitude":
        rename_in[src_lat] = "latitude"
    src_norm = src.rename(rename_in) if rename_in else src

    target_shape = tlon.shape
    tlon_flat = tlon.ravel()
    tlat_flat = tlat.ravel()

    if method == "radius_mean":
        if radius is None:
            raise ValueError(
                "regrid: method='radius_mean' requires radius=<float deg>."
            )
        sampled = sample_unstructured_at_points(
            src_norm, tlon_flat, tlat_flat, radius=radius,
        )
    elif method in ("nearest_s2d", "nearest_d2s"):
        sampled = sample_unstructured_at_points(
            src_norm, tlon_flat, tlat_flat, max_distance=max_distance,
        )
    else:
        raise NotImplementedError(
            f"regrid (ckdtree backend): method={method!r} not supported. "
            "Use 'nearest_s2d', 'nearest_d2s', or 'radius_mean'."
        )

    # Resolve target_dims.
    if target_dims is None:
        if len(target_shape) == 1:
            target_dims = ("target",)
        else:
            target_dims = tuple(f"dim_{i}" for i in range(len(target_shape)))
    target_dims = tuple(target_dims)
    if len(target_dims) != len(target_shape):
        raise ValueError(
            f"regrid: target_dims has length {len(target_dims)} but target "
            f"shape is {target_shape}."
        )

    # Fast path: 1-D target with default name -- sample_unstructured_at_points
    # already returns exactly this shape.
    if len(target_shape) == 1 and target_dims == ("target",):
        return sampled

    # 1-D target with caller-chosen dim name: just rename.
    if len(target_shape) == 1:
        return sampled.rename({"target": target_dims[0]})

    # N-D target: reshape every var's trailing "target" axis back to
    # target_shape, then attach lon/lat as coords on the target dims.
    out = xr.Dataset(attrs=dict(sampled.attrs))
    for v in sampled.data_vars:
        da = sampled[v]
        if "target" not in da.dims:
            out[v] = da
            continue
        transposed = da.transpose(..., "target")
        arr = np.asarray(transposed.values)
        new_shape = arr.shape[:-1] + target_shape
        new_dims = transposed.dims[:-1] + target_dims
        out[v] = xr.DataArray(
            arr.reshape(new_shape), dims=new_dims, attrs=dict(da.attrs),
        )

    out = out.assign_coords({
        "longitude": (target_dims, tlon),
        "latitude": (target_dims, tlat),
    })
    return out
