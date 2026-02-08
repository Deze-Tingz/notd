CreateObject("WScript.Shell").Run "pythonw """ & CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName) & "\notd.py"" listen", 0, False
