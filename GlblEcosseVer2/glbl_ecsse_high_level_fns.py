"""
#-------------------------------------------------------------------------------
# Name:        hwsd_glblecsse_fns.py
# Purpose:     consist of high level functions invoked by main GUI
# Author:      Mike Martin
# Created:     11/12/2015
# Licence:     <your licence>
# Description:
#   comprises two functions:
#       def _generate_ecosse_files(form, climgen, num_band)
#       def generate_banded_sims(form)
#-------------------------------------------------------------------------------
#
"""

__prog__ = 'glbl_ecsse_high_level_fns.py'
__version__ = '0.0.1'
__author__ = 's03mm5'

from time import time
from operator import itemgetter
from copy import copy
from netCDF4 import Dataset
from PyQt5.QtWidgets import QApplication

from make_ltd_data_files import MakeLtdDataFiles
from getClimGenNC import ClimGenNC

from getClimGenFns import check_clim_nc_limits, associate_climate
from getClimGenOsbgFns import fetch_chess_bbox_indices
import hwsd_bil
from hwsd_mu_globals_fns import gen_grid_cells_for_band
from plant_input_fns import fetch_yields, associate_yield, associate_yield_nc
from plant_input_csv_fns import associate_plant_inputs, cnvrt_joe_plant_inputs_to_df
from prepare_ecosse_files import update_progress, make_ecosse_file
from mngmnt_fns_and_class import ManagementSet, check_mask_location

WARN_STR = '*** Warning *** '
MASK_FLAG = False

def simplify_soil_recs(soil_recs, use_dom_soil_flag):
    """
    compress soil records if duplicates are present
    simplify soil records if requested
    each mu_global points to a group of soils
    a soil group can have up to ten soils
    """
    func_name =  __prog__ + ' _simplify_soil_recs'

    num_raw = 0 # total number of sub-soils
    num_compress = 0 # total number of sub-soils after compressions

    new_soil_recs = {}
    for mu_global in soil_recs:

        # no processing necessary
        # =======================
        num_sub_soils = len(soil_recs[mu_global])
        num_raw += num_sub_soils
        if num_sub_soils == 1:
            num_compress += 1
            new_soil_recs[mu_global] = soil_recs[mu_global]
            continue

        # check each soil for duplicates
        # ==============================
        new_soil_group = []
        soil_group = sorted(soil_recs[mu_global])

        # skip empty groups
        # =================
        if len(soil_group) == 0:
            continue

        first_soil = soil_group[0]
        metrics1 = first_soil[:-1]
        share1   = first_soil[-1]
        for soil in soil_group[1:]:
            metrics2 = soil[:-1]
            share2 =   soil[-1]
            if metrics1 == metrics2:
                share1 += share2
            else:
                new_soil_group.append(metrics1 + [share1])
                metrics1 = metrics2
                share1 = share2

        new_soil_group.append(metrics1 + [share1])
        num_sub_soils = len(new_soil_group)
        num_compress += num_sub_soils
        if num_sub_soils == 1:
            new_soil_recs[mu_global] = new_soil_group
            continue

        if use_dom_soil_flag:
            # assign 100% to the first entry of sorted list
            # =============================================
            dom_soil = copy(sorted(new_soil_group, reverse = True, key=itemgetter(-1))[0])
            dom_soil[-1] = 100.0
            new_soil_recs[mu_global] = list([dom_soil])

    mess = 'Leaving {}\trecords in: {} out: {}'.format(func_name, len(soil_recs),len(new_soil_recs))
    print(mess + '\tnum raw sub-soils: {}\tafter compression: {}'.format(num_raw, num_compress))
    return new_soil_recs

def _simplify_aoi(lggr, num_band, aoi_res):
    """
    simplify AOI records
    """
    aoi_res_new = []
    nskipped = 0
    for site_rec in aoi_res:
        content = site_rec[-1]
        npairs = len(content)
        if npairs == 0:
            lggr.info('No soil information for AOI cell {} - will skip'.format(site_rec))
            nskipped += 1
        elif npairs == 1:
            aoi_res_new.append(site_rec)
        else:
            site_rec_list = list(site_rec)  # convert tuple to a list so we can edit last element
            new_content = sorted(content.items(), reverse = True, key = itemgetter(1))  # sort content so we can pick up most dominant mu_global
            total_proportion = sum(content.values())    # add up proportions
            site_rec_list[-1] = {new_content[0][0]: total_proportion}       # create a new single mu global with summed proportions

            aoi_res_new.append(tuple(site_rec_list)) # convert list to tuple

    if nskipped > 0:
        mess = 'No soil information for {} AOI cells for band {}'.format(nskipped, num_band)
        print(mess); lggr.info(mess)

    return aoi_res_new

