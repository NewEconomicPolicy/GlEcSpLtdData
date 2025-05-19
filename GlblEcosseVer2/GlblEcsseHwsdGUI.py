# -------------------------------------------------------------------------------
# Name:
# Purpose:     Creates a GUI with five adminstrative levels plus country
# Author:      Mike Martin
# Created:     11/12/2015
# Licence:     <your licence>
# -------------------------------------------------------------------------------

__prog__ = 'GlblEcsseHwsdGUI.py'
__version__ = '0.0.1'
__author__ = 's03mm5'

import sys
from os.path import normpath
from os import system, getcwd
from time import time

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtWidgets import (QLabel, QWidget, QApplication, QHBoxLayout, QVBoxLayout, QGridLayout, QLineEdit,
                             QComboBox, QPushButton, QCheckBox, QFileDialog, QTextEdit)

from common_componentsGUI import (exit_clicked, commonSection, changeConfigFile, studyTextChanged, save_clicked)
from glbl_ecss_cmmn_cmpntsGUI import calculate_grid_cell, grid_resolutions

from shape_funcs import format_bbox, calculate_area
from glbl_ecsse_high_level_fns import generate_banded_sims
from glbl_ecsse_wthr_only_fns import generate_weather_only, generate_soil_output

from weather_datasets import change_weather_resource
import hwsd_mu_globals_fns
from initialise_funcs import read_config_file, check_lu_pi_json_fname
from initialise_common_funcs import initiation, build_and_display_studies, write_runsites_config_file
from mngmnt_fns_and_class import check_xls_coords_fname
from plant_input_fns import check_plant_input_nc
from set_up_logging import OutLog

STD_BTN_SIZE_100 = 100
STD_BTN_SIZE_80 = 80
STD_FLD_SIZE_180 = 180

ERROR_STR = '*** Error *** '
WARN_STR = '*** Warning *** '

# ========================

