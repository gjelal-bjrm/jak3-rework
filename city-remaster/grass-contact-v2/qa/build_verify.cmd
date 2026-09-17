@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cl /nologo /O2 /EHsc /std:c++17 verify_anchors.cpp /Fe:verify_anchors.exe /Fo:verify_anchors.obj
if errorlevel 1 exit /b 1
verify_anchors.exe native-grass.bin native-roots.bin anchors-validation.json
