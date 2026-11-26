# F11 – Änderungsprotokoll

## Ziel

Jede Änderung in TimberTalk ist nachvollziehbar: wer hat wann welchen Preis, welches Konto,
welchen Termin oder welche Buchung geändert.

## Was der Zimmerer danach kann

In „Einstellungen → Änderungsprotokoll“ sieht der Admin die letzten 300 Änderungen, die neuesten
oben: Zeitpunkt, Person, was gemacht wurde (z. B. „Preis eintragen – Material, Fahrten und Preise
· Nr. 1“) und mit welchen Angaben („unit_price: 520.00 · valid_from: 2026-12-01“). Er kann nach
Bereich filtern. Passwörter stehen dort nie.

## Abnahme

Im Meeting wird genau das vorgeführt:

1. Der Admin legt ein Material an und trägt einen Preis ein. Beides steht im Protokoll mit
   seinem Namen, Uhrzeit und den Angaben.
2. Er setzt das Passwort von Tom zurück und legt ein Konto mit Startpasswort an. Im Protokoll
   steht „Passwort zurücksetzen“ bzw. „Konto anlegen“, das Startpasswort steht dort als „•••“.
3. Abgelehnte Änderungen (z. B. Material ohne Namen), Anmelden und reines Ansehen stehen nicht
   im Protokoll.
4. Die Auswahl „Bereich“ zeigt nur Änderungen eines Bereichs, z. B. „Planung: Kalender je
   Mitarbeiter“.
5. Verwaltung und Gesellen sehen den Abschnitt nicht; die API antwortet ihnen mit 403. Der Admin
   kann das Recht „Änderungsprotokoll sehen“ in „Rollen und Rechte“ weitergeben.
6. `uv run pytest`, `uv run ruff check .` und `uv run ruff format --check .` sind grün.

## Nicht dabei

- **Alter Wert vorher:** Das Protokoll zeigt, was gesendet wurde, nicht den Wert davor.
- **Einträge löschen oder ändern:** gibt es absichtlich nicht.
- **Fehlgeschlagene Anmeldungen:** stehen nicht im Protokoll (dafür gibt es die Sperre in F10).

## Neues Konzept fürs Team

- **Middleware:** `AuditMiddleware` steht vor allen Endpunkten und schreibt nach jeder
  erfolgreichen Änderung (POST, PUT, PATCH, DELETE unter `/api`) einen Eintrag. Features müssen
  dafür nichts tun.
- **`summary` am Endpunkt:** `@router.post("/items", summary="Material anlegen")` ist der Name
  der Änderung im Protokoll (und in der API-Doku unter `/docs`). Neue ändernde Endpunkte bekommen
  immer ein `summary`.

## Reiter

Kein eigener Reiter: Abschnitt `frontend/features/settings/sections/audit.js`
(„Änderungsprotokoll“) im Reiter „Einstellungen“.

## Pate

<offen>
