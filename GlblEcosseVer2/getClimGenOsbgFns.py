#-------------------------------------------------------------------------------
# Name:        getClimGenOsbgFns.py
# Purpose:     additional functions for getClimGenNC.py
# Author:      s03mm5
# Created:     08/02/2018
# Copyright:   (c) s03mm5 2015
# Licence:     <your licence>
#-------------------------------------------------------------------------------
#!/usr/bin/env python

__prog__ = 'getClimGenOsbgFns.py'
__author__ = 's03mm5'

from PyQt5.QtWidgets import QApplication
from calendar import isleap, monthrange
from math import floor, ceil
from netCDF4 import Dataset
from csv import writer as csv_writer
from os.path import exists, normpath, split, join, lexists, basename
from os import makedirs
from glob import glob
from copy import copy

from thornthwaite import thornthwaite
from cvrtcoord import WGS84toOSGB36

ERROR_STR = '*** Error *** '
METRICS = ['precip', 'tas']
METRICS_LTA = METRICS + ['pet']
MNTHS_YR = 12
numSecsDay = 3600*24

def _make_met_files_osgb(clim_dir, lat, climgen, pettmp_grid_cell = None):
    """
    feed annual temperatures to Thornthwaite equations to estimate Potential Evapotranspiration [mm/month]
    """
    func_name = __prog__ + '  _make_met_files_osgb'

    if not climgen.mnthly_flag:
        print(ERROR_STR + func_name + ' is monthly only')
        return

    nyears = climgen.max_num_years
    met_fnames = []

    # check if met files already exist
    # ================================
    if lexists(clim_dir):
        met_files = glob(clim_dir + '\\met*s.txt')
        if len(met_files) >= nyears:
            for met_file in met_files:
                dummy, short_name = split(met_file)
                met_fnames.append(short_name)
    else:
        makedirs(clim_dir)

    if pettmp_grid_cell is None:        # check for met files only
        return met_fnames

    pettmp_precip = pettmp_grid_cell['precip']
    pettmp_tas = [val - 273.15 for val in pettmp_grid_cell['tas']]     # CHESS Near-Surface air temperature is in Kelvin

    # create met files
    # ================
    strt_year = climgen.hist_start_year
    nmnths = len(pettmp_precip)
    indx1 = 0

    for year in range(strt_year, strt_year + nyears):
        fname = 'met{}s.txt'.format(year)
        met_fnames.append(fname)
        met_path = join(clim_dir, fname)
        monthrange(year, 2)

        indx2 = indx1 + MNTHS_YR
        if indx2 > nmnths:
            print('indx2: {}\tnmnths: {}'.format(indx2, nmnths))
            break

        # air temperature
        # ===============
        if indx2 == nmnths:
            temp_mean     = pettmp_tas[indx1:]
            precip_for_yr = pettmp_precip[indx1:]
        else:
            temp_mean     = pettmp_tas[indx1:indx2]
            precip_for_yr = pettmp_precip[indx1:indx2]

        pet = thornthwaite(temp_mean, lat, year)

        # convert precipitation with units: kg m-2 s-1 to mm per month
        # ============================================================
        precips = []
        for imnth, precip in enumerate(precip_for_yr):
            ndays = monthrange(year, imnth + 1)[1]
            precip_mm = precip * numSecsDay * ndays
            precips.append(precip_mm)

        # TODO: do something about occasional runtime warning...
        pot_evapotrans = [round(p, 2) for p in pet]
        precip_out     = [round(p, 2) for p in precips]
        tmean_out      = [round(t, 2) for t in temp_mean]

        # write file
        # ==========
        output = []
        for tstep, mean_temp in enumerate(tmean_out):
            output.append([tstep+1, precip_out[tstep], pot_evapotrans[tstep], mean_temp])

        with open(met_path, 'w', newline='') as fpout:
            writer = csv_writer(fpout, delimiter='\t')
            writer.writerows(output)

        indx1 += MNTHS_YR

    return met_fnames