def _generate_ecosse_files(form, climgen, chess_extent, mask_defn, yield_df, num_band, yield_defn, pi_var, pi_csv_tple):
    """
    Main loop for generating ECOSSE outputs
    """
    func_name =  __prog__ + '\t_generate_ecosse_files'

    study = form.study
    print('Gathering soil and climate data for study {}...\t\tin {}'.format(study,func_name))
    snglPntFlag = False

    # instantiate a soil grid and climate objects
    hwsd = hwsd_bil.HWSD_bil(form.lgr, form.hwsd_dir)

    # add requested grid resolution attributes to the form object
    bbox = form.sttngs['bbox']

    # create grid of mu_globals based on bounding box
    # ===============================================
    nvals_read = hwsd.read_bbox_hwsd_mu_globals(bbox, form.hwsd_mu_globals, form.sttngs['req_resol_upscale'])

    # retrieve dictionary consisting of mu_globals (keys) and number of occurences (values)
    # =====================================================================================
    mu_globals = hwsd.get_mu_globals_dict()
    if mu_globals is None:
        print('No soil records for AOI: {}\n'.format(bbox))
        return

    mess = 'Retrieved {} values  of HWSD grid consisting of {} rows and {} columns: ' \
          '\n\tnumber of unique mu_globals: {}'.format(nvals_read, hwsd.nlats, hwsd.nlons, len(mu_globals))
    form.lgr.info(mess)

    # create soil records for each grid point
    # =======================================
    hwsd.bad_muglobals = form.hwsd_mu_globals.bad_mu_globals
    aoi_res, bbox = gen_grid_cells_for_band(hwsd, form.sttngs['req_resol_upscale'])
    if form.w_use_high_cover.isChecked():
        aoi_res =  _simplify_aoi(form.lgr, num_band, aoi_res)

    lon_ll_aoi, lat_ll_aoi, lon_ur_aoi, lat_ur_aoi = bbox
    num_meta_cells = len(aoi_res)
    print('Band aoi LL lon/lat: {} {}\tUR lon/lat: {} {}\t# meta cells: {}'
                            .format(lon_ll_aoi, lat_ll_aoi, lon_ur_aoi, lat_ur_aoi, num_meta_cells))
    if num_meta_cells == 0:
        mess = 'No aoi_res recs therefore unable to create simulation files... \n'
        print(mess); form.lgr.info(mess)
        return

    # 4.5 = estimated mean number of dominant soils per cell
    # ======================================================
    est_num_sims = 0
    for site_rec in aoi_res:
        est_num_sims += len(site_rec[-1])
    est_num_sims = int(est_num_sims * 4.5)
    mess = 'Generated {} Area of Interest grid cell records for band {} which will result in an estimated {} simulations'\
                                    .format(num_meta_cells, num_band, est_num_sims)
    form.lgr.info(mess); print(mess)

    # generate weather dataset indices which enclose the AOI for this band
    # ====================================================================
    #indx_nrth_ll, indx_nrth_ur, indx_east_ll, indx_east_ur, nrthng_ll, nrthng_ur, eastng_ll, eastng_ur = chess_extent
    # =============================
    wthr_rsrc = climgen.wthr_rsrc

    print('Getting future ' + wthr_rsrc + ' data for band {}'.format(num_band))
    QApplication.processEvents()
    mess = 'Getting historic ' + wthr_rsrc + 'data for band {}'.format(num_band)

    if wthr_rsrc == 'CHESS':
        aoi_indices = chess_extent[:4]
        pettmp_fut = climgen.fetch_chess_NC_data(aoi_indices, num_band)
        print(mess)
        pettmp_hist = climgen.fetch_chess_NC_data(aoi_indices, num_band, future_flag = False)
    else:
        aoi_indices_fut, aoi_indices_hist = climgen.genLocalGrid(bbox, hwsd, snglPntFlag, num_band)
        pettmp_fut = climgen.fetch_cru_future_NC_data(aoi_indices_fut, num_band)
        print(mess)
        pettmp_hist = climgen.fetch_cru_historic_NC_data(aoi_indices_hist, num_band)

    print('Creating simulation files for band {}...'.format(num_band))
    #      =========================================

    # Initialise the limited data object with general settings that do not change between simulations
    # ===============================================================================================
    ltd_data = MakeLtdDataFiles(form, climgen, comments=True) # create limited data object

    # open plant input NC dataset
    # ===========================
    if mask_defn is not None:
        mask_defn.nc_dset = Dataset(mask_defn.nc_fname, mode='r')

    if pi_var is not None:
        yield_dset = Dataset(yield_defn.nc_fname, mode='r')

    if pi_csv_tple is not None:
        strt_year, nyears, pi_df = pi_csv_tple

    last_time = time()
    completed = 0
    skipped = 0
    landuse_yes = 0
    landuse_no = 0
    warning_count = 0

    land_use = 'forest'     # TODO

    # generate sets of Ecosse files for each site where each site has one or more soils
    # each soil can have one or more dominant soils
    # =======================================================================
    for site_indx, site_rec in enumerate(aoi_res):

        # help with debug
        if site_indx == 9:
            print()

        pettmp_grid_cell = associate_climate(site_rec, climgen, pettmp_hist, pettmp_fut)
        if len(pettmp_grid_cell) == 0:
            print('*** Warning *** no wthr data for site with lat: {}\tlon: {}'
                                                        .format(round(site_rec[2],3), round(site_rec[3],3)))
            continue

        # land use mask
        # =============
        if mask_defn is not None:            
            if check_mask_location(mask_defn, site_rec, land_use, form.req_resol_deg):
                landuse_yes += 1
            else:
                landuse_no += 1
                skipped += 1
                continue

        gran_lat, gran_lon, latitude, longitude, area, mu_globals_props = site_rec
        if len(pettmp_grid_cell['precipitation'][0]) == 0:
            mess = 'No weather data for lat/lon: {}/{}\tgranular lat/lon: {}/{}'\
                                                                    .format(latitude, longitude, gran_lat, gran_lon)
            form.lgr.info(mess)
            skipped += 1
        else:
            if yield_df is not None:
                associate_yield(form.lgr.info, latitude, longitude, ltd_data, yield_df)        # modify ltd_data object
            elif pi_var is not None:
                associate_yield_nc(form.lgr.info, latitude, longitude, ltd_data, yield_defn, yield_dset, pi_var)
            elif pi_csv_tple is not None:
                associate_plant_inputs(form.lgr.info, strt_year, gran_lat, gran_lon, pi_df, ltd_data)

            make_ecosse_file(form, climgen, ltd_data, site_rec, study, pettmp_grid_cell)
            completed += 1
            if completed >= form.sttngs['completed_max']:
                print(WARN_STR + 'Exited after {} cells completed'.format(completed) )
                break

        last_time = update_progress(last_time, completed, num_meta_cells, skipped, warning_count, form.w_prgrss)

    # close plant input NC dataset
    # ============================
    if pi_var is not None:
        yield_dset.close()

    if mask_defn is not None:
        mask_defn.nc_dset.close()
        print('\nBand: {}\tLU yes: {}  no: {}\tskipped: {}\tcompleted: {}'
              .format(num_band, landuse_yes, landuse_no, skipped, completed))

    print('')   # spacer
    return

