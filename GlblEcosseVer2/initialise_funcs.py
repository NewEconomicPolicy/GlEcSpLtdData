"""
#-------------------------------------------------------------------------------
# Name:        initialise_funcs.py
# Purpose:     script to read read and write the setup and configuration files
# Author:      Mike Martin
# Created:     31/07/2015
# Licence:     <your licence>
#-------------------------------------------------------------------------------
"""

__prog__ = 'initialise_funcs.py'
__version__ = '0.0.0'

# Version history
# ---------------
# 
from os.path import exists, isfile, join
import json

import hwsd_mu_globals_fns
from plant_input_fns import check_plant_input_nc
from shape_funcs import format_bbox, calculate_area
from weather_datasets import change_weather_resource, record_weather_settings
from initialise_common_funcs import check_lu_pi_json_fname
from glbl_ecss_cmmn_cmpntsGUI import calculate_grid_cell
from mngmnt_fns_and_class import check_xls_coords_fname

MIN_GUI_LIST = ['weatherResource', 'aveWthrFlag', 'bbox', 'luPiJsonFname', 'hwsdCsvFname']
CMN_GUI_LIST = ['study', 'histStrtYr', 'histEndYr', 'climScnr', 'futStrtYr', 'futEndYr', 'gridResol', 'eqilMode']
BBOX_DEFAULT = [116.90045, 28.2294, 117.0, 29.0]    # bounding box default - somewhere in SE Europe
sleepTime = 5
ERROR_STR = '*** Error *** '

# ===========================================

def _write_default_config_file(config_file):
    """
    #        ll_lon,    ll_lat  ur_lon,ur_lat
    # stanza if config_file needs to be created
    """
    _default_config = {
        'minGUI': {
            'aveWthrFlag': False,
            'bbox': BBOX_DEFAULT,
            'cordexFlag': 0,
            'hwsdCsvFname': '',
            'luPiJsonFname': '',
            'snglPntFlag': True,
            'usePolyFlag': False
        },
        'cmnGUI': {
            'climScnr' : 'rcp26',
            'eqilMode' : '9.5',
            'futStrtYr': '2006',
            'futEndYr' : '2015',
            'gridResol': 0,
            'histStrtYr': '1980',
            'histEndYr' : '2005',
            'study'    : ''
        }
    }
    # if config file does not exist then create it...
    with open(config_file, 'w') as fconfig:
        json.dump(_default_config, fconfig, indent=2, sort_keys=True)
        fconfig.close()
        return _default_config

