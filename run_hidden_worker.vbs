Set WshShell = CreateObject("WScript.Shell")
' Altere o caminho abaixo para a localização real da sua pasta do projeto
WshShell.Run chr(34) & "C:\Caminho\Para\O\Seu\Projeto\TaskShift\start_worker.bat" & Chr(34), 0
Set WshShell = Nothing