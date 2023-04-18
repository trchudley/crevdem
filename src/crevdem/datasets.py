"""
This module contains functions for loading supplementary data, including geoid and 
surface mask data, from third-party datasets (BedMachine and GrIMP). The local file
locations must be provided. 

Tom Chudley | Durham University | thomas.r.chudley@durham.ac.uk
"""


import glob, os
from typing import Optional

import rasterio as rs
import rioxarray as rxr

from shapely.geometry import box
from rasterio.enums import Resampling
from rioxarray.merge import merge_arrays
from xarray import DataArray


def get_bedmachine_geoid(bm_fpath, target_rxd) -> DataArray:
    """Extracts the BedMachine geoid, resampled to match the target dataset

    :param bm_fpath: Filepath to BedMachine dataset, defaults to None
    :type bm_fpath: str
    :param target_rxd: (rio)xarray dataset that BedMachine will be resampled to match
    :type target_rxd: DataArray

    :returns: geoid for the target_rxd region as an xarray DataArray
    :rtype: DataArray"""

    geoid = rxr.open_rasterio(f"{bm_fpath}")["geoid"]
    geoid_crs = geoid.rio.crs
    geoid = geoid.squeeze().astype("float32").rio.write_crs(geoid_crs)
    geoid = geoid.rio.reproject_match(target_rxd, Resampling.bilinear)

    return geoid.squeeze()


def get_grimp_mask(
    grimp_mask_dir: str,
    target_rxd: DataArray,
    ice_val: Optional[int] = 0,
    ocean_val: Optional[int] = 0,
    land_val: Optional[int] = 0,
) -> DataArray:
    """Get the GrIMP mask for given (rio)xarray Dataset or DataArray. Values for ice,
    ocean, and land can be provided seperately, and will all default to zero. For the
    mask to be treated as boolean, limit values to 1 (True) or 0 (False).

    :param grimp_mask_dir: Filepath of directory containing the 15 m GrIMP ice mask.
    :type grimp_mask_dir: str
    :param target_rxd: (rio)xarray Dataset or DataArray to match to mask to (in CRS,
    resolution, and extent) according to nearest neighobur resampling.
    :type target_rxd: Dataset or DataArray
    :param ice_val: Value of ice-masked region in output array, defaults to 0
    :type ice_val: int, optional
    :param ocean_val: Value of ocean-masked region in output array, defaults to 0
    :type ocean_val: int, optional
    :param land_val: Value of land-masked region in output array, defaults to 0
    :type land_val: int, optional

    :returns: GrIMP mask for the region as an xarray DataArray
    :rtype: DataArray
    """

    bounds = target_rxd.rio.bounds()
    aoi = box(*bounds)

    if (ice_val == 0) and (ocean_val == 0) and (land_val == 0):
        raise ValueError(
            "At least one of `ice_val`, `ocean_val`, or `land_val` must be set to !=0"
        )

    # Loop through GIMP masks, getting valid tile codes
    ice_tile_fpaths = []
    for gimp_fpath in glob.glob(os.path.join(grimp_mask_dir, "GimpIceMask_15m_*.tif")):
        with rs.open(gimp_fpath) as src:
            xmin, ymin, xmax, ymax = src.bounds
            gimp = box(xmin, ymin, xmax, ymax)

        if aoi.intersects(gimp) == True:
            ice_tile_fpaths.append(gimp_fpath)

    if len(ice_tile_fpaths) < 1:
        raise ValueError(f"No GrIMP tiles intersect bounds {bounds}")

    # Get ice mask if necessary
    if ice_val != 0 or land_val != 0:
        ice_masks = []
        for fpath in ice_tile_fpaths:
            mask = rxr.open_rasterio(fpath)
            mask = mask.rio.clip_box(*bounds)
            ice_masks.append(mask)
        if len(ice_masks) > 1:
            ice_mask = merge_arrays(ice_masks)
        else:
            ice_mask = ice_masks[0]
    else:
        ice_mask = 0

    # Get ocean mask if necessary
    if ocean_val != 0 or land_val != 0:
        ocean_tile_fpaths = [
            s.replace("GimpIceMask", "GimpOceanMask") for s in ice_tile_fpaths
        ]
        ocean_masks = []
        for fpath in ocean_tile_fpaths:
            mask = rxr.open_rasterio(fpath)
            mask = mask.rio.clip_box(*bounds)
            ocean_masks.append(mask)
        if len(ocean_masks) > 1:
            ocean_mask = merge_arrays(ocean_masks)
        else:
            ocean_mask = ocean_masks[0]
    else:
        ocean_mask = 0

    # Get land mask if necessary
    if land_val != 0:
        land_mask = ((ice_mask == 0) & (ocean_mask == 0)).astype("uint8")
    else:
        land_mask = 0

    mask = (ice_mask * ice_val + ocean_mask * ocean_val + land_mask * land_val).astype(
        "uint8"
    )

    mask = mask.rio.reproject_match(target_rxd, Resampling.nearest)

    return mask.squeeze()
