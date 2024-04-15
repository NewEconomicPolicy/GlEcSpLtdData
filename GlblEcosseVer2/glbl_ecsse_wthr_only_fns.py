"""
#-------------------------------------------------------------------------------
# Name:        glbl_ecsse_wthr_only_fns.py
# Purpose:     consist of high level functions invoked by main GUI
# Author:      Mike Martin
# Created:     05/02/2021
# Licence:     <your licence>
# Description:
#   generate weather from HWSD file
#-------------------------------------------------------------------------------
#
"""
__prog__ = 'glbl_ecsse_wthr_only_fns.py'
__version__ = '0.0.1'
__author__ = 's03mm5'

from time import time
import csv
from os.path import join
from PyQt5.QtWidgets import QApplication

import getClimGenNC
import hwsd_bil
from glbl_ecsse_high_level_fns import simplify_soil_recs
from prepare_ecosse_files import update_progress
from getClimGenFns import check_clim_nc_limits, associate_climate

HEADERS = ['latitude', 'longitude', 'mu_global', 'gran_lat', 'gran_lon']

def generate_soil_output(form):
    """
    called from GUI
    """
    if form.hwsd_mu_globals == None:
        print('Undetermined HWSD aoi - please select a valid HSWD csv file')
        return

    # bounding box defn
    # =================
    lat_ll = form.hwsd_mu_globals.lat_ll_aoi
    lon_ll = form.hwsd_mu_globals.lon_ll_aoi
    lat_ur = form.hwsd_mu_globals.lat_ur_aoi
    lon_ur = form.hwsd_mu_globals.lon_ur_aoi
    bbox = list([lon_ll, lat_ll, lon_ur, lat_ur])
    form.bbox = bbox

    # Create and initialise CSV object
    # ================================
    climgen = getClimGenNC.ClimGenNC(form)
    wthr_csv = WthrCsvOutputs(form, climgen)
    wthr_csv.create_results_files()

    # extract required values from the HWSD database and simplify if requested
    # ========================================================================
    hwsd = hwsd_bil.HWSD_bil(form.lgr, form.hwsd_dir)

    mu_global_pairs = {mu_global : None for mu_global in form.hwsd_mu_globals.mu_global_list}     # dict comprehension
    soil_recs = hwsd.get_soil_recs(mu_global_pairs)  # list is already sorted
    for mu_global in hwsd.bad_muglobals:
        del (soil_recs[mu_global])

    form.hwsd_mu_globals.soil_recs = simplify_soil_recs(soil_recs)
    form.hwsd_mu_globals.bad_mu_globals = [0] + hwsd.bad_muglobals
    aoi_indices_fut, aoi_indices_hist = climgen.genLocalGrid(bbox, hwsd)

    # step through each cell
    # ======================
    skipped, completed, warning_count = 3*[0]
    last_time, start_time = 2*[time()]
    ncells = form.hwsd_mu_globals.data_frame.shape[0]
    for index, row in form.hwsd_mu_globals.data_frame.iterrows():
        mu_global = int(row['mu_global'])
        latitude = round(row['latitude'], 5)
        longitude = round(row['longitude'], 5)
        gran_lat = int(row['gran_lat'])
        gran_lon = int(row['gran_lon'])

        site_rec = list([gran_lat, gran_lon, latitude, longitude, mu_global, None])

        completed += 1
        last_time = update_progress(last_time, start_time, completed, ncells, skipped, warning_count)

    # close CSV files
    # ==============
    for key in wthr_csv.output_fhs:
        wthr_csv.output_fhs[key].close()
    print('\nFinished processing')

    return

def _fetch_weather(form, climgen, site_rec, pettmp_grid_cell):
    """
    select requested time segment
    """
    func_name = 'make_ecosse_file'

    gran_lat, gran_lon, latitude, longitude, area, mu_globals_props = site_rec
    sims_dir = form.sims_dir
    fut_clim_scen = climgen.fut_clim_scen

    # unpack weather
    # ==============
    pettmp_hist = {}
    pettmp_fut  = {}
    for metric in list(['precipitation','temperature']):
        pettmp_hist[metric] = pettmp_grid_cell[metric][0]
        pettmp_fut[metric]  = pettmp_grid_cell[metric][1]

    sim_start_year = climgen.sim_start_year
    sim_end_year = climgen.sim_end_year

    hist_start_year = form.weather_sets['CRU_hist']['year_start']
    hist_end_year = form.weather_sets['CRU_hist']['year_end']
    fut_start_year = form.weather_sets['ClimGen_A1B']['year_start']

    pettmp_sim = {}
    indx_strt = 12*(sim_start_year - fut_start_year)
    indx_end = 12*(sim_end_year - fut_start_year + 1)
    for metric in pettmp_fut:
        pettmp_sim[metric] = pettmp_fut[metric][indx_strt:indx_end]

    return pettmp_sim

