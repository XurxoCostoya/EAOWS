# -*- coding: utf-8 -*-
"""
NetCDF to SP2 Converter for SWAN Wave Model
-------------------------------------------

This script converts a set of daily NetCDF files containing wave spectral energy 
data into SWAN-compatible SP2 files. Each NetCDF file must include energy density 
matrices (time x point x frequency x direction) with a 3-hourly time resolution.

The output is a plain-text .sp2 file for each input NetCDF, following SWAN's 
spectral input format.

Usage:
1. Place the daily NetCDF files in the same folder as this script. 
   Filenames should start with 'esp_' and have a '.nc' extension.
2. Run this script.
3. The generated .sp2 files will be saved in a subfolder named: 'converted_sp2_files'

"""

import xarray as xr
import numpy as np
import os
from datetime import datetime
from tqdm import tqdm
import logging

# Configuration
CONFIG = {
    'input_dir': os.getcwd(),             # Directory containing input NetCDF files
    'output_dir': os.path.join(os.getcwd(), "converted_sp2_files"),  # Directory for SP2 output files
    'log_file': 'conversion_log.txt',     # Log file path
    'exception_value': -99.0,             # Value for missing data in SP2 files
    'swan_version': '41.41',              # SWAN version for header
    'project_name': 'WaveDataProject',    # Project name for header
    'run_number': '1.0',                  # Run number for header
    'overwrite': False                    # Overwrite existing SP2 files?
}

def setup_logging():
    """Configure logging system with both file and console output."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(CONFIG['log_file']),
            logging.StreamHandler()
        ]
    )
    logging.info("SWAN NetCDF to SP2 Conversion Tool")
    logging.info(f"Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def validate_netcdf(ds):
    """
    Validate that the NetCDF contains required variables and dimensions.
    
    Args:
        ds: xarray Dataset to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    required_vars = ['longitude', 'latitude', 'frequency', 'direction', 
                    'energy_density', 'time']
    for var in required_vars:
        if var not in ds.variables:
            logging.error(f"Missing required variable: {var}")
            return False
    return True

def format_swan_time(nptime):
    """
    Convert numpy datetime64 to SWAN time format (YYYYMMDD.HHMMSS).
    
    Args:
        nptime: numpy datetime64 value
        
    Returns:
        str: Formatted time string
    """
    dt = np.datetime_as_string(nptime, unit="s")
    date, time = dt.split("T")
    return f"{date.replace('-', '')}.{time.replace(':', '')}"

def write_sp2_header(f, ds, nloc):
    """
    Write the SWAN SP2 file header section.
    
    Args:
        f: File handle
        ds: xarray Dataset
        nloc: Number of locations
    """
    # File identification
    f.write("SWAN   1                                Swan standard spectral file, version\n")
    f.write(f"$   Data produced by SWAN version {CONFIG['swan_version']}\n")
    f.write(f"$   Project: {CONFIG['project_name']}        ;  run number: {CONFIG['run_number']}\n")
    
    # Time information
    f.write("TIME                                    time-dependent data\n")
    f.write("     1                                  time coding option\n")
    
    # Location information
    f.write("LONLAT                                  locations in spherical coordinates\n")
    f.write(f"{nloc:6d}                                  number of locations\n")
    
    # Write coordinates
    for lon, lat in zip(ds.longitude.values, ds.latitude.values):
        f.write(f"{lon:10.4f} {lat:10.4f}\n")
    
    # Frequency information
    f.write("AFREQ                                   absolute frequencies in Hz\n")
    f.write(f"{len(ds.frequency):6d}                                  number of frequencies\n")
    for fr in ds.frequency.values:
        f.write(f"{fr:10.4f}\n")
    
    # Direction information
    f.write("NDIR                                    spectral nautical directions in degr\n")
    f.write(f"{len(ds.direction):6d}                                  number of directions\n")
    for d in ds.direction.values:
        f.write(f"{d:10.4f}\n")
    
    # Quantity information
    f.write("QUANT\n")
    f.write("     1                                  number of quantities in table\n")
    f.write("EnDens                                  energy densities in J/m2/Hz/degr\n")
    f.write("J/m2/Hz/degr                            unit\n")
    f.write(f"{CONFIG['exception_value']:10.4e}                          exception value\n")

def convert_netcdf_to_sp2(input_path, output_path):
    """
    Convert a single NetCDF file to SP2 format.
    
    Args:
        input_path: Path to input NetCDF file
        output_path: Path for output SP2 file
    """
    try:
        # Open NetCDF file
        with xr.open_dataset(input_path) as ds:
            if not validate_netcdf(ds):
                return False
            
            # Prepare data arrays
            energy = ds.energy_density.values
            factors = ds.factor.values if 'factor' in ds else np.ones((len(ds.time), len(ds.longitude)))
            nloc = len(ds.longitude)
            
            # Create output directory if needed
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Write SP2 file
            with open(output_path, 'w') as f:
                # Write header
                write_sp2_header(f, ds, nloc)
                
                # Write time steps
                for t_idx in range(len(ds.time)):
                    swan_time = format_swan_time(ds.time.values[t_idx])
                    f.write(f"{swan_time}                         date and time\n")
                    
                    # Write data for each location
                    for p_idx in range(nloc):
                        f.write("FACTOR\n")
                        f.write(f"{factors[t_idx, p_idx]:.16e}\n")
                        
                        # Write energy matrix
                        for fr_idx in range(len(ds.frequency)):
                            row = energy[t_idx, p_idx, fr_idx, :]
                            row_ints = np.nan_to_num(row, nan=0.0)
                            row_ints = np.round(row_ints).astype(int)
                            row_str = " ".join(f"{val:6d}" for val in row_ints)
                            f.write(row_str + "\n")
            
            return True
            
    except Exception as e:
        logging.error(f"Error processing {os.path.basename(input_path)}: {str(e)}")
        return False

def main():
    """Main conversion routine."""
    setup_logging()
    
    # Create output directory
    os.makedirs(CONFIG['output_dir'], exist_ok=True)
    
    # Get list of NetCDF files (only those starting with 'esp_' and ending with '.nc')
    netcdf_files = [
        f for f in os.listdir(CONFIG['input_dir']) 
        if f.startswith('esp_') and f.endswith('.nc')
    ]
    
    if not netcdf_files:
        logging.warning(f"No valid NetCDF files found in {CONFIG['input_dir']}")
        logging.warning("Expected files starting with 'esp_' and ending with '.nc'")
        return
    
    logging.info(f"Found {len(netcdf_files)} NetCDF files to process")
    
    # Process files with progress bar
    success_count = 0
    for filename in tqdm(netcdf_files, desc="Converting files"):
        input_path = os.path.join(CONFIG['input_dir'], filename)
        output_path = os.path.join(
            CONFIG['output_dir'], 
            f"{os.path.splitext(filename)[0]}.sp2"
        )
        
        # Skip existing files if overwrite is False
        if not CONFIG['overwrite'] and os.path.exists(output_path):
            logging.info(f"Skipping existing file: {filename}")
            continue
            
        if convert_netcdf_to_sp2(input_path, output_path):
            success_count += 1
            logging.info(f"Successfully converted: {filename}")
    
    # Final report
    logging.info("\nConversion Summary:")
    logging.info(f"- Total files processed: {len(netcdf_files)}")
    logging.info(f"- Successfully converted: {success_count}")
    logging.info(f"- Output directory: {os.path.abspath(CONFIG['output_dir'])}")
    logging.info(f"Log file saved to: {os.path.abspath(CONFIG['log_file'])}")

if __name__ == "__main__":
    main()