"""
This module contains the functions necessary to preprocess an ArcticDEM/REMA strip 
loaded by the `load_aws()` or `load_local()` functions, to facilitate further 
processing by `crevdem`. 
"""

from typing import Optional

import numpy as np
from xarray import DataArray
from cv2 import GaussianBlur

from ._utils import get_resolution, geospatial_match
from .datasets import get_grimp_mask, get_bedmachine_geoid


def detrend(
    dem: DataArray,
    gauss_std_m: float,
    gauss_cutoff: Optional[float] = 1,
    resolution: Optional[float] = None,
) -> DataArray:
    """Returns a detrended DEM DataArray using a large gaussian filter. Standard
    deviation size should be >> the features of interest (in the default `crevdem`
    settings, the gauss_std_m is 200).

    :param dem: xarray of DEM with 'dem' attribute
    :type dem: DataArray
    :param gauss_std_m: standard deviation of the Gaussian filter in metres
    :type gauss_std_m: float, optional
    :param gauss_cutoff: Truncate the gaussian kernel at this many standard deviations,
        defaults to 1
    :type gauss_cutoff: float, optional
    :param resolution: Resolution of DEM strip, defaults to None
    :type resolution: float, optional

    :returns: Detrended DEM as DataArray.
    :rtype: DataArray
    """

    # Get resolution if not provided
    if resolution == None:
        resolution = get_resolution(dem)

    # Get standard deviation in pixel size
    gauss_std_px = int(np.round(gauss_std_m / resolution))

    # Get kernel size
    ksize = int(np.round(gauss_std_px * gauss_cutoff))
    if ksize % 2 == 0:  # kernel size needs to be odd
        ksize += 1

    # perform gaussian blur, add to dataset
    dem_detrend = GaussianBlur(dem.values, (ksize, ksize), gauss_std_px)

    dem_detrended = dem - dem_detrend

    return dem_detrended


def geoid_correct(
    dem: DataArray,
    bedmachine_fpath: Optional[str] = None,
    geoid: Optional[DataArray] = None,
) -> DataArray:
    """Returns a geoid-corrected DEM. Can provide either your own geoid (as a
    DataArray) using the `geoid` variable, or the filepath to an appropriate BedMachine
    dataset using the `bedmachine_fpath` variable.

    :param dem: DEM as xarray DataArray
    :type dem: DataArray
    :param bedmachine_fpath: Filepath to BedMachine dataset, mutually exclusive with
        `geoid`, defaults to None
    :type bedmachine_fpath: str
    :param geoid: Geoid as xarray DataArray, mutually exclusive with `bedmachine_fpath`,
    :type geoid: DataArray

    :returns: Geoid-corrected DEM DataArray
    :rtype: DataArray
    """

    if (bedmachine_fpath == None) and (geoid == None):
        raise ValueError("One of `bedmachine_fpath` or `geoid` must be provided")

    elif (bedmachine_fpath != None) and (geoid != None):
        raise ValueError("Only one of `bedmachine_fpath` or `geoid` can be provided")

    elif (bedmachine_fpath != None) and (geoid == None):
        geoid = get_bedmachine_geoid(bedmachine_fpath, dem)

    elif (bedmachine_fpath == None) and (geoid != None):
        # if not the same size, align geoid
        if not geospatial_match(dem, geoid):
            geoid = geoid.rio.reproject_match(dem, Resampling.bilinear)

    else:
        pass

    return dem - geoid


def mask_bedrock(
    dem: DataArray,
    grimp_mask_dir: Optional[str] = None,
    mask: Optional[DataArray] = None,
) -> DataArray:
    """Returns a bedrock-masked DEM. Can either provide your own mask (as a DataArray)
    using the `mask` variable (where bedrock = 0/False and ice/ocean = 1/True), or
    provide the path to a directory containing the GrIMP 15 m classification mask using
    the `grimp_mask_dir` variable.

    :param dem: DEM as xarray DataArray
    :type dem: DataArray
    :param grimp_mask_dir: Filepath of directory containing the 15 m GrIMP ice mask,
        mutually exclusive with `mask`.
    :type grimp_mask_dir: str, optional
    :param mask: Mask as xarray DataArray, where land = 0/False and ice/ocean = 1/True.
        Mutually exclusive with `grimp_mask_dir`,
    :type geoid: DataArray, optional

    :returns: Masked DEM DataArray
    :rtype: DataArray
    """

    if (grimp_mask_dir == None) and (mask == None):
        raise ValueError("One of `grimp_mask_dir` or `mask` must be provided")

    elif (grimp_mask_dir != None) and (mask != None):
        raise ValueError("Only one of `grimp_mask_dir` or `mask` can be provided")

    elif (grimp_mask_dir != None) and (mask == None):
        mask = get_grimp_mask(
            grimp_mask_dir,
            dem,
            ice_val=1,
            ocean_val=1,
            land_val=0,
        )
    elif (grimp_mask_dir == None) and (mask != None):
        # if not the same size, align geoid
        if not geospatial_match(dem, mask):
            mask = mask.rio.reproject_match(dem, Resampling.nearest)
    else:
        pass

    return dem.where(mask == 1)


