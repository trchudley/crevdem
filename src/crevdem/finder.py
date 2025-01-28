"""
This module contains the functions necessary to extract crevasse location and volume 
from ArcticDEM/REMA strips, based around the use of black top hat (BTH) filtering (Kodde
_et al._ 2007). 

The primary input is an xarray DataAray of a 2 m ArcticDEM or REMA strip, which can be 
created and filtered using other functions within `crevdem`. 

The key tunable parameter is the `range` variable, which is set to 60 m based on 
variogram analysis of ArcticDEM strips of marine-terminating Greenlandic glaciers.
An example of this anlaysis is included in the `notebooks` directory of the package.
"""

import time
from typing import Optional

import numpy as np

from cv2 import morphologyEx, MORPH_BLACKHAT
from rasterio.fill import fillnodata
from xarray import DataArray
from numpy import maximum

from ._utils import get_resolution
from .preprocess import detrend


def find(
    dem: DataArray,
    resolution: Optional[float] = None,
    range_m: float = 60.0,
    gauss_std_m: float = 200,
    gauss_cutoff: float = 1.0,
    depth_thresh_m: float = 1.0,
    retain_intermediates: bool | tuple = False,
    verbose: bool = False,
) -> DataArray:
    """Returns crevasse depths, batch processed from input DEM strip. Parameters default
    to Chudley _et al._ generic workflow for Greenland marine margins, but can be
    modified. This function is a wrapper for the `detrend`, `bth_filter`,
    `threshold_depth`, `interpolate_surface`, and `calc_depth` functions.

    :param dem: xarray DataArray of DEM strip
    :type dem: DataArray
    :param resolution: Resolution of DEM strip, defaults to None
    :type resolution: float, optional
    :param range_m: Range of crevasse variability in metres, defaults to 60
    :type range_m: float
    :param gauss_std_m: standard deviation of Gaussian filter in metres, defaults to 200
    :type gauss_std_m: float
    :param gauss_cutoff: Truncate the gaussian kernel at this many standard deviations,
        defaults to 1
    :type gauss_cutoff: float
    :param depth_thresh_m: Threshold of BTH filter, in metres, at which to classify
        crevasses, defaults to 1
    :type depth_thresh_m: float
    :param retain_intermediates: If True, output will be a DataSet containing all
        intermediate steps, ["dem_detrended", "bth", "crev_mask", "dem_filled"]), if
        False, output will be dem_filled DataArray only, defaults to False
    :type retain_intermediates: bool
    :param verbose: Provides print output of intermediate steps and timings if True,
        defaults to False
    :type verbose: bool

    :returns: Dataset or DataArray containing output(s) of crevasse-finding procedure,
        dependent on whether retain_intermediates is True
    :rtype: Dataset or DataArray
    """

    # Get resolution if not provided
    if resolution == None:
        resolution = get_resolution(dem)

    # # Calculate range in nearest int number of pixels
    # range_px = int(np.round(range / resolution))

    # Step 1: Detrend
    if verbose == True:
        print("Detrending...", end=" ")
        start = time.time()

    dem_detrended = detrend(dem, gauss_std_m, gauss_cutoff, resolution=resolution)

    if verbose == True:
        print(f"{(time.time() - start):.1f} s")

    # Step 2: BTH filter
    if verbose == True:
        print("Applying Black Top Hat filter...", end=" ")
        start = time.time()

    bth = bth_filter(
        dem_detrended,
        kernel_diameter_m=range_m,
        resolution=resolution,
    )

    if verbose == True:
        print(f"{(time.time() - start):.1f} s")

    # Step 3: Depth filter
    if verbose == True:
        print("Applying depth threshold...", end=" ")
        start = time.time()

    crev_mask = threshold_depth(bth, depth_thresh_m)

    if verbose == True:
        print(f"{(time.time() - start):.1f} s")

    # Step 4: Infilling
    if verbose == True:
        print("Interpolating surface...", end=" ")
        start = time.time()

    # Set search distance is twice range
    search_dist_px = int(np.round(range_m / resolution)) * 2

    dem_filled = interpolate_surface(
        dem,
        crev_mask,
        search_dist_px,
        smoothing_iterations=2,
    )

    if verbose == True:
        print(f"{(time.time() - start):.1f} s")

    # Step 5: Calculating crevasse depth
    if verbose == True:
        print("Calculating crevasse depth...", end=" ")
        start = time.time()

    crev_depth = calc_depth(dem, dem_filled)

    if verbose == True:
        print(f"{(time.time() - start):.1f} s")

    if verbose == True:
        print("Finished")

    # Step 6a: If not retaining intermediates, return filled DEM
    if retain_intermediates == False:
        del (
            dem_detrended,
            bth,
            crev_mask,
            dem_filled,
        )
        return crev_depth

    # Step 6b, if retaining intermediates, construct and return DataSet of variables
    elif retain_intermediates == True:
        xds = dem.to_dataset(name="dem")
        xds["dem_detrended"] = dem_detrended
        xds["bth"] = bth
        xds["crev_mask"] = crev_mask
        xds["dem_filled"] = dem_filled
        xds["crev_depth"] = crev_depth

        return xds


