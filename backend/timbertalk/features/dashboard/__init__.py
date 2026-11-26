# Feature „Dashboard“ (F12): die Startseite mit Widgets.
# Reiter im Frontend: frontend/features/start/start.js (über das Logo oben links).
#
# Ein Widget ist eine Datei frontend/features/<ordner>/widgets/<name>.js – im Ordner des Features,
# dem es gehört (Kalender, Stunden, …). service.py findet diese Dateien selbst, genau wie
# load_features() die Feature-Ordner findet. Ein neues Widget legt also nur eine neue Datei an;
# weder das Dashboard noch eine Liste wird dafür geändert.
# Handbuch-Kapitel: docs/handbuch/F12-dashboard.md, Steckbrief: docs/features/F12-dashboard.md.