def read_config_file(form):
    """
    read widget settings used in the previous programme session from the config file, if it exists,
    or create config file using default settings if config file does not exist
    """
    func_name =  __prog__ +  ' read_config_file'

    config_file = form.config_file
    if exists(config_file):
        try:
            with open(config_file, 'r') as fconfig:
                config = json.load(fconfig)
                fconfig.close()
                print('Read config file ' + config_file)
        except (OSError, IOError) as err:
                print(err)
                return False
    else:
        config = _write_default_config_file(config_file)

    grp = 'minGUI'
    for key in MIN_GUI_LIST:
        if key not in config[grp]:
            print(ERROR_STR + 'setting {} is required in group {} of config file {}'.format(key, grp, config_file))
            form.bbox = BBOX_DEFAULT
            form.csv_fname = ''
            return False

    # added July 2020 to enable MK plant inputs NC file
    # =================================================
    pi_nc_fname = ''
    if 'piNcFname' in config[grp] and 'usePiNcFname' in config[grp]:
        if config[grp]['usePiNcFname']:
            form.w_use_pi_nc.setCheckState(2)
        else:
            form.w_use_pi_nc.setCheckState(0)

        pi_nc_fname = config[grp]['piNcFname']
        form.w_lbl_pi_nc.setText(pi_nc_fname)

    check_plant_input_nc(form, pi_nc_fname)

    # ==== end of MK plant inputs NC file extension =====

    # added March 2021 to enable Marta and Joe plant inputs CSV file
    # ==============================================================
    pi_csv_fname = ''
    if 'piCsvFname' in config[grp] and 'usepiCsvFname' in config[grp]:
        if config[grp]['usepiCsvFname']:
            form.w_use_pi_nc.setCheckState(0)
            form.w_use_pi_csv.setCheckState(2)
        else:
            form.w_use_pi_csv.setCheckState(0)

        pi_csv_fname = config[grp]['piCsvFname']
        form.w_lbl_pi_csv.setText(pi_csv_fname)

    # ==== end of Marta and Joe plant inputs CSV file extension =====

    weather_resource = config[grp]['weatherResource']
    ave_weather = config[grp]['aveWthrFlag']
    form.bbox = config[grp]['bbox']
    lu_pi_json_fname = config[grp]['luPiJsonFname']
    hwsd_csv_fname = config[grp]['hwsdCsvFname']

    form.combo10w.setCurrentText(weather_resource)
    change_weather_resource(form, weather_resource)

    # land use and plant input
    # ========================
    form.w_lbl13.setText(lu_pi_json_fname)
    form.w_lbl14.setText(check_lu_pi_json_fname(form))  # displays file info

    # land uses
    # =========
    grp = 'landuseGUI'
    if grp in config and form.mask_fn is not None:
        for lu in form.w_hilda_lus:
            if config[grp][lu]:
                form.w_hilda_lus[lu].setCheckState(2)
            else:
                form.w_hilda_lus[lu].setCheckState(0)

        form.adjustLuChckBoxes()
    else:
        for lu in form.w_hilda_lus:
            form.w_hilda_lus[lu].setCheckState(0)

    # common area
    # ===========
    grp = 'cmnGUI'
    for key in CMN_GUI_LIST:
        if key not in config[grp]:
            print(ERROR_STR + 'setting {} is required in configuration file {} '.format(key, config_file))
            form.bbox = BBOX_DEFAULT
            form.csv_fname = ''
            return False

    form.w_study.setText(str(config[grp]['study']))
    hist_strt_year = config[grp]['histStrtYr']
    hist_end_year = config[grp]['histEndYr']
    scenario = config[grp]['climScnr']
    sim_strt_year = config[grp]['futStrtYr']
    sim_end_year = config[grp]['futEndYr']
    form.w_equimode.setText(str(config[grp]['eqilMode']))
    form.combo16.setCurrentIndex(config[grp]['gridResol'])

    # record weather settings
    # =======================
    form.wthr_settings_prev[weather_resource] = record_weather_settings(scenario, hist_strt_year, hist_end_year,
                                                                                        sim_strt_year, sim_end_year)
    form.combo09s.setCurrentText(hist_strt_year)
    form.combo09e.setCurrentText(hist_end_year)
    form.combo10.setCurrentText(scenario)
    form.combo11s.setCurrentText(sim_strt_year)
    form.combo11e.setCurrentText(sim_end_year)

    # ===================
    # bounding box set up
    # ===================
    area = calculate_area(form.bbox)
    ll_lon, ll_lat, ur_lon, ur_lat = form.bbox
    form.w_ur_lon.setText(str(ur_lon))
    form.w_ur_lat.setText(str(ur_lat))
    form.fstudy = ''
    form.w_ll_lon.setText(str(ll_lon))
    form.w_ll_lat.setText(str(ll_lat))
    form.w_bbox.setText(format_bbox(form.bbox,area))

    # reset widgets associated with the HWSD file
    # ===========================================
    if hwsd_csv_fname != '':
        if isfile(hwsd_csv_fname):
            # read CSV file using pandas and create obj
            form.hwsd_mu_globals = hwsd_mu_globals_fns.HWSD_mu_globals_csv(form, hwsd_csv_fname)
            form.w_hwsd_bbox.setText(form.hwsd_mu_globals.aoi_label)
        else:
            print('HWSD csv file ' + hwsd_csv_fname + ' does not exist')
            hwsd_csv_fname = ''

    if hwsd_csv_fname == '':
        form.hwsd_mu_globals = None
        form.w_hwsd_bbox.setText('')

    form.w_hwsd_fn.setText(hwsd_csv_fname)

    # set check boxes
    # ===============
    if ave_weather:
        form.w_ave_weather.setCheckState(2)
    else:
        form.w_ave_weather.setCheckState(0)

    # avoids errors when exiting
    # ==========================
    form.req_resol_deg = None
    form.req_resol_granul = None
    form.w_use_dom_soil.setChecked(True)
    form.w_use_high_cover.setChecked(True)

    if form.python_exe == '' or form.runsites_py == '' or form.runsites_config_file is None:
        print('Could not activate Run Ecosse widget - python: {}\trunsites: {}\trunsites_config_file: {}'
                                                .format(form.python_exe, form.runsites_py, form.runsites_config_file))
        form.w_run_ecosse.setEnabled(False)
        form.w_auto_spec.setEnabled(False)

    return True