class Form(QWidget):
    """
    C
    """
    def __init__(self, parent=None):

        super(Form, self).__init__(parent)

        self.version = 'HWSD_grid'
        initiation(self)
        font = QFont(self.font())
        font.setPointSize(font.pointSize() + 2)
        self.setFont(font)

        # The layout is done with the QGridLayout
        grid = QGridLayout()
        grid.setSpacing(10)  # set spacing between widgets

        # line 0
        # ======
        irow = 0
        lbl00 = QLabel('Study:')
        lbl00.setAlignment(Qt.AlignRight)
        grid.addWidget(lbl00, irow, 0)

        w_study = QLineEdit()
        w_study.setFixedWidth(STD_FLD_SIZE_180)
        grid.addWidget(w_study, irow, 1, 1, 2)
        self.w_study = w_study

        lbl00s = QLabel('studies:')
        lbl00s.setAlignment(Qt.AlignRight)
        helpText = 'list of studies'
        lbl00s.setToolTip(helpText)
        grid.addWidget(lbl00s, irow, 3)

        combo00s = QComboBox()
        for study in self.studies:
            combo00s.addItem(study)
        grid.addWidget(combo00s, irow, 4, 1, 2)
        combo00s.currentIndexChanged[str].connect(self.changeConfigFile)
        self.combo00s = combo00s

        # UR lon/lat
        # ==========
        irow += 1
        lbl02a = QLabel('Upper right longitude:')
        lbl02a.setAlignment(Qt.AlignRight)
        grid.addWidget(lbl02a, irow, 0)

        w_ur_lon = QLineEdit()
        grid.addWidget(w_ur_lon, irow, 1)
        self.w_ur_lon = w_ur_lon

        lbl02b = QLabel('latitude:')
        lbl02b.setAlignment(Qt.AlignRight)
        grid.addWidget(lbl02b, irow, 2)

        w_ur_lat = QLineEdit()
        w_ur_lat.setFixedWidth(80)
        grid.addWidget(w_ur_lat, irow, 3)
        self.w_ur_lat = w_ur_lat

        # LL lon/lat
        # ==========
        irow += 1
        lbl01a = QLabel('Lower left longitude:')
        lbl01a.setAlignment(Qt.AlignRight)
        grid.addWidget(lbl01a, irow, 0)

        w_ll_lon = QLineEdit()
        grid.addWidget(w_ll_lon, irow, 1)
        self.w_ll_lon = w_ll_lon

        lbl01b = QLabel('latitude:')
        lbl01b.setAlignment(Qt.AlignRight)
        grid.addWidget(lbl01b, irow, 2)

        w_ll_lat = QLineEdit()
        grid.addWidget(w_ll_lat, irow, 3)
        w_ll_lat.setFixedWidth(80)
        self.w_ll_lat = w_ll_lat

        # bbox
        # ====
        irow += 1
        lbl03a = QLabel('Study bounding box:')
        lbl03a.setAlignment(Qt.AlignRight)
        grid.addWidget(lbl03a, irow, 0)

        self.w_bbox = QLabel()
        grid.addWidget(self.w_bbox, irow, 1, 1, 5)

        # soil switches
        # =============
        irow += 1
        lbl04 = QLabel('Options:')
        lbl04.setAlignment(Qt.AlignRight)
        grid.addWidget(lbl04, irow, 0)

        w_use_dom_soil = QCheckBox('Use most dominant soil')
        helpText = 'Each HWSD grid cell can have up to 10 soils. Select this option to use most dominant soil and\n' \
                   ' discard all others. The the most dominant soil is defined as having the highest percentage coverage ' \
                   ' of all the soils for that grid cell'
        w_use_dom_soil.setToolTip(helpText)
        grid.addWidget(w_use_dom_soil, irow, 1, 1, 2)
        self.w_use_dom_soil = w_use_dom_soil

        w_use_high_cover = QCheckBox('Use highest coverage soil')
        helpText = 'Each meta-cell has one or more HWSD mu global keys with each key associated with a coverage expressed \n' \
                   ' as a proportion of the area of the meta cell. Select this option to use the mu global with the highest coverage,\n' \
                   ' discard the others and aggregate their coverages to the selected mu global'
        w_use_high_cover.setToolTip(helpText)
        grid.addWidget(w_use_high_cover, irow, 3, 1, 2)
        self.w_use_high_cover = w_use_high_cover

        # line 6 - option to use CSV file of cells
        # ========================================
        irow += 1
        w_use_csv_file = QPushButton("HWSD CSV file")
        helpText = 'Option to enable user to select a CSV file comprising latitude, longitiude and HWSD mu_global.'
        w_use_csv_file.setToolTip(helpText)
        grid.addWidget(w_use_csv_file, irow, 1)
        w_use_csv_file.clicked.connect(self.fetchCsvFile)

        w_hwsd_fn = QLabel('')  # label for HWSD csv file name
        grid.addWidget(w_hwsd_fn, irow, 2, 1, 5)
        self.w_hwsd_fn = w_hwsd_fn

        # HWSD AOI bounding box detail
        # ============================
        irow += 1
        w_lbl07 = QLabel('HWSD bounding box:')
        w_lbl07.setAlignment(Qt.AlignRight)
        grid.addWidget(w_lbl07, irow, 0)

        self.w_hwsd_bbox = QLabel('')
        grid.addWidget(self.w_hwsd_bbox, irow, 2, 1, 5)

        irow += 1
        grid.addWidget(QLabel(''), irow, 2)  # spacer

        # create weather and grid resolution
        # ==================================
        irow = commonSection(self, grid, irow)
        irow = grid_resolutions(self, grid, irow)

        # command line
        # ============
        irow += 1
        w_create_files = QPushButton("Create sim files")
        helpText = 'Generate ECOSSE simulation file sets corresponding to ordered HWSD global mapping unit set in CSV file'
        w_create_files.setToolTip(helpText)
        w_create_files.setEnabled(False)
        w_create_files.setFixedWidth(STD_BTN_SIZE_100)
        grid.addWidget(w_create_files, irow, 0, )
        w_create_files.clicked.connect(self.createSimsClicked)
        self.w_create_files = w_create_files

        w_auto_spec = QCheckBox('Auto run Ecosse')
        helpText = 'Select this option to automatically run Ecosse'
        w_auto_spec.setToolTip(helpText)
        grid.addWidget(w_auto_spec, irow, 1)
        self.w_auto_spec = w_auto_spec

        w_run_ecosse = QPushButton('Run Ecosse')
        helpText = 'Select this option to create a configuration file for the spec.py script and run it.\n' \
                   + 'The spec.py script runs the ECOSSE programme'
        w_run_ecosse.setToolTip(helpText)
        w_run_ecosse.setFixedWidth(STD_BTN_SIZE_80)
        w_run_ecosse.clicked.connect(self.runEcosseClicked)
        grid.addWidget(w_run_ecosse, irow, 2)
        self.w_run_ecosse = w_run_ecosse

        w_save = QPushButton("Save")
        helpText = 'Save configuration and study definition files'
        w_save.setToolTip(helpText)
        w_save.setFixedWidth(STD_BTN_SIZE_80)
        grid.addWidget(w_save, irow, 3)
        w_save.clicked.connect(self.saveClicked)

        w_cancel = QPushButton("Cancel")
        helpText = 'Leaves GUI without saving configuration and study definition files'
        w_cancel.setToolTip(helpText)
        w_cancel.setFixedWidth(STD_BTN_SIZE_80)
        grid.addWidget(w_cancel, irow, 4)
        w_cancel.clicked.connect(self.cancelClicked)

        w_exit = QPushButton("Exit", self)
        grid.addWidget(w_exit, irow, 5)
        w_exit.setFixedWidth(STD_BTN_SIZE_80)
        w_exit.clicked.connect(self.exitClicked)

        # =======
        w_wthr = QPushButton("Wthr only")
        helpText = 'Generate CSV weather data based on HWSD file for Marta-Joe project'
        w_wthr.setToolTip(helpText)
        w_wthr.setFixedWidth(STD_BTN_SIZE_100)
        grid.addWidget(w_wthr, irow, 6)
        w_wthr.clicked.connect(self.genWthrOnlyClicked)
        self.w_wthr = w_wthr

        # =============================================
        irow += 1
        lbl02a = QLabel('Maximum cells:')
        lbl02a.setAlignment(Qt.AlignRight)
        grid.addWidget(lbl02a, irow, 0)

        w_max_cells = QLineEdit()
        grid.addWidget(w_max_cells, irow, 1)
        self.w_max_cells = w_max_cells

        w_soil_outpts = QPushButton("Make soil files")
        helpText = 'For the HoliSoils project - not developed'
        w_soil_outpts.setToolTip(helpText)
        w_soil_outpts.setFixedWidth(STD_BTN_SIZE_100)
        grid.addWidget(w_soil_outpts, irow, 6)
        w_soil_outpts.clicked.connect(self.genSoilOutptsClicked)
        w_soil_outpts.setEnabled(False)
        self.w_soil_outpts = w_soil_outpts

        # LH vertical box consists of png image
        # =====================================
        lh_vbox = QVBoxLayout()

        lbl20 = QLabel()
        lbl20.setPixmap(QPixmap(self.fname_png))
        lbl20.setScaledContents(True)
        lh_vbox.addWidget(lbl20)

        # add grid consisting of combo boxes, labels and buttons to RH vertical box
        # =========================================================================
        rh_vbox = QVBoxLayout()
        rh_vbox.addLayout(grid)

        # add reporting
        # =============
        bot_hbox = QHBoxLayout()
        w_report = QTextEdit()
        w_report.verticalScrollBar().minimum()
        w_report.setMinimumHeight(225)
        w_report.setMinimumWidth(1000)
        w_report.setStyleSheet('font: bold 10.5pt Courier')  # big jump to 11pt
        bot_hbox.addWidget(w_report, 1)
        self.w_report = w_report

        sys.stdout = OutLog(self.w_report, sys.stdout)
        # sys.stderr = OutLog(self.w_report, sys.stderr, QColor(255, 0, 0))

        # add LH and RH vertical boxes to main horizontal box
        # ===================================================
        main_hbox = QHBoxLayout()
        main_hbox.setSpacing(10)
        main_hbox.addLayout(lh_vbox)
        main_hbox.addLayout(rh_vbox, stretch=1)

        # feed horizontal boxes into the window
        # =====================================
        outer_layout = QVBoxLayout()
        outer_layout.addLayout(main_hbox)
        outer_layout.addLayout(bot_hbox)
        self.setLayout(outer_layout)

        # posx, posy, width, height
        self.setGeometry(200, 100, 690, 250)
        self.setWindowTitle('Generic Global Ecosse - generate sets of limited data ECOSSE input files based on HWSD grid')

        # reads and set values from last run
        # ==================================
        read_config_file(self)

        self.combo10w.currentIndexChanged[str].connect(self.weatherResourceChanged)
        # self.w_study.textChanged[str].connect(self.studyTextChanged)
        self.w_ll_lat.textChanged[str].connect(self.bboxTextChanged)
        self.w_ll_lon.textChanged[str].connect(self.bboxTextChanged)
        self.w_ur_lat.textChanged[str].connect(self.bboxTextChanged)
        self.w_ur_lon.textChanged[str].connect(self.bboxTextChanged)

    def keyPress(self, bttnWdgtId):
        """

        """
        pass
        # print("Key was pressed, id is: ", self.w_inpt_choice.id(bttnWdgtId))

    def genSoilOutptsClicked(self):
        """

        """
        generate_soil_output(self)

    def adjustLuChckBoxes(self):
        """

        """
        for lu in self.w_hilda_lus:
            if lu == 'all':
                continue
            else:
                if self.w_hilda_lus['all'].isChecked():
                    self.w_hilda_lus[lu].setEnabled(False)
                else:
                    self.w_hilda_lus[lu].setEnabled(True)
        return

    def genWthrOnlyClicked(self):
        """

        """
        generate_weather_only(self)

    def weatherResourceChanged(self):
        """

        """
        change_weather_resource(self)

    def fetchCsvFile(self):
        """
        QFileDialog returns a tuple for Python 3.5, 3.6
        """
        fname = self.w_hwsd_fn.text()
        if fname == '':
            fname = self.images_dir
        fname, dummy = QFileDialog.getOpenFileName(self, 'Open file', fname, 'CSV files (*.csv)')
        if fname != '':
            self.w_hwsd_fn.setText(fname)
            self.hwsd_mu_globals = hwsd_mu_globals_fns.HWSD_mu_globals_csv(self, fname)
            self.mu_global_list = self.hwsd_mu_globals.mu_global_list
            self.w_hwsd_bbox.setText(self.hwsd_mu_globals.aoi_label)

    def fetchLuPiJsonFile(self):
        """
        QFileDialog returns a tuple for Python 3.5, 3.6
        """
        fname = self.w_lbl13.text()
        fname, dummy = QFileDialog.getOpenFileName(self, 'Open file', fname, 'JSON files (*.json)')
        if fname != '':
            self.w_lbl13.setText(fname)
            self.w_lbl14.setText(check_lu_pi_json_fname(self))

    def resolutionChanged(self):
        """

        """
        granularity = 120
        calculate_grid_cell(self, granularity)

    def studyTextChanged(self):
        """

        """
        studyTextChanged(self)

    def bboxTextChanged(self):
        """

        """
        try:
            bbox = list([float(self.w_ll_lon.text()), float(self.w_ll_lat.text()),
                         float(self.w_ur_lon.text()), float(self.w_ur_lat.text())])
            area = calculate_area(bbox)
            self.w_bbox.setText(format_bbox(bbox, area))
            self.bbox = bbox
        except ValueError as e:
            pass

    def createSimsClicked(self):
        """

        """
        study = self.w_study.text()
        if study == '':
            print('study cannot be blank')
            return

        # check for spaces
        # ================
        if study.find(' ') >= 0:
            print('*** study name must not have spaces ***')
            return

        self.study = study

        generate_banded_sims(self)

        # run further steps...
        if self.w_auto_spec.isChecked():
            self.runEcosseClicked()

    def runEcosseClicked(self):
        """
        NB components of the command string have been checked at startup
        """
        if write_runsites_config_file(self):
            # run the make simulations script
            # ===============================
            print('Working dir: ' + getcwd())
            start_time = time()
            cmd_str = self.python_exe + ' ' + self.runsites_py + ' ' + self.runsites_config_file
            system(cmd_str)
            end_time = time()
            print('Time taken: {}'.format(round(end_time - start_time)))

    def saveClicked(self):
        """

        """
        study = self.w_study.text()
        if study == '':
            print('study cannot be blank')
        else:
            if study.find(' ') >= 0:
                print('*** study name must not have spaces ***')
            else:
                save_clicked(self)
                build_and_display_studies(self)

    def cancelClicked(self):
        """

        """
        exit_clicked(self, write_config_flag=False)

    def exitClicked(self):
        """
        exit cleanly
        """
        study = self.w_study.text()
        if study == '':
            print('study cannot be blank')
        else:
            if study.find(' ') >= 0:
                print('*** study name must not have spaces ***')
            else:
                exit_clicked(self)

    def changeConfigFile(self):
        """
        permits change of configuration file
        """
        changeConfigFile(self)

    def fetchPiCsvFile(self):
        """
        Select CSV file of plant inputs
        """
        fname = self.w_lbl_pi_csv.text()
        fname, dummy = QFileDialog.getOpenFileName(self, 'Select CSV of plant inputs', fname, 'CSV file (*.csv)')
        fname = normpath(fname)
        if fname != '':
            self.w_lbl_pi_csv.setText(fname)

    def fetchPiNcFile(self):
        """
        Select NetCDF file of plant inputs
        if user canels then fname is returned as an empty string
        """
        fname = self.w_lbl_pi_nc.text()
        fname, dummy = QFileDialog.getOpenFileName(self, 'Select NetCDF of plant inputs', fname, 'NetCDF file (*.nc)')
        if fname != '':
            fname = normpath(fname)
            check_plant_input_nc(self, fname)
            self.w_lbl_pi_nc.setText(fname)

    def adustPiCsv(self):
        """

        """
        if self.w_use_pi_nc.isChecked():
            self.w_use_pi_csv.setCheckState(0)

    def adustPiNc(self):
        """

        """
        if self.w_use_pi_csv.isChecked():
            self.w_use_pi_nc.setCheckState(0)

def main():
    """

    """
    app = QApplication(sys.argv)  # create QApplication object
    form = Form()  # instantiate form
    # display the GUI and start the event loop if we're not running batch mode
    form.show()  # paint form
    sys.exit(app.exec_())  # start event loop


if __name__ == '__main__':
    main()
