Dim WshShell
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "cmd /c cd /d C:\Users\iwashita.AKGNET\pc-compat-engine && set PORT=10001 && python app.py > tmp_server.log 2>&1", 0, False
