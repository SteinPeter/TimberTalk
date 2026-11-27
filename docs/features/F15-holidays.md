# F15 – Feiertage je Bundesland

## Ziel

TimberTalk kennt die gesetzlichen Feiertage des Bundeslands, in dem der Betrieb sitzt – ohne dass
jemand das Bundesland eintragen muss.

## Was der Zimmerer danach kann

Er trägt unter „Einstellungen → Firma und Bank“ die Adresse mit Postleitzahl ein; TimberTalk erkennt
daran das Bundesland. Unter „Einstellungen → Feiertage“ steht „Bundesland: Brandenburg – erkannt an
der Postleitzahl 14467“ und die Feiertage des Jahres. Im Kalender stehen Feiertage mit Namen im
Tageskopf und sind farbig hinterlegt; Stunden- und Urlaubskonto (F14) zählen sie nicht als
Arbeitstag.

## Abnahme

Im Meeting wird genau das vorgeführt:

1. Firmenadresse „Am Sägewerk 12, 14467 Potsdam“: Einstellungen → Feiertage zeigt Brandenburg mit
   12 Feiertagen 2026 (u. a. Ostersonntag, Pfingstsonntag, Reformationstag).
2. Adresse auf „80331 München“ ändern: Bayern, u. a. Fronleichnam und Allerheiligen; im Kalender
   steht am 4.6.2026 „Fronleichnam“, das Stundenkonto rechnet die Woche mit vier Arbeitstagen.
3. Liegt der Betrieb an einer Landesgrenze und die Postleitzahl ergibt das falsche Land, legt der
   Chef es unter „Bundesland festlegen“ fest; „Automatisch aus der Firmenadresse“ stellt zurück.
4. Ohne Postleitzahl in der Adresse gelten nur die bundesweiten Feiertage, mit Hinweis.
5. Kalender KW 52/2026: „1. Weihnachtstag“ und „2. Weihnachtstag“ im Kopf, die Spalten hinterlegt.
6. `uv run pytest`, `uv run ruff check .` und `uv run ruff format --check .` sind grün.

## Nicht dabei

- Feiertage, die nur in einzelnen Gemeinden gelten (Mariä Himmelfahrt in Bayern, Fronleichnam in
  Teilen Sachsens und Thüringens, Augsburger Friedensfest) und einmalige Feiertage.
- Baustellen in einem anderen Bundesland: Es zählt immer der Sitz des Betriebs.
- Eigene, betriebliche freie Tage (Heiligabend, Silvester) – die trägt man als Abwesenheit ein.

## Neues Konzept fürs Team

- **Postleitzahl → Bundesland** (`holidays/rules.py`): zuerst die ersten zwei Ziffern
  (Leitregion), dann eine Liste von Ausnahmen für Bereiche an Landesgrenzen.
- **Ostern rechnen** nach Gauß; alle beweglichen Feiertage hängen daran.
- **Ein Feature für mehrere andere:** F8 (Kalender) und F14 (Konten) fragen hier nach
  Feiertagen und Arbeitstagen – so gibt es die Regeln nur einmal.

## Reiter

Kein eigener Reiter. Abschnitt `frontend/features/settings/sections/holidays.js` („Feiertage“ in
den Einstellungen); angezeigt werden die Feiertage auch im Kalender (`planning.js`).

## Pate

<offen>