def generate_banded_sims(form):
    '''
    called from GUI
    '''
    if form.w_use_dom_soil.isChecked():
        dom_soil_flag = True
    else:
        dom_soil_flag = False

    # make sure bounding box is correctly set
    # =======================================
    lon_ll = float(form.w_ll_lon.text())
    lat_ll = float(form.w_ll_lat.text())
    lon_ur = float(form.w_ur_lon.text())
    lat_ur = float(form.w_ur_lat.text())
    form.sttngs['bbox'] =  list([lon_ll, lat_ll, lon_ur, lat_ur])

    # ==========
    chess_extent = fetch_chess_bbox_indices(lon_ll, lat_ll, lon_ur, lat_ur)

    # weather choice
    # ==============
    wthr_rsrc = form.combo10w.currentText()

    # check requested AOI coordinates against extent of the weather resource dataset
    # ==============================================================================
    if check_clim_nc_limits(form, wthr_rsrc, form.sttngs['bbox']):
        print('Selected ' + wthr_rsrc)
        form.historic_wthr_flag = wthr_rsrc
        form.future_climate_flag   = wthr_rsrc
    else:
        return

    # mask
    # ====
    if MASK_FLAG and form.mask_fn is not None:
        mask_defn = ManagementSet(form.mask_fn, 'cropmasks')   # mask
    else:
        mask_defn = None

    # check plant inputs NC and open
    # ==============================
    pi_var = None
    yield_defn = None
    pi_csv_tple = None
    if form.w_use_pi_nc.isChecked():
        pi_var = form.w_combo15.currentText()   # Select PI NC variable - start with: PlantInput e.g. PlantInput05
        if pi_var == '':
            pi_var = None   # could happen for EU28_cropland_npp.nc
        else:
            # open plant input NC dataset
            # ===========================
            pi_nc_fname = form.w_lbl_pi_nc.text()
            yield_defn = ManagementSet(pi_nc_fname, 'yields')
            print('*** Please note *** Will use yields from variable: ' + pi_var + ' in NC dataset: ' + pi_nc_fname)

    # print('Study bounding box and HWSD CSV file overlap')
    #        ============================================
    start_at_band = form.sttngs['start_at_band']
    print('Starting at band {}'.format(start_at_band))
    yield_df = fetch_yields(form)

    # trap situation where both methods of including external plant inputs are active
    # ===============================================================================
    if pi_var is not None and yield_df is not None:
        print('*** Warning *** disabled yield map specified')
        yield_df = None

    # extract required values from the HWSD database and simplify if requested
    # ========================================================================
    hwsd = hwsd_bil.HWSD_bil(form.lgr, form.hwsd_dir)

    # TODO: patch to be sorted
    # ========================
    mu_global_pairs = {}
    for mu_global in form.hwsd_mu_globals.mu_global_list:
        mu_global_pairs[mu_global] = None

    soil_recs = hwsd.get_soil_recs(mu_global_pairs)  # list is already sorted
    for mu_global in hwsd.bad_muglobals:
        del(soil_recs[mu_global])

    form.hwsd_mu_globals.soil_recs = simplify_soil_recs(soil_recs, dom_soil_flag)
    form.hwsd_mu_globals.bad_mu_globals = [0] +  hwsd.bad_muglobals
    del(hwsd); del(soil_recs)

    # create climate object
    # =====================
    climgen = ClimGenNC(form)

    # main banding loop
    # =================
    lat_step = 0.5
    nsteps = int((lat_ur-lat_ll)/lat_step) + 1
    for isec in range(nsteps):
        lat_ll_new = lat_ur - lat_step
        num_band = isec + 1

        # if the latitude floor of the band has not reached the ceiling of the HWSD aoi then skip this band
        # =================================================================================================
        if lat_ll_new > form.hwsd_mu_globals.lat_ur_aoi or num_band < start_at_band:
            print('Skipping out of area band {} of {} with latitude extent of min: {}\tmax: {}\n'
                                                    .format(num_band, nsteps, round(lat_ll_new,6), round(lat_ur, 6)))
        else:
            form.sttngs['bbox'] = list([lon_ll, lat_ll_new, lon_ur, lat_ur])

            print('\nProcessing band {} of {} with latitude extent of min: {}\tmax: {}'
                  .format(num_band, nsteps, round(lat_ll_new,6), round(lat_ur, 6)))

            # does actual work
            # ================
            _generate_ecosse_files(form, climgen, chess_extent, mask_defn, yield_df, num_band,
                                                                        yield_defn, pi_var, pi_csv_tple)

        # check to see if the last band is completed
        # ==========================================
        lat_ll_aoi = form.hwsd_mu_globals.lat_ll_aoi
        if lat_ll_aoi > lat_ll_new or num_band == nsteps:
            print('Finished processing after {} bands of latitude extents'.format(num_band))
            for ichan in range(len(form.fstudy)):
                form.fstudy[ichan].close()
            break

        lat_ur = lat_ll_new

    return