def generate_weather_only(form):
    """
    called from GUI
    """
    if form.hwsd_mu_globals == None:
        print('Undetermined HWSD aoi - please select a valid HSWD csv file')
        return

    # make sure bounding box is correctly set
    # =======================================   

    # lat_ll is the floor i.e. least latitude, of the HWSD aoi which marks the end of the banding loop
    lat_ll = form.hwsd_mu_globals.lat_ll_aoi
    lon_ll = form.hwsd_mu_globals.lon_ll_aoi
    lat_ur = form.hwsd_mu_globals.lat_ur_aoi
    lon_ur = form.hwsd_mu_globals.lon_ur_aoi
    bbox = list([lon_ll, lat_ll, lon_ur, lat_ur])
    form.bbox = bbox

    # weather choice
    # ==============
    weather_resource = form.combo10w.currentText()
    if weather_resource != 'CRU':
        print('Only CRU weather_resource allowed')
        return

    # check requested AOI coordinates against extent of the weather resource dataset
    # ==============================================================================
    if check_clim_nc_limits(form, weather_resource):
        print('Selected ' + weather_resource)
        form.historic_weather_flag = weather_resource
        form.future_climate_flag   = weather_resource
    else:
        return

    # create climate object and generate weather dataset indices enclosing the AOI for the HWSD CSV dataset
    # ======================================================================================================
    climgen = getClimGenNC.ClimGenNC(form)
    sim_start_year = climgen.sim_start_year
    fut_start_year = form.weather_sets['ClimGen_A1B']['year_start']
    mess = 'Simulation start year: {}\tfuture weather dataset start year: {}'.format(sim_start_year, fut_start_year)
    if fut_start_year > sim_start_year:
        print(mess + '\n\tsim start year must be same as or more recent than future dset start year')
        return
    print(mess)

    # Create and initialise CSV object
    # ================================
    wthr_csv = WthrCsvOutputs(form, climgen)
    wthr_csv.create_results_files()

    num_band = 0
    hwsd = hwsd_bil.HWSD_bil(form.lgr, form.hwsd_dir)
    snglPntFlag = False
    aoi_indices_fut, aoi_indices_hist = climgen.genLocalGrid(bbox, hwsd, snglPntFlag)

    '''
    data in historic and future datasets is generally always present for any given grid cell, however, occasionally 
    data may be present in one but not the other 
    '''
    print('Getting future weather data for this HWSD CSV file')
    QApplication.processEvents()
    pettmp_fut = climgen.fetch_cru_future_NC_data(aoi_indices_fut, num_band)
    print('Getting historic weather')
    QApplication.processEvents()
    pettmp_hist = climgen.fetch_cru_historic_NC_data(aoi_indices_hist, num_band)

    # step through each cell
    # ======================
    skipped, completed, warning_count = 3*[0]
    last_time, start_time = 2*[time()]
    ncells = form.hwsd_mu_globals.data_frame.shape[0]
    for index, row in form.hwsd_mu_globals.data_frame.iterrows():
        mu_global = int(row['mu_global'])
        latitude = round(row['latitude'], 5)
        longitude = round(row['longitude'], 5)
        gran_lat = int(row['gran_lat'])
        gran_lon = int(row['gran_lon'])

        site_rec = list([gran_lat, gran_lon, latitude, longitude, mu_global, None])

        pettmp_grid_cell = associate_climate(site_rec, climgen, pettmp_hist, pettmp_fut)
        if len(pettmp_grid_cell) == 0:
            print('*** Warning *** no weather data for site with lat: {}\tlon: {}'
                  .format(round(site_rec[2], 3), round(site_rec[3], 3)))
            continue

        if len(pettmp_grid_cell['precipitation'][0]) == 0:
            mess = 'No historic weather data for lat/lon: {}/{}'.format(row['latitude'], row['longitude'])
            form.lgr.info(mess)
            skipped += 1
            continue

        pettmp_sim = _fetch_weather(form, climgen, site_rec, pettmp_grid_cell)
        for varname, var2 in zip(wthr_csv.writers, pettmp_sim):
            site_rec = list([latitude, longitude, mu_global, gran_lat, gran_lon])
            wthr_csv.writers[varname].writerow(site_rec + pettmp_sim[var2])

        completed += 1
        last_time = update_progress(last_time, start_time, completed, ncells, skipped, warning_count)

    # close CSV files
    # ==============
    for key in wthr_csv.output_fhs:
        wthr_csv.output_fhs[key].close()
    print('\nFinished processing')

    return

class WthrCsvOutputs(object):
    """
    Class to write CSV results of a Spatial ECOSSE run
    """
    def __init__(self, form, climgen):

        self.lgr = form.lgr
        self.varnames = list(['precip','tair'])
        self.sims_dir = form.sims_dir
        self.study = form.w_study.text()
        self.sim_start_year = climgen.sim_start_year
        self.sim_end_year = climgen.sim_end_year

    def create_results_files(self):
        """
        Create empty results files
        """
        size_current = csv.field_size_limit(131072*4)

        self.output_fhs = {}
        self.writers = {}
        hdr_rec = HEADERS
        for year in range(self.sim_start_year, self.sim_end_year + 1):
            for month in range(1, 13):
                hdr_rec.append('{0}-{1:0>2}'.format(str(year), str(month)))

        for varname in self.varnames:
            fname = self.study + '_{0}.txt'.format(varname)
            try:
                self.output_fhs[varname] = open(join(self.sims_dir, fname), 'w', newline='')
            except (OSError, IOError) as err:
                err_mess = 'Unable to open output file. {0}'.format(err)
                self.lgr.critical(err_mess)
                print(err_mess)

            self.writers[varname] = csv.writer(self.output_fhs[varname], delimiter='\t')
            self.writers[varname].writerow(hdr_rec)
        return
