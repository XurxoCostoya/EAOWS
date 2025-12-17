# EWAVES-CLIM
This repository contains the code used for processing the data from the database "European Atlantic Wave Data under Historical and Future Climate Scenarios (EAWAVES-CLIM)", which is hosted in the CEDA archive.

Currently, only one file is included (netcdf_to_sp2.py), which is described below:

- Python script to convert NetCDF daily spectral files into .sp2 format required by SWAN for spectral forcing.
- Input: NetCDF files with dimensions (time x location x frequency x direction).
- Output: .sp2 plain-text files that allow starting SWAN simulations.
- Usage instructions and metadata are included in the script's header.
