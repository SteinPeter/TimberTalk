# Feature „Änderungsprotokoll“ (F11).
# Reiter im Frontend: Abschnitt „Änderungsprotokoll“ in den Einstellungen
# (frontend/features/settings/sections/audit.js).
#
# Schreibt jede erfolgreiche Änderung über die API mit: wann, wer, in welchem Bereich, was, mit
# welchen Angaben. Das macht die Middleware in middleware.py – die anderen Features müssen dafür
# nichts tun. Sie geben ihren Endpunkten nur einen lesbaren Namen: @router.post(..., summary="…").
# Handbuch-Kapitel: docs/handbuch/F11-audit.md, Steckbrief: docs/features/F11-audit.md.
