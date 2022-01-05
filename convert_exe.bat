.\env_37\Scripts\pyinstaller.exe --clean --noconfirm --add-data ./config/;config/  --add-data ./hdb_py/;hdb_py/ -w -D  ./run_viewer_mem.py

::.\build_env\Scripts\pyinstaller.exe --clean --noconfirm -D -w -i ./ico/1.ico ./run_viewer.py
::pyinstaller.exe -D -w -i ./ico/1.ico ./run_viewer.py

:: cmd 执行
:: .\venv_72\Scripts\pyinstaller.exe --clean --noconfirm --add-data ./config/;config/ --add-data ./ico/;ico/ --add-data ./hft_py/;hft_py/ -w -D -i ./ico/app.ico ./BTViewer.py
PAUSE