def write_config_file(form, message_flag = True):
    """
    # write current selections to config file
    """
    study = form.w_study.text()

    # facilitate multiple config file choices
    # =======================================
    glbl_ecsse_str = form.glbl_ecsse_str
    config_file = join(form.config_dir, glbl_ecsse_str + study + '.txt')

    # prepare the bounding box
    # ========================
    ll_lon = 0.0
    ll_lat = 0.0
    try:
        ll_lon = float(form.w_ll_lon.text())
        ll_lat = float(form.w_ll_lat.text())
        ur_lon = float(form.w_ur_lon.text())
        ur_lat = float(form.w_ur_lat.text())
    except ValueError as e:
        print('Problem writing bounding box to config file: ' + str(e))
        ur_lon = 0.0
        ur_lat = 0.0
    form.bbox =  list([ll_lon,ll_lat,ur_lon,ur_lat])

    # TODO: might want to consider where else in the work flow to save these settings
    weather_resource = form.combo10w.currentText()
    scenario         = form.combo10.currentText()
    hist_strt_year   = form.combo09s.currentText()
    hist_end_year    = form.combo09e.currentText()
    sim_strt_year    = form.combo11s.currentText()
    sim_end_year     = form.combo11e.currentText()
    form.wthr_settings_prev[weather_resource] = record_weather_settings(scenario, hist_strt_year, hist_end_year,
                                                                                        sim_strt_year, sim_end_year)
    hwsd_csv_fname = form.w_hwsd_fn.text()
    grid_resol = form.combo16.currentIndex()

    config = {
        'minGUI': {
            'bbox'            : form.bbox,
            'snglPntFlag'     : False,
            'weatherResource' : weather_resource,
            'aveWthrFlag'  : form.w_ave_weather.isChecked(),
            'hwsdCsvFname' : hwsd_csv_fname,
            'luPiJsonFname': form.w_lbl13.text(),
            'piNcFname'    : form.w_lbl_pi_nc.text(),
            'usePiNcFname' : form.w_use_pi_nc.isChecked(),
            'piCsvFname': form.w_lbl_pi_csv.text(),
            'usepiCsvFname': form.w_use_pi_csv.isChecked(),
            'usePolyFlag'  : False
        },
        'cmnGUI': {
            'study'     : form.w_study.text(),
            'histStrtYr': hist_strt_year,
            'histEndYr' : hist_end_year,
            'climScnr'  : scenario,
            'futStrtYr' : sim_strt_year,
            'futEndYr'  : sim_end_year,
            'eqilMode'  : form.w_equimode.text(),
            'gridResol' : grid_resol
            },
        'landuseGUI': {
            'cropland': form.w_hilda_lus['cropland'].isChecked(),     # '', 'grassland', 'all'
            'pasture': form.w_hilda_lus['pasture'].isChecked(),
            'other': form.w_hilda_lus['other'].isChecked(),
            'forest': form.w_hilda_lus['forest'].isChecked(),
            'grassland': form.w_hilda_lus['grassland'].isChecked(),
            'all': form.w_hilda_lus['all'].isChecked()
            }
        }
    if isfile(config_file):
        descriptor = 'Overwrote existing'
    else:
        descriptor = 'Wrote new'
    if study != '':
        with open(config_file, 'w') as fconfig:
            json.dump(config, fconfig, indent=2, sort_keys=True)
            fconfig.close()
            if message_flag:
                print('\n' + descriptor + ' configuration file ' + config_file)
            else:
                print()

def write_study_definition_file(form):
    """
    # write study definition file
    """

    # do not write study def file
    # ===========================
    if 'LandusePI' not in form.lu_pi_content:
        return

    # prepare the bounding box
    # ========================
    ll_lon = 0.0; ll_lat = 0.0
    try:
        ll_lon = float(form.w_ll_lon.text())
        ll_lat = float(form.w_ll_lat.text())
        ur_lon = float(form.w_ur_lon.text())
        ur_lat = float(form.w_ur_lat.text())
    except ValueError:
        ur_lon = 0.0
        ur_lat = 0.0
    bbox =  list([ll_lon,ll_lat,ur_lon,ur_lat])
    study = form.w_study.text()

    weather_resource = form.combo10w.currentText()
    if weather_resource == 'CRU':
        fut_clim_scen = form.combo10.currentText()
    else:
        fut_clim_scen = weather_resource

    # construct land_use change - not elegant but adequate
    # =========================
    land_use = ''
    try:
        for indx in form.lu_pi_content['LandusePI']:
            lu, pi = form.lu_pi_content['LandusePI'][indx]
            land_use += form.lu_type_abbrevs[lu] + '2'
    except AttributeError as e:
        print(e)
        return

    land_use = land_use.rstrip('2')

    # convert resolution to granular then to decimal
    # ==============================================
    hwsd_csv_fname = form.w_hwsd_fn.text()
    resol_decimal = calculate_grid_cell(form)
    study_defn = {
        'studyDefn': {
            'bbox'     : bbox,
            "luPiJsonFname": form.w_lbl13.text(),
            'hwsdCsvFname' : hwsd_csv_fname,
            'study'    : study,
            'land_use' : land_use,
            'histStrtYr': form.combo09s.currentText(),
            'histEndYr' : form.combo09e.currentText(),
            'climScnr' : fut_clim_scen,
            'futStrtYr': form.combo11s.currentText(),
            'futEndYr' : form.combo11e.currentText(),
            'province' : 'xxxx',
            'resolution': resol_decimal,
            'shpe_file': 'xxxx',
            'version'  : form.version
            }
        }

    # copy to sims area
    # =================
    if study == '':
        print('*** Warning *** study not defined  - could not write study definition file')
    else:
        study_defn_file = join(form.sims_dir, study + '_study_definition.txt')
        with open(study_defn_file, 'w') as fstudy:
            json.dump(study_defn, fstudy, indent=2, sort_keys=True)
            print('\nWrote study definition file ' + study_defn_file)

    return
