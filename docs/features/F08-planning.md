# F8 – Kalender je Mitarbeiter (Dispatching)

## Ziel

Für jede Person im Betrieb gibt es einen Kalender. Wer plant, teilt Leute auf einer Plantafel
Baustellen und Terminen zu und sieht sofort, wer schon verplant oder abwesend ist.
Erster Teil des Features `planning/` aus dem Programmaufbau („Kalender je Mitarbeiter“).

## Was der Zimmerer danach kann

Im Reiter „Kalender“ sieht der Chef die Woche als Plantafel: eine Zeile je Person, eine Spalte je
Tag. Mit einem Klick auf „+“ in einer Zelle oder auf „Termin eintragen“ legt er einen Termin an –
z. B. „Carport Berger“ von Montag bis Mittwoch für Max und Tom, mit Ort und Uhrzeit. Ist jemand
schon verplant oder im Urlaub, sagt TimberTalk es nach dem Speichern. Ein Geselle sieht auf dem
Handy seine eigene Woche als Liste nach Tagen – wo er wann ist und mit wem.

Dazu: Fahrzeuge und Maschinen (Transporter, Kran) stehen als eigene Zeilen auf der Plantafel und
werden wie Personen eingeplant. Termine lassen sich mit der Maus auf einen anderen Tag oder zu
einer anderen Person ziehen, mit „Rückgängig“. Wer ein-, aus- oder umgeplant wird, bekommt oben
rechts eine Mitteilung. Gesellen beantragen Urlaub, der Chef genehmigt ihn mit einem Klick, und er
steht im Kalender. Jede Person kann ihren Kalender über einen geheimen Link in der Kalender-App
des Handys abonnieren.

## Abnahme

Im Meeting wird genau das vorgeführt:

1. **Plantafel:** Der Chef sieht KW 49 mit allen aktiven Konten als Zeilen, blättert mit
   „Vorwoche“, „Heute“, „Nächste“, und der heutige Tag ist hervorgehoben.
2. **Einplanen:** Er trägt „Carport Berger, Potsdam“ von Mo bis Mi für Max und Tom ein. Der
   Termin steht in beiden Zeilen an allen drei Tagen.
3. **Überschneidung:** Er trägt für Tom am Dienstag Urlaub ein. Nach dem Speichern steht dort
   „Achtung: Tom Adler ist am 01.12.2026 schon eingeplant: Carport Berger.“ – gespeichert ist es
   trotzdem. Vormittags- und Nachmittagstermine am selben Tag gelten nicht als Überschneidung.
4. **Ändern und löschen:** Ein Klick auf den Termin öffnet ihn; Zeitraum, Personen und Uhrzeit
   lassen sich ändern, der Termin lässt sich nach Rückfrage löschen.
5. **Persönlicher Kalender:** Max meldet sich auf dem Handy an und sieht „Meine Woche“ mit seinen
   Terminen, Ort und Kollegen – ohne „+“ und ohne „Termin eintragen“.
6. **Rechte:** Nimmt der Chef (Admin-Konto) in „Rollen und Rechte“ den Gesellen das Häkchen „Kalender aller
   Mitarbeitenden sehen“, sieht Max nur noch seinen eigenen Kalender, auch über die API.
   Eintragen ohne „Termine für alle planen“ antwortet mit 403.
7. **Mitteilungen:** Max sieht oben rechts „Mitteilungen 1“: „Neu eingeplant: Carport Berger,
   Mo 30.11.–Mi 02.12., Potsdam.“ Ändert der Chef den Zeitraum, kommt „Geändert: …“, nimmt er
   Max heraus „Ausgeplant: …“, löscht er den Termin „Abgesagt: …“. Wer plant, bekommt selbst nichts.
8. **Fahrzeuge und Maschinen:** In „Einstellungen → Fahrzeuge und Maschinen“ legt der Chef
   „Transporter“ und „Autokran“ an. Sie erscheinen als Zeilen auf der Plantafel und im Dialog.
   Ist der Kran schon verplant, kommt der Hinweis „Autokran ist am … schon verplant: …“.
   Ausgemusterte erscheinen nicht mehr, alte Termine behalten sie.
