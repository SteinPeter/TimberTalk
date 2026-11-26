# F10 – Benutzerkonten und Rechte

## Ziel

Jeder Mensch im Betrieb hat ein eigenes Konto mit einer Rolle (Admin, Meister, Verwaltung,
Geselle, Azubi). Der Chef bekommt ein Admin-Konto – eine eigene Chef-Rolle gibt es nicht. Die Rolle
bestimmt, was jemand sehen und ändern darf – zuerst bei Preisen und Kosten.
Grundlage: `TimberTalk_Programmaufbau.pdf`, Kapitel 10 „Konten und Rechte“.

## Was der Zimmerer danach kann

Wer TimberTalk öffnet, meldet sich mit Anmeldenamen oder Personalnummer und Passwort an und bleibt
auf dem Gerät 30 Tage angemeldet. Oben rechts steht sein Foto (oder seine Initialen) mit dem
Nachnamen darunter; ein Klick öffnet „Mein Konto“ und „Abmelden“. Oben links führt das Logo
TimberTalk zur Startseite. Der Admin legt in den Einstellungen Konten an – mit Foto, wenn er
möchte. Jedes neue Konto bekommt das Standardpasswort (voreingestellt „timbertalk-start“, der
Admin kann es ändern). Bei der ersten Anmeldung muss man es durch ein eigenes ersetzen. Hat jemand
sein Passwort vergessen, setzt der Admin es wieder auf das Standardpasswort. In „Rollen und Rechte“ legt der Admin mit Häkchen fest, welche Rolle was darf –
soll z. B. die Verwaltung auch Konten pflegen, bekommt sie das Häkchen „Konten verwalten“. Ein Geselle bucht zum Beispiel Material und Fahrten, sieht aber keine Preise, keine Beträge
und keine Projektkosten.

## Abnahme

Im Meeting wird genau das vorgeführt:

1. **Erster Start:** Auf einer leeren Datenbank meldet man sich mit `admin` / `admin` an und
   muss sofort ein eigenes Passwort (mindestens 8 Zeichen) festlegen. Vorher antwortet die API
   außer „Mein Konto“ und „Abmelden“ nur mit 403.
2. **Ohne Anmeldung nichts:** Jeder Endpunkt außer `/api/health` und der Anmeldung antwortet ohne
   Anmeldung mit 401. Die Seite zeigt dann nur die Anmeldung.
3. **Konto anlegen:** Der Admin klickt „+ Neues Konto“ und legt „Max Berger“ als Geselle mit
   Personalnummer 017 und Foto an. Max meldet sich mit „017“ und dem Standardpasswort an und setzt
   sein eigenes Passwort; das Standardpasswort selbst nimmt TimberTalk dafür nicht an. Oben rechts
   sieht Max sein Foto und darunter „Berger“.
4. **Rechte beim Material:** Max sieht im Reiter „Buchungen“ das Material ohne Preis, bucht
   2,5 m³ und sieht die Buchung ohne Preis, Betrag und Gesamtkosten. In den Einstellungen sieht er
   nur „Mein Konto“. Der Admin sieht dieselbe Buchung mit Betrag.
5. **Passwort vergessen:** Der Admin setzt das Passwort von Max zurück. Max ist auf allen Geräten
   abgemeldet und meldet sich wieder mit dem Standardpasswort an.
6. **Rechte ändern:** In „Rollen und Rechte“ bekommt der Geselle ein Häkchen bei „Preise … sehen“.
   Nach dem Neuladen sieht Max die Preise. Häkchen beim Admin lassen sich nicht abwählen.
7. **Fehlversuche:** Nach fünf falschen Passwörtern hintereinander ist das Konto 15 Minuten
   gesperrt, auch für das richtige Passwort. In „Benutzerkonten“ steht dann „Fehlversuche –
   gesperrt bis …“; „Passwort zurücksetzen“ hebt die Sperre sofort auf.
