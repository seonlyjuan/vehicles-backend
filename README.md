# Server lokal und im WLAN starten
--------------------------------------------------------------------------------
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

--------------------------------------------------------------------------------
SERVER:
```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

--------------------------------------------------------------------------------
CLIENT:
```powershell
npm.cmd run dev
```

--------------------------------------------------------------------------------

Bei neuer IP addresse:
    Supabase -> Site URL anpassen
             -> Redirect URLs anpassen

--------------------------------------------------------------------------------

## Request-Sicherheit

Gemeinsam verwendete Request-Gates liegen unter `app/core/security/`:

- `authentication.py`: prüft den Supabase-Bearer-Token.
- `rate_limiting.py`: stellt die gemeinsame Rate-Limit-Mechanik und FastAPI-Dependency bereit.
- `request_limits.py`: begrenzt die Grösse von Bild-Uploads vor der Verarbeitung.
- `headers.py`: setzt gemeinsame HTTP-Sicherheitsheader.

Fachspezifische Policies bleiben bei der jeweiligen Domain:

- `vehicles/access.py` und `messages/access.py`: Besitz- und Teilnehmerprüfungen.
- `*/schemas.py`: Eingabevalidierung.
- `*/rate_limits.py`: Grenzwerte pro Endpunktgruppe.
- `*/service.py`: Businessregeln und Anwendungslogik.

## HTTPS in Produktion

Der lokale Uvicorn-Befehl verwendet bewusst HTTP. In Produktion muss die API
hinter einem HTTPS-fähigen Hostingdienst oder Reverse Proxy betrieben werden.
TLS-Zertifikate und HTTP-zu-HTTPS-Weiterleitungen werden dort konfiguriert. Der
Client muss dann über `VITE_API_URL=https://...` ebenfalls die HTTPS-Adresse
verwenden. Den Supabase-Service-Role-Key niemals an den Client ausliefern.

## Neues Supabase-Projekt und Migrationen

Die Datenbank wird nicht mehr durch einzeln kopierte Abfragen im SQL Editor
verwaltet. Alle versionierten Migrationen liegen unter `supabase/migrations/`
und werden von der lokal installierten Supabase CLI in der richtigen Reihenfolge
ausgeführt. Die alte, teilweise manuell migrierte Datenbank nicht mit diesem
Projekt verknüpfen.

Einmalige Einrichtung für ein neues Supabase-Projekt:

1. Im Supabase Dashboard ein leeres Projekt erstellen.
2. Im Server-Ordner die festgeschriebene CLI-Version installieren:

```powershell
npm.cmd install
```

3. Anmelden und das neue Projekt über dessen Project Ref verknüpfen:

```powershell
npm.cmd run db:login
npm.cmd run db:link -- --project-ref DEINE_PROJECT_REF
```

4. Zuerst nur anzeigen, welche Migrationen ausgeführt würden:

```powershell
npm.cmd run db:check
```

5. Wenn die Liste stimmt, alle Migrationen einmalig anwenden:

```powershell
npm.cmd run db:push
npm.cmd run db:migrations
```

Der Push erstellt das Profilschema, Inserate, Nachrichten, Moderation,
Benachrichtigungen, RLS-Regeln und den privaten Bucket `vehicles-images`.
Bereits erfolgreich angewendete Migrationen werden bei späteren Pushes
automatisch übersprungen.

Danach die Zugangsdaten des neuen Projekts in `server/.env` und `client/.env`
eintragen. Lokale Konfigurationsdateien und geheime Schlüssel bleiben durch die
Gitignore vom Repository ausgeschlossen. Benutzer und Daten des alten Projekts
werden nicht automatisch übertragen.

Eine neue Datenbankänderung wird immer als weitere Migration erstellt:

```powershell
npm.cmd run db:new -- kurze_beschreibung
npm.cmd run db:check
npm.cmd run db:push
```

`supabase db reset --linked` niemals gegen das Online-Projekt ausführen, weil
dies das entfernte Schema und vorhandene Daten zurücksetzen kann.

## Schweizer PLZ-Verzeichnis importieren

Die Tabelle `swiss_postal_codes` wird bewusst nicht mit einer veraltenden Kopie
ausgeliefert. Das aktuelle amtliche Ortschaftenverzeichnis als CSV von
swisstopo/opendata.swiss herunterladen und danach im Server-Ordner importieren:

`https://opendata.swiss/de/dataset/amtliches-ortschaftenverzeichnis-mit-postleitzahl-und-perimeter`

```powershell
..\.venv\Scripts\python.exe -m scripts.import_swiss_postal_codes C:\Pfad\AMTOVZ_CSV.csv
```

Der Import erkennt deutsche Spaltennamen wie `PLZ`, `Ortschaftsname` und
`Kantonskürzel` und kann bei einem aktualisierten Datensatz erneut laufen.

## Regelmässige Aufbewahrungs- und Löschjobs

Folgenden Befehl in Produktion täglich über den Scheduler des Hostinganbieters
ausführen:

```powershell
..\.venv\Scripts\python.exe -m app.maintenance.cleanup
```

Der Job deaktiviert abgelaufene Inserate und entfernt Daten nach den zentral in
`app/maintenance/service.py` definierten Fristen. Die Fristen müssen vor dem
Launch mit der Datenschutzerklärung abgestimmt werden.

## Produktionskonfiguration

- `APP_ENV=production` deaktiviert den Zahlungsplatzhalter zwingend.
- `APP_ENV=production` aktiviert standardmässig HTTPS-Weiterleitung und schaltet
  die lokale WLAN-CORS-Regel ab.
- `ALLOWED_HOSTS` muss auf die produktive API-Domain gesetzt werden.
- `REDIS_URL` aktiviert einen gemeinsamen Rate Limiter für mehrere API-Instanzen.
- Ein Admin wird ausschliesslich direkt in der Datenbank über
  `profiles.platform_role = 'admin'` freigeschaltet, niemals über den Client.
- Payrexx ist noch nicht angebunden. In Produktion bleibt die Veröffentlichung
  deshalb gesperrt, bis ein signaturgeprüfter Payrexx-Webhook implementiert ist.