9. **Ziehen:** Der Chef zieht „Carport Berger“ bei Max von Montag auf Dienstag: Der Termin läuft
   jetzt Di–Do, mit Hinweis auf Überschneidungen. „Rückgängig“ holt ihn zurück. Auf eine andere
   Person gezogen, tritt diese an die Stelle von Max.
10. **Urlaubsantrag:** Max beantragt im Kalender Urlaub. Der Chef bekommt eine Mitteilung, sieht
    beim Antrag „Achtung: Max Berger ist am … schon eingeplant …“ und genehmigt. Der Urlaub steht
    im Kalender, Max bekommt „Urlaub genehmigt: …“. Abgelehnt mit Grund steht der Grund dabei.
11. **Kalender-Abo:** Max erzeugt unter „Kalender aufs Handy holen“ einen Abo-Link. Die Adresse
    liefert ohne Anmeldung seinen Kalender als iCalendar; ein neuer Link macht den alten ungültig.
12. `uv run pytest`, `uv run ruff check .` und `uv run ruff format --check .` sind grün.

## Rechte (Voreinstellung, in „Rollen und Rechte“ änderbar)

| Recht | Admin (Chef) | Meister | Verwaltung | Geselle | Azubi |
| --- | :-: | :-: | :-: | :-: | :-: |
| Kalender aller Mitarbeitenden sehen (`calendar.view_all`) | ✓ | ✓ | ✓ | ✓ | ✓ |
| Termine für alle planen und ändern, Fahrzeuge pflegen (`calendar.dispatch`) | ✓ | ✓ | ✓ | – | – |
| Urlaub beantragen (`calendar.request_absence`) | ✓ | ✓ | ✓ | ✓ | ✓ |
| Urlaubsanträge genehmigen oder ablehnen (`calendar.approve_absence`) | ✓ | – | – | – | – |

Ohne `calendar.view_all` sieht man nur den eigenen Kalender.

## Nicht dabei

- **Verknüpfung mit Projekten:** Der Termin hat einen freien Titel. Die Projektnummer kommt dazu,
  sobald F3 (Projekte) in `main` ist.
- **Arbeitspakete und Gantt-Ansicht:** späterer Teil von `planning/`.
- **Wiederkehrende Termine, Resturlaub zählen, Ziehen auf dem Handy:** später.
- **Mitteilungen per E-Mail oder Push aufs Handy:** Mitteilungen gibt es nur in TimberTalk selbst.
- **Kalender-Abo von unterwegs:** Das Handy muss den Rechner im Betrieb erreichen (WLAN oder VPN).

## Neues Konzept fürs Team

- **Termin über mehrere Tage und Personen:** Ein Termin (`planning_entry`) hat ersten und letzten
  Tag; wer dabei ist, steht in einer eigenen Tabelle (`planning_assignment`), eine Zeile je Person.
- **Hinweis statt Verbot:** Überschneidungen werden gemeldet, aber nicht verhindert – die
  Entscheidung bleibt beim Planenden.
- **`<dialog>`:** Der Browser bringt das Fenster „Termin eintragen“ selbst mit (`showModal()`);
  Escape und „Abbrechen“ schließen es.
- **Mitteilungen als eigenes kleines Feature** (`notifications/`): Jedes Feature kann mit
  `notifications.service.notify(session, [konten], "Text")` Personen etwas mitteilen.
- **Ziehen und Ablegen** (HTML Drag and Drop): `draggable`, `dragstart`, `dragover`, `drop`.
- **iCalendar** (RFC 5545): Kalender als Text, den jede Kalender-App abonnieren kann; der Link
  enthält einen geheimen Schlüssel, weil Kalender-Apps sich nicht anmelden können.

## Reiter

`frontend/features/planning/planning.js` („Kalender“) – war bisher leer – mit
`requests.js` (Urlaubsanträge) und `ical.js` (Kalender-Abo) im selben Ordner. Dazu der Abschnitt
`frontend/features/settings/sections/planning-resources.js` („Fahrzeuge und Maschinen“) und der
Knopf „Mitteilungen“ in der Leiste (`frontend/shared/notifications.js`).

## Pate

<offen>
