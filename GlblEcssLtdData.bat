rem 
@set root_dir=I:\AbUnivGit\
@set emg_dir=%root_dir%EnvMdllngModuls\
@set source_dir=%root_dir%GlEcSpLtdData\GlblEcosseVer2\
@set glecsuite_dir=E:\AbUniv\GlobalEcosseSuite\
@set py_intrprtr=E:\Python38\python.exe

@set PYTHONPATH=%emg_dir%EnvModelModules;%emg_dir%GlblEcosseModulesLtd
@set init_wrkng_dir=%cd%
@chdir /D %glecsuite_dir%setup\ltd_data
start cmd.exe /k "%py_intrprtr% -W ignore %source_dir%GlblEcsseHwsdGUI.py"
@chdir /D %init_wrkng_dir%
