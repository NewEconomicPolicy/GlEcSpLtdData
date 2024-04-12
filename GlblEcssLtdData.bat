@rem Generic batch file
@set setup_dir=E:\AbUniv\GlobalEcosseSuite\setup\ltd_data\
@set source_dir=G:\AbUnivGit\GlEcSpLtdData\GlblEcosseVer2\
@set envmdlng_dir=G:\AbUnivGit\EnvMdllngModuls\
@set python_exe=E:\Python38\python.exe
@set PYTHONPATH=%envmdlng_dir%EnvModelModules

@set initial_working_dir=%cd%
@chdir /D %setup_dir%
start cmd.exe /k "%python_exe% -W ignore %source_dir%GlblEcsseHwsdGUI.py"
@chdir /D %initial_working_dir%


rem 
@set source_dir=E:\AbUniv\
@set PYTHONPATH=%source_dir%EnvModelModules;%source_dir%GlblEcosseModulesLtd
@set initial_working_dir=%cd%
@chdir /D %source_dir%GlobalEcosseSuite\setup\ltd_data
start cmd.exe /k "E:\Python38\python.exe -W ignore %source_dir%GlblEcosseVer2\GlblEcsseHwsdGUI.py"
@chdir /D %initial_working_dir%
