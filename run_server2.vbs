Set oShell = CreateObject("WScript.Shell")
oShell.CurrentDirectory = "C:\Users\iwashita.AKGNET\pc-compat-engine"
oShell.Run "cmd /c python app.py > tmp_server.log 2>&1", 0, False