def add_data_to_grid_cells(climgen, grid_cells):
    """
    units are taken care of when outputting met files in make_met_file
        precipitation has units of kg m-2 s-1
        tas in degrees Kelvin

    due to an anomoly in the historic dataset we must reduce number of time steps from by one month
    """

    wthr_rsrc = climgen.wthr_rsrc_key
    hist_precip_dset = climgen.hist_precip_dset
    fut_precip_dset = climgen.fut_precip_dset
    hist_tas_dset = climgen.hist_tas_dset
    fut_tas_dset = climgen.fut_tas_dset
    fut_strt_indx = climgen.fut_strt_indx

    for grid_ref in grid_cells.keys():
        print('Adding CHESS data to cell '  + grid_ref)
        QApplication.processEvents()

        grid_cell = copy(grid_cells[grid_ref])
        indx_east = grid_cell.indx_east
        indx_nrth = grid_cell.indx_nrth

        # record LTAs
        # ===========
        for metric in METRICS_LTA:  # tas, pet, precip
            grid_cell.lta[metric] = [float(val) for val in climgen.lta_nc_dset.variables[metric][:, indx_nrth, indx_east]]

        # check if a complete set of met files for this grid cell already exists
        # ======================================================================
        lat = grid_cell.lat
        met_rel_path = '..\\..\\' + wthr_rsrc + '\\' + grid_ref + '\\'
        grid_cell.met_rel_path = met_rel_path

        clim_dir = normpath(join(climgen.sims_dir, wthr_rsrc, grid_ref))      #
        met_fnames = _make_met_files_osgb(clim_dir, lat, climgen)     # check to see if met files are aleady present
        if len(met_fnames) == 0:

            # discard last month of historic data
            # ===================================
            wthr = {}
            hist_vals = [float(val) for val in hist_precip_dset['precip'][:-1, indx_nrth, indx_east]]
            fut_vals  = [float(val) for val in fut_precip_dset['pr'][fut_strt_indx:, indx_nrth, indx_east]]
            wthr['precip'] = hist_vals + fut_vals

            hist_vals = [float(val) for val in hist_tas_dset['tas'][:-1, indx_nrth, indx_east]]
            fut_vals = [float(val) for val in fut_tas_dset['tas'][fut_strt_indx:, indx_nrth, indx_east]]
            wthr['tas'] = hist_vals + fut_vals

            met_fnames = _make_met_files_osgb(clim_dir, lat, climgen, wthr)
            # grid_cell.wthr = wthr

        grid_cells[grid_ref] = grid_cell

    return

def open_chess_dsets(climgen):
    """

    """
    climgen.fut_precip_dset = Dataset(climgen.fut_precip_fname, 'r')
    climgen.fut_tas_dset = Dataset(climgen.fut_tas_fname, 'r')
    climgen.hist_precip_dset = Dataset(climgen.hist_precip_fname, 'r')
    climgen.hist_tas_dset = Dataset(climgen.hist_tas_fname, 'r')
    climgen.lta_nc_dset = Dataset(climgen.lta_nc_fname, 'r')

    return

def close_chess_dsets(climgen):
    """

    """
    climgen.fut_precip_dset.close()
    climgen.fut_tas_dset.close()
    climgen.hist_precip_dset.close()
    climgen.hist_tas_dset.close()
    climgen.lta_nc_dset.close()

    return

def fetch_chess_bbox_indices(lon_ll, lat_ll, lon_ur, lat_ur):
    """
     use Hannah Fry functions
    """
    eastng_ll, nrthng_ll = WGS84toOSGB36(lon_ll, lat_ll)
    indx_east_ll = floor(eastng_ll / 1000)
    indx_nrth_ll = floor(nrthng_ll / 1000)

    eastng_ur, nrthng_ur = WGS84toOSGB36(lon_ur, lat_ur)
    indx_east_ur = ceil(eastng_ur / 1000)
    indx_nrth_ur = ceil(nrthng_ur / 1000)

    ret_code = list([indx_nrth_ll, indx_nrth_ur, indx_east_ll, indx_east_ur])
    ret_code += [1000*val + 500 for val in ret_code]

    return ret_code