8. **Azubi:** Ein Konto mit der Rolle Azubi bucht Material und sieht keine Preise.
9. **Standardpasswort und Foto:** Der Admin ändert in „Benutzerkonten“ das Standardpasswort; neue
   Konten bekommen ab dann das neue. In „Mein Konto“ wählt Max ein eigenes Foto; es erscheint
   sofort oben rechts. Im Änderungsprotokoll steht das Standardpasswort nicht.
10. **Sperren:** Ein gesperrtes Konto wird sofort abgemeldet und kann sich nicht mehr anmelden.
   Das eigene Konto und das letzte Admin-Konto lassen sich nicht sperren.
11. `uv run pytest`, `uv run ruff check .` und `uv run ruff format --check .` sind grün.

## Rollen und Rechte (Voreinstellung)

| Recht | Admin | Meister | Verwaltung | Geselle | Azubi |
| --- | :-: | :-: | :-: | :-: | :-: |
| Konten verwalten, Passwörter zurücksetzen, Rechte ändern | ✓ | – | – | – | – |
| Preise, Stundensätze und Projektkosten sehen | ✓ | ✓ | ✓ | – | – |
| Preise, Stundensätze und Firmendaten ändern | ✓ | – | ✓ | – | – |
| Materialstamm pflegen | ✓ | ✓ | ✓ | – | – |
| Material und Fahrten buchen | ✓ | ✓ | ✓ | ✓ | ✓ |
| Kalender aller Mitarbeitenden sehen (F8) | ✓ | ✓ | ✓ | ✓ | ✓ |
| Termine für alle planen und ändern (F8) | ✓ | ✓ | ✓ | – | – |

Wer „Konten verwalten“ hat, kann jedes Häkchen außer denen des Admins ändern. Admin-Konten legt,
ändert und setzt nur ein Admin zurück.

Die Rolle ist eine Einordnung für den Admin: Sie steht nur im Abschnitt „Benutzerkonten“
(Recht `accounts.manage`). In der Leiste, in „Mein Konto“ und in anderen Features erscheint nur
der Name.

## Nicht dabei

- **Kalender je Mitarbeiter:** eigenes Feature in `planning/` (F8). Es benutzt die Konten und
  Rechte von hier.
- **Verknüpfung mit `employees/`:** Stundensatz und Stammdaten eines Mitarbeiters kommen mit dem
  Feature Mitarbeitende. Dort verweist der Eintrag auf sein Konto.
- **Konten löschen:** Konten werden gesperrt, nicht gelöscht, damit Buchungen ihre Person behalten.
- **Zwei-Faktor-Anmeldung:** später, wenn TimberTalk von außerhalb des Betriebs erreichbar ist.
- **Rechte für Kunden, Projekte, Stunden, Rechnungen:** Jedes dieser Features trägt seine Rechte
  in `permissions.py` ein, sobald es gebaut wird.

## Neues Konzept fürs Team

- **Anmeldung für alle Endpunkte:** `main.py` hängt `require_login` aus `accounts/deps.py` an jeden
  Feature-Router. Ein Feature muss dafür nichts tun.
- **Rechte im Endpunkt:** `Depends(require("finance.edit"))` lässt nur Konten mit diesem Recht
  durch (403). `Depends(can("finance.view"))` sagt nur Ja oder Nein, z. B. um Preise auszublenden.
- **Rechte in der Oberfläche:** `can("…")` aus `frontend/shared/session.js`. Ein Reiter oder
  Abschnitt mit `export const permission = "…"` erscheint nur mit diesem Recht.
- **Tests mit Rollen:** Die Fixture `client` ist jetzt als Admin angemeldet. `client_as("journeyman")`
  gibt einen Browser mit einem Gesellen-Konto, `anonymous_client` einen ohne Anmeldung.
- **Passwort-Hash und Sitzungsschlüssel:** siehe Handbuch-Kapitel `docs/handbuch/F10-accounts.md`.

## Reiter

Kein eigener Reiter. Drei Abschnitte im Reiter „Einstellungen“:
`frontend/features/settings/sections/accounts-own.js` („Mein Konto“),
`accounts-manage.js` („Benutzerkonten“) und `accounts-roles.js` („Rollen und Rechte“).
Dazu die Anmeldeseite `frontend/shared/login.js`.

## Pate

<offen>
