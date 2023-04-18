# CrevDEM

**_Tools for extracting crevasse location and volume from high-resolution digital elevation models._**

![An aerial image of crevasses on the Greenland Ice Sheet](./images/crevasses_uav_header.jpeg "An aerial image of crevasses on the Greenland Ice Sheet")

CrevDEM is a Python package for extracting crevasse location and volume from high-resolution Digital Elevation Models (DEMs) of glaciers and ice sheets.

The functions within provide a complete workflow for:

1. Automatically downloading and clipping 2 m strips of the version 4.1 ArcticDEM (Porter _et al._ 2022) and Reference Elevation Model of Antarctica (REMA; Howat _et al._ 2022).
2. DEM geoid correction and filtering of bare rock and proglacial sea-ice/mélange.
3. Extracting crevasse presence following the method outlined by Chudley _et al._ (_in prep_).

The principle of crevasse extraction is based around Black Top Hat filtering of a detrended surface (Kodde _et al._ 2007). The optimal kernel size can be determined quantiatively through the use of variogram analysis: a notebook is provided to aid with this. 

> **Warning** 
> This workflow is designed for scientific purposes only. ArcticDEM and REMA strips are not suitable for detecting sub-decametre-scale and snow-covered crevasses, and should not be used for field hazard assessment.

![An example output from CrevDEM](./images/crevdem_output.jpg "An example output from CrevDEM")

# Cite

Please cite the source paper when using CrevDEM:

> Chudley, T. R., Howat, I. M., King, M. D., and MacKie, E. (_in prep_) An increase in crevasses across accelerating Greenland Ice Sheet margins.

As always when using ArcticDEM and REMA products, please [cite](#refererences) the datasets appropriately and [acknowledge](#acknowledgements) the PGC.


# Installation

## Install CrevDEM

After downloading, `crevdem` can be installed from the top-level directory via `pip install .`:

```bash
git clone https://github.com/trchudley/CrevDEM
cd CrevDEM
pip install .  # add -e flag for editable mode
```

CrevDEM has the following dependencies:
  - rioxarray
  - Rasterio
  - Shapely
  - NumPy
  - OpenCV

The variogram analysis notebook requires additional packages, including `scikit-gstat`. If you would not like to install these yourself using `conda` or similar, use `pip install .[variogram]`.

## Install supplementary datasets

Supplementary datasets are required to be available locally to complete geoid correction and filtering of non-glacial regions: specifically, the BedMachine Greenland v5 or BedMachine Antarctica v3 respectively (Morlighem _et al._ 2022a, 2022b) and, for Greenland, the GrIMP ice mask (Howat, 2017) for bedrock filtering.File or directory paths will be requested in the relevant functions.

These can be downloaded from the NSIDC manually ([Greenland BedMachine](https://doi.org/10.5067/GMEVBWFLWA7X), [Antarctic BedMachine](https://doi.org/10.5067/FPSU0V1MWUB6), [Greenland surface mask](https://doi.org/10.5067/B8X58MQBFUPA)) but for conveninence, download scripts are provided in the `supp_data` directory. The BedMachine download scripts are provided by the NSIDC, and require an Earthdata user account and password to be provided. The files will be downloaded into the directory the scripts are run. 

```bash
cd supp_data
python download_bedmachine_greenland_v5.py
python download_grimp_2015_15m.py
python download_bedmachine_antarctica_v3.py
```


# Usage

Jupyter Notebooks are provided in the `./notebooks` directory in order to provide an introduction into the use of CrevDEM.

## Retreiving and Masking ArcticDEM strips

### Loading

`xds = load_aws()` or `load_local()`

`geoid = get_bm_geoid()`

`xds['dem'] = geoidcorr(xds.dem, geoid)`

### Masking

`mask_grimp = get_grimp_mask(xds.dem)` or `mask = get_bm_mask(xds.dem)`

`mask_sea = get_sea_mask(xds.dem)`  is get_sea_level also exposed?

`mask = mask_grimp & mask_melange`

`xds['dem'] = mask(xds.dem, [mask1, mask2])`


## Extracting crevasse presence

`xds['crev_depth'] = find(xds.dem)`

which wraps a few other exposed functions.

`detrend`

`bth`

`crev_mask`

`crev_depth`

# Improvements

 - [ ] Write notebooks
 - [ ] Update 'Usage' section
 - [ ] Push to github
 - [ ] Verbose timing, BedMachine mask
 - [ ] Write proper tests

The tool is presented _as-is_, but requests/contributions to functionality are welcome (thomas.r.chudley@durham.ac.uk). Avenues for future work include the following:

 - Implement geoid-correction and filtering of land/ocean for Antarctica.
 - Additional filter for remnant cloud blunders (e.g. from difference to reference DEM mosaic?)
 - Explore alternative/custom Gaussian filters to prevent erosion at edges? Currently, Guassian and BTH filters return `Nan` if `NaN`s are present within the kernel, leading to margin effects. Could try and rewrite these functions to account for `NaN` values (`astropy` already has such a function for Gaussian filters but is _very_ slow)


# References

Chudley, T. R., _et al._ (_in prep_). An increase in crevasses across accelerating Greenland Ice Sheet margins. 

Howat, I. (2017). MEaSUREs Greenland Ice Mapping Project (GIMP) Land Ice and Ocean Classification Mask, Version 1 [Data Set]. _NASA National Snow and Ice Data Center Distributed Active Archive Center_. https://doi.org/10.5067/B8X58MQBFUPA

Howat, I., _et al._ (2022). The Reference Elevation Model of Antarctica – Strips, Version 4.1. _Harvard Dataverse_ https://doi.org/10.7910/DVN/X7NDNY

Kodde, M. P., _et al._ (2007). Automatic glacier surface analysis from airborne laser scanning. _The International Archives of the Photogrammetry, Remote Sensing and Spatial Information Sciences_, 36(3), 221–226.

Morlighem, M. _et al._ (2022). MEaSUREs BedMachine Antarctica, Version 3 [Data Set]. _NASA National Snow and Ice Data Center Distributed Active Archive Center_. https://doi.org/10.5067/FPSU0V1MWUB6

Morlighem, M. _et al._ (2022). IceBridge BedMachine Greenland, Version 5 [Data Set]. _NASA National Snow and Ice Data Center Distributed Active Archive Center_. https://doi.org/10.5067/GMEVBWFLWA7X

Porter, C., _et al._ (2022). ArcticDEM - Strips, Version 4.1. _Harvard Dataverse_. https://doi.org/10.7910/DVN/OHHUKH

Shiggins, _et al._ (2023). Automated ArcticDEM iceberg detection tool: insights into area and volume distributions, and their potential application to satellite imagery and modelling of glacier–iceberg–ocean systems, The Cryosphere, 17, 15–32, https://doi.org/10.5194/tc-17-15-2023

# Acknowledgements

**ArcticDEM:** DEMs are provided by the Polar Geospatial Center under NSF-OPP awards 1043681, 1559691, and 1542736.

**REMA:** DEMs are provided by the Byrd Polar and Climate Research Center and the Polar Geospatial Center under NSF-OPP awards 1543501, 1810976, 1542736, 1559691, 1043681, 1541332, 0753663, 1548562, 1238993 and NASA award NNX10AN61G. Computer time provided through a Blue Waters Innovation Initiative. DEMs produced using data from Maxar.