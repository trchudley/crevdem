"""
This module contains the functions necessary to open the ArcticDEM/REMA strip as an 
xarray DataArray suitable for further processing by `crevdem`. 
"""

import os
from typing import Optional, Literal
from warnings import warn

import rioxarray as rxr

from xarray import DataArray

from ._utils import clip


def load_local(
    dem_fpath: str,
    bounds: Optional[tuple] = None,
    bitmask_fpath: Optional[str] = None,
) -> DataArray:
    """NOTE: THIS FUNCTION IS DEPRECATED. USE `pdemtools` TO DOWNLOAD ARCTICDEM/REMA
    STRIP DATA INSTEAD.

    Loads the desired ArcticDEM/REMA DEM strip, from local filepaths, as an xarray
    DataArray suitable for further processing by `crevdem`. Option to filter to bounds
    and bitmask.

    :param dem_fpath: Filepath of DEM strip
    :type dem_fpath: str
    :param bounds: Clip to bounds [xmin, ymin, xmax, ymax], in EPSG:3413 (ArcticDEM) or
        EPSG:3031 (REMA), defaults to None
    :type bounds: tuple, optional
    :param bitmask_fpath: Path to *_bitmask.tif file used to mask the DEM, defaults to None
    :type bitmask_fpath: str, optional

    :returns: xarray DataArray of DEM strip suitable for onward processing by `crevdem`
        package
    :rtype: DataArray
    """

    warn(
        "The `load` module and assocaited functions are deprecated and will be removed in a "
        "future version. Please use the `pdemtools` package to download ArcticDEM and REMA "
        "strips instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    # Open dataarray using rioxarray
    dem = rxr.open_rasterio(dem_fpath)

    # Clip if requested, or get whole bounds if not
    if bounds is not None:
        dem = clip(dem, bounds)
    else:
        bounds = dem.rio.bounds()

    # Filter -9999.0 values
    dem = dem.where(dem > -9999.0)

    # Mask using bitmask if requested
    if bitmask_fpath is not None:
        mask = rxr.open_rasterio(bitmask_fpath)
        if bounds is not None:
            mask = clip(mask, bounds)
        dem = dem.where(mask == 0)
        del mask

    # Remove `band` dim
    dem = dem.squeeze(drop=True)

    return dem


def load_aws(
    dataset: Literal["arcticdem", "rema"],
    geocell: str,
    dem_id: str,
    bounds: Optional[tuple] = None,
    bitmask: Optional[bool] = True,
    bucket: Optional[str] = "https://pgc-opendata-dems.s3.us-west-2.amazonaws.com",
    version: Optional[str] = "s2s041",
    preview: Optional[bool] = False,
) -> DataArray:
    """NOTE: THIS FUNCTION IS DEPRECATED. USE `pdemtools` TO DOWNLOAD ARCTICDEM/REMA
    STRIP DATA INSTEAD.

    Returns the selected ArcticDEM/REMA strip, downloaded from the relevant AWS
    bucket, as an xarray DataArray suitable for further processing by `crevdem`. Option
    to filter to bounds and bitmask. 2 m DEM strips are large in size and loading
    remotely from AWS may take some time.

    :param dataset: Either 'arcticdem' or 'rema'. Case-sensitive.
    :type dataset: str
    :param geocell: Geographic grouping of ArcticDEM / REMA strip. e.g. 'n70w051'.
    :type geocell: str
    :param dem_id: ArcticDEM/REMA strip ID. e.g.
        'SETSM_s2s041_WV01_20200709_102001009A689B00_102001009B63B200_2m_lsf_seg2'
    :type dem_id: str
    :param bounds: Clip to bounds [xmin, ymin, xmax, ymax], in EPSG:3413 (ArcticDEM) or
        EPSG:3031 (REMA), defaults to None
    :type bounds: tuple, optional
    :param bitmask: Choose whether apply the associated mask, defaults to True
    :type bitmask: str
    :param bucket: AWS buck link, defaults to
        'https://pgc-opendata-dems.s3.us-west-2.amazonaws.com'
    :type bucket: str
    :param version: Version string, defaults to 's2s041'
    :type version: str
    :param preview: Return just a link to the STAC preview page, defaults to False
    :type preview: bool, optional

    :return: xarray DataArray of DEM strip suitable for onward processing by `crevdem`
        package
    :retype: DataArray
    """

    warn(
        "The `load` module and associated functions are deprecated and will be removed in a "
        "future version. Please use the `pdemtools` package to download ArcticDEM and REMA "
        "strips instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    if preview == True:
        browser_prefix = "https://polargeospatialcenter.github.io/stac-browser/#/external/pgc-opendata-dems.s3.us-west-2.amazonaws.com"
        preview_fpath = os.path.join(
            browser_prefix, dataset, "strips", version, "2m", geocell, f"{dem_id}.json"
        )
        return preview_fpath

    # Construct DEM fpath
    dem_fpath = os.path.join(
        bucket, dataset, "strips", version, "2m", geocell, f"{dem_id}_dem.tif"
    )

    # Construct bitmask fpath, if required
    if bitmask == True:
        bitmask_fpath = os.path.join(
            bucket, dataset, "strips", version, "2m", geocell, f"{dem_id}_bitmask.tif"
        )
    else:
        bitmask_fpath = None

    # Pass AWS URL locations to load_local command
    return load_local(
        dem_fpath,
        bounds,
        bitmask_fpath,
    )
