# Pipeline and Workflow

This section contains a large collection of Python Jupyter notebooks that perform the essential data processing workflows.  I've stuck with Python as it's generally the easiest for non-software folks to grasp.  It's also a really solid data science language.


## Landsat Overview

For this demonstration, we use Landsat 8 and 9.  Information about Landsat bands can be located here at the [USGS](https://www.usgs.gov/faqs/what-are-band-designations-landsat-satellites).  

For information about Analysis Ready Data (ARD) and naming conventions, see [this link](https://www.usgs.gov/landsat-missions/landsat-collection-2-us-analysis-ready-data).

### Stages of Landsat Computations

Landsat 8 and 9 provide the following spectral bands which are relevant to us:

| Band ID   | Color                     | Wavelengths   | Resolution            |
|-----------|---------------------------|---------------|-----------------------|
|    4      |  Red                      | 0.64 - 0.67   | $30 \frac{m}{pixel}$  |
|    5      | Near Infrared (NIR)       | 0.85 - 0.88   | $30 \frac{m}{pixel}$  |
|   10      | Thermal Infrared (TIRS) 1 | 10.60 - 11.19 | $100 \frac{m}{pixel}$ |
|   11      | Thermal Infrared (TIRS) 2 | 11.50 - 12.51 | $100 \frac{m}{pixel}$ |

Other Data Products

| Product ID   | Description                                          |
|--------------|------------------------------------------------------|
| ST_B6        | Surface Temperature in Kelvin                        |
| ST_QA        | Surface Temperature Quality Assessment (Uncertainty) |
| ST_ATRAN     | Surface Temperature Atmospheric Transmittance Layer  |
| ST_EMIS      | Surface Temperature Emissivity Layer                 |
| ST_EMSD      | Surface Temperature Emissivity Standard Deviation    |



Data provided courtesy of the USGS. 
* [Spectral Band Overview](https://www.usgs.gov/faqs/what-are-best-landsat-spectral-bands-use-my-research)
* [Provisional Surface Temperature Overview](https://www.usgs.gov/landsat-missions/landsat-provisional-surface-temperature)

### 1. Cleaning Up Landsat Folders

**Feel free to skip this notebook.** This is a simple utility to reorganize the vast quantity of Landsat imagery I collected into a more digestible catalog.

### 2. Landsat Data Wrangling
This section focuses on clipping and reprojecting all base image layers to UTM focused around Denver.

[](Part2_Data_Wrangling)

### 3. NDVI and LST for Landsat 8 and 9

This notebook takes the Landsat 8 and 9 bands we projected and builds the following:

* Normalized Difference Vegetation Index (NDVI)
* Brightness Temperature
* Emissivity
* Land Surface Temperature

### 2. Visualizing Landsat Data

From the results, we look at a bunch of different gardens. 


## Misc Python Projection and Image Processing Notes

For a good tutorial on using Rasterio, see [this link](https://hatarilabs.com/ih-en/how-to-reproject-single-and-multiple-rasters-with-python-and-rasterio-tutorial). 