def _bth_kernel(kernel_diameter_m: float, resolution: float) -> np.ndarray:
    """Create BTH disc-shaped kernel of radius `bth_kernel_diameter_m`, following
    the scipy.morphology 'disc' function.

    :param bth_kernel_diameter_m: Diameter of BTH kernel, in metres
    :type bth_kernel_diameter_m: float
    :param resolution: Resolution of DEM strip, defaults to None
    :type resolution: float, optional

    :returns: Kernel array to be used as input to opencv `morphologyEx` function
    :rtype: np.ndarray
    """
    radius_px = int(kernel_diameter_m / resolution / 2)

    # below repiclated from scipy.morphology function disk
    L = np.arange(-radius_px, radius_px + 1)
    X, Y = np.meshgrid(L, L)
    kernel = ((X**2 + Y**2) <= radius_px**2).astype(np.uint8)

    return kernel


def bth_filter(
    dem_detrended: DataArray,
    kernel_diameter_m: float,
    resolution: Optional[float] = None,
) -> DataArray:
    """Returns a black-top-hat-filtered DEM DataArrat from the (detrended) DEM
    DataArray. Kernel diameter is set following the range distance.

    :param dem_detrended: Detrended DEM DataArray
    :type dem_detrended: DataArray
    :param kernel_diameter_m: Diameter of BTH kernel, in metres
    :type kernel_diameter_m: float
    :param resolution: Resolution of DEM strip, defaults to None
    :type resolution: float, optional

    :returns: BTH-filtered DEM as dataarray.
    :rtype: DataArray
    """

    # Get resolution if not provided
    if resolution == None:
        resolution = get_resolution(dem_detrended)

    kernel = _bth_kernel(kernel_diameter_m, resolution)

    bth = morphologyEx(
        dem_detrended.values,
        MORPH_BLACKHAT,
        kernel,
    )

    # Slightly hacky workaround to make ndarray a DataArray with inherited
    # geospatial information:
    bth = dem_detrended * 0 + bth

    # dem_xds["bth_filter"] = (
    #     ("y", "x"),
    #     morphologyEx(
    #         dem_xds.dem_detrend.values,
    #         MORPH_BLACKHAT,
    #         kernel,
    #     ),
    # )

    return bth


def threshold_depth(
    bth: DataArray,
    depth_thresh_m: float,
) -> DataArray:
    """Returns crevasse mask (crevasse = 1; not crevasse = 0) DataArray from
    BTH-filtered DataArray. Mask is filtered to the threshold BTH value, which is set
    to 1 metre in the default workflow.

    :param bth: BTH-filtered DEM, as DataArray
    :type bth: DataArray
    :param depth_thresh_m: Threshold depth of crevasses, in metres
    :type depth_thresh_m: float

    :returns: Mask DataArray with crevasse=1 and not crevasse=0.
    :rtype: DataArray
    """

    crev_mask = np.where(bth.values >= depth_thresh_m, 1, 0).astype(np.int8)

    # Slightly hacky workaround to make ndarray a DataArray with inherited
    # geospatial information:
    crev_mask = bth * 0 + crev_mask

    # dem_xds["crev_mask"] = (
    #     ("y", "x"),
    #     np.where(dem_xds.bth_filter.values >= depth_thresh, 1, 0).astype(np.int8),
    # )

    return crev_mask


def interpolate_surface(
    dem: DataArray,
    crev_mask: DataArray,
    search_dist_px: int,
    smoothing_iterations: Optional[int] = 2,
) -> DataArray:
    """Returns a 'crevasse-filled' DEM from the original DEM and crevasse mask, using
    the GDAL FillNodata algorithm (inverse distance weighting) to fill crevasse-masked
    regions. Smoothing iterations are applied to smooth  out artefacts.

    :param dem: DEM, as DataArray
    :type dem: DataArray
    :param crev_mask: Crevasse mask, as DataArray
    :type crev_mask: DataArray
    :param search_dist_px: Search distance for infilling operation, in pixels
    :type search_dist_px: float
    :param smoothing_iterations: The number of 3x3 smoothing filter passes to run,
        defaults to 2
    :type smoothing_iterations: float

    :returns: DEM-filled DataArray.
    :rtype: DataArray

    """

    dem_idw = dem.values.copy()
    fillnodata(
        dem_idw,
        mask=(1 - crev_mask.values),
        max_search_distance=search_dist_px,
        smoothing_iterations=smoothing_iterations,
    )

    # dem_xds["dem_filled"] = (("y", "x"), dem_idw)
    dem_filled = dem * 0 + dem_idw

    # Where IDW takes intepolated surface 'beneath' true surface, take true surface
    dem_filled = maximum(dem, dem_filled)

    # Remove edge interpolation effects by filtering to original BTH surface
    dem_filled = dem_filled.where(crev_mask >= 0)

    return dem_filled


def calc_depth(dem: DataArray, dem_filled: DataArray) -> DataArray:
    """Returns final crevasse depth, calculated from the raw DEM and the filled DEM.

    :param dem: Raw DEM, as DataArray
    :type dem: DataArray
    :param dem_filled: Crevasse-filled DEM, as DataArray
    :type dem_filled: DataArray

    :returns: Crevasse depth DataArray.
    :rtype: DataArray
    """

    return dem_filled - dem
