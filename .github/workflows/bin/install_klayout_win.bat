
for /f "tokens=* USEBACKQ" %%i in (`python3 setup/_tools.py --tool klayout --field version`) do set KLAYOUTVERSION=%%i

curl https://www.klayout.org/downloads/Windows/klayout-%KLAYOUTVERSION%-win64.zip --output klayout.zip
7z x klayout.zip
xcopy /E klayout-%KLAYOUTVERSION%-win64 "C:\Program Files (x86)\KLayout\"