def mask_melange(
    dem: DataArray,
    resolution: Optional[float] = None,
    candidate_height_thresh_m: Optional[float] = 10,
    candidate_area_thresh_km2: Optional[float] = 1,
    near_sealevel_thresh_m: Optional[float] = 5,
) -> DataArray:
    """Returns a DEM with mélange/ocean regions, as identified by `get_melange_mask()`
    function, filtered out. If no likely sea level is identified, returns the original
    DEM. DEM must be geoid-corrected.

    :param dem: Geoid-corrected DEM as xarray DataArray
    :type dem: DataArray
    :param resolution: Resolution of DEM strip, defaults to None
    :type resolution: float, optional
    :param candidate_height_thresh_m: Maximum value relative to geoid to be considered
        as SL, in m, defaults to 10
    :type candidate_height_thresh_m: float
    :param candidate_area_thresh_km2: Minimum area beneath `candidate_height_thresh_m`
        to be considered for sea level assessment, in km^2, defaults to 1
    :type candidate_area_thresh_km2: float
    :param near_sealevel_thresh_m: Filter out regions below this value, in metres above
        sea level, defaults to 5
    :type near_sealevel_thresh_m: float

    :returns: Filtered DEM as xarray DataArray
    :rtype: DataArray
    """

    # Get resolution if not provided
    if resolution == None:
        resolution = get_resolution(dem)

    mask = get_melange_mask(
        dem,
        resolution,
        candidate_height_thresh_m,
        candidate_area_thresh_km2,
        near_sealevel_thresh_m,
    )

    if mask is None:
        return dem.dem
    else:
        return dem.where(mask)


def get_melange_mask(
    dem: DataArray,
    resolution: Optional[float] = None,
    candidate_height_thresh_m: float = 10,
    candidate_area_thresh_km2: float = 1,
    near_sealevel_thresh_m: float = 5,
) -> DataArray:
    """Returns a mask of mélange/ocean regions of a DEM, using sea level as returned by
    the `get_sea_level()` function. DEM must be geoid-corrected. In returned mask,
    land/ice is True and ocean is False.

    :param dem: Geoid-corrected DEM as xarray DataArray
    :type dem: DataArray
    :param resolution: Resolution of DEM strip, defaults to None
    :type resolution: float, optional
    :param candidate_height_thresh_m: Maximum value relative to geoid to be considered
        as SL, in m, defaults to 10
    :type candidate_height_thresh_m: float
    :param candidate_area_thresh_km2: Minimum area beneath `candidate_height_thresh_m`
        to be considered for sea level assessment, in km^2, defaults to 1
    :type candidate_area_thresh_km2: float
    :param near_sealevel_thresh_m: Filter out regions below this value, in metres above
        sea level, defaults to 5
    :type near_sealevel_thresh_m: float

    :returns: Mask as xarray DataArray. Land/ice is True and ocean is False
    :rtype: DataArray
    """

    # Get resolution if not provided
    if resolution == None:
        resolution = get_resolution(dem)

    est_sea_level = get_sea_level(
        dem,
        resolution,
        candidate_height_thresh_m,
        candidate_area_thresh_km2,
    )

    if est_sea_level == None:
        return ~dem.isnull()
    else:
        return dem > (est_sea_level + near_sealevel_thresh_m)


def get_sea_level(
    dem: DataArray,
    resolution: Optional[float] = None,
    candidate_height_thresh_m: float = 10,
    candidate_area_thresh_km2: float = 1,
) -> float:
    """Returns estimated sea level following method of Shiggins _et al._ (2023). If no
    candidate sea level is identified, None is returned. DEM must be geoid-corrected.

    :param dem: Geoid-corrected DEM as xarray DataArray
    :type dem: DataArray
    :param resolution: Resolution of DEM strip, defaults to None
    :type resolution: float, optional
    :param candidate_height_thresh_m: Maximum value relative to geoid to be considered
        as SL, in m, defaults to 10
    :type candidate_height_thresh_m: float
    :param candidate_area_thresh_km2: Minimum area beneath `candidate_height_thresh_m`
        to be considered for sea level assessment, in km^2, defaults to 1
    :type candidate_area_thresh_km2: float

    :returns: Mask as xarray DataArray. Land/ice is True and ocean is False
    :rtype: DataArray
    """

    # Get resolution if not provided
    if resolution == None:
        resolution = get_resolution(dem)

    # Get values close to sea level as 1D numpy array
    near_sealevel_values = dem.values.ravel()
    near_sealevel_values = near_sealevel_values[
        near_sealevel_values < candidate_height_thresh_m
    ]

    # Skip melange filtering if the candidate region is less than the threshold area
    thresh_px_n = int(candidate_area_thresh_km2 * 1e6 / (resolution * 2))
    if len(near_sealevel_values) < thresh_px_n:
        return None

    # Else, construct a 0.25m resolution histogram between -15 and +15:
    else:
        bin_edges = np.arange(-15.125, 15.375, 0.25)
        bin_centres = bin_edges[:-1] + 0.125
        hist, _ = np.histogram(near_sealevel_values, bins=bin_edges)

        # The estimated sea level is the centre of the modal bin
        est_sea_level = bin_centres[np.argmax(hist)]

        return est_sea_level
