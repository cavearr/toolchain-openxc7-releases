@echo off
rem openxc7 Windows Python selector, shared by the bin\*.cmd launchers.
rem
rem The package does not ship an interpreter. Apio puts oss-cad-suite's
rem lib directory on PATH, and that directory contains python3.exe (not
rem python.exe). A machine with neither resolves "python" to the
rem Microsoft Store alias, which exits 9009 (apio#1194).
rem
rem Order, each candidate executed before it is kept:
rem   1. OPENXC7_PYTHON, when set. A value that does not run stops here.
rem   2. python3 on PATH (the suite interpreter, under apio).
rem   3. python on PATH.
rem   4. py -3 (the python.org launcher).
rem
rem A candidate is kept only when it is Python 3.8 or newer and can
rem import fasm and prjxray. textX 4.0.1, which fasm uses, requires
rem Python >= 3.8. The probe stdout and stderr are discarded, so a Store
rem alias cannot print its install message. The site-packages directory
rem is lib\python3.12 because that was the build interpreter. The
rem packages are pure Python; the name is not the runtime version.
rem
rem OPENXC7_SELECTOR_TRACE, when set to a file path, receives one line
rem naming the interpreter that was chosen. Success stays silent
rem otherwise: a warning on stderr fails the bitstream build.
setlocal EnableExtensions
if not defined OPENXC7_SCRIPT (
  echo openxc7: internal error: OPENXC7_SCRIPT is not set. 1>&2
  exit /b 1
)
if not exist "%OPENXC7_SCRIPT%" (
  echo openxc7: internal error: tool script not found: "%OPENXC7_SCRIPT%" 1>&2
  exit /b 1
)

if defined OPENXC7_PYTHON (
  call :use_explicit
  if errorlevel 1 (
    echo openxc7: OPENXC7_PYTHON is set to "%OPENXC7_PYTHON%" but it cannot run these tools. 1>&2
    echo openxc7: It must be Python 3.8 or newer and be able to import fasm and prjxray. 1>&2
    echo openxc7: Fix OPENXC7_PYTHON, or unset it to search PATH. 1>&2
    exit /b 1
  )
  goto :run
)

call :use_python3
if not errorlevel 1 goto :run
call :use_python
if not errorlevel 1 goto :run
call :use_py
if not errorlevel 1 goto :run

echo openxc7: no usable Python found. 1>&2
echo openxc7: Tried python3, then python, then py -3. Each one was executed, or was not on PATH. 1>&2
echo openxc7: Set OPENXC7_PYTHON to a Python 3.8 or newer executable, 1>&2
echo openxc7: or add the oss-cad-suite lib directory to PATH. 1>&2
echo openxc7: That directory contains python3.exe. Apio adds it for you. 1>&2
exit /b 1

:use_explicit
rem OPENXC7_PYTHON is a path. "where" searches PATH and misses a full path.
if not exist "%OPENXC7_PYTHON%" exit /b 1
call :accept "%OPENXC7_PYTHON%"
if errorlevel 1 exit /b 1
set "OPENXC7_PY=%OPENXC7_PYTHON%"
set "OPENXC7_MODE=exe"
exit /b 0

:use_python3
where python3 >nul 2>&1
if errorlevel 1 exit /b 1
call :accept python3
if errorlevel 1 exit /b 1
set "OPENXC7_PY=python3"
set "OPENXC7_MODE=exe"
exit /b 0

:use_python
where python >nul 2>&1
if errorlevel 1 exit /b 1
call :accept python
if errorlevel 1 exit /b 1
set "OPENXC7_PY=python"
set "OPENXC7_MODE=exe"
exit /b 0

:use_py
where py >nul 2>&1
if errorlevel 1 exit /b 1
call :accept py -3
if errorlevel 1 exit /b 1
set "OPENXC7_MODE=py"
exit /b 0

:accept
%* -c "import sys; import fasm, prjxray; sys.exit(1) if sys.version_info<(3, 8) else None" >nul 2>&1
exit /b %ERRORLEVEL%

:run
if defined OPENXC7_SELECTOR_TRACE (
  if "%OPENXC7_MODE%"=="py" (
    >>"%OPENXC7_SELECTOR_TRACE%" echo py -3
  ) else (
    >>"%OPENXC7_SELECTOR_TRACE%" echo %OPENXC7_PY%
  )
)
if "%OPENXC7_MODE%"=="py" (
  py -3 "%OPENXC7_SCRIPT%" %*
) else (
  "%OPENXC7_PY%" "%OPENXC7_SCRIPT%" %*
)
exit /b %ERRORLEVEL%
