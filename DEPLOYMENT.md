# Backend bereitstellen

Der Server ist ein eigenes Git-Repository. Alle folgenden Befehle werden im
Ordner `server` ausgeführt. Die technische Bereitstellung gibt Zahlungsabläufe
oder AGB nicht für den Produktivbetrieb frei.

## Laufzeit und Installation

Python **3.13.7** steht in `.python-version`. `requirements.txt` enthält die
getesteten direkten und indirekten Paketversionen. Änderungen daran bewusst
vornehmen und anschliessend Tests und Linux-Container-Build ausführen.
Die Node-Version für die Supabase CLI steht in `.node-version`.

```sh
python -m venv .venv
# Linux: .venv/bin/python; Windows: .venv/Scripts/python.exe
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip check
.venv/bin/python -m unittest discover -s tests -v
```

## Produktionskonfiguration

`.env.production.example` als Vorlage verwenden. Die echten Werte als
Umgebungsvariablen im Hostingdienst oder in einer privaten `.env.production`
hinterlegen. Lokale `.env`-Dateien werden nicht in das Docker-Image kopiert.
Produktionsdateien mit Zugangsdaten sind durch `.gitignore` ausgeschlossen.

| Variable | Bedeutung |
| --- | --- |
| `APP_ENV` | Für die produktive API zwingend `production`. Im Docker-Image voreingestellt. |
| `CLIENT_ORIGIN` | HTTPS-Origin des Frontends, ohne Pfad oder abschliessenden Schrägstrich. |
| `ALLOWED_HOSTS` | Kommagetrennte API-Hostnamen ohne Schema, Port oder Wildcards. |
| `SUPABASE_URL` | HTTPS-Adresse des Zielprojekts. |
| `SUPABASE_SERVICE_ROLE_KEY` | Ausschliesslich serverseitiger Schlüssel aus dem Zielprojekt. |
| `ENFORCE_HTTPS` | In Produktion `true`. |
| `PORT` | Interner HTTP-Port; Standard `8000`. |
| `WEB_CONCURRENCY` | API-Prozesse; Standard `1`. |
| `FORWARDED_ALLOW_IPS` | Vertrauenswürdige IPs/Netze des vorgeschalteten HTTPS-Proxys. |
| `REDIS_URL` | Gemeinsamer Rate Limiter; notwendig bei mehreren Prozessen oder Replikaten. |

Der Start prüft Produktionswerte und bricht bei fehlenden Pflichtwerten oder
lokalen HTTP-Adressen ab. Fehlertexte enthalten keine Schlüssel.
`CLIENT_ORIGIN_REGEX` bleibt in Produktion ungesetzt. Mehrere Prozesse werden
ohne Redis abgelehnt; bei mehreren Replikaten muss Redis ebenfalls im Hoster
konfiguriert werden, da ein Prozess andere Replikate nicht selbst erkennen kann.

## Start und HTTPS

Mit bereits gesetzten Umgebungsvariablen:

```sh
python -m app.start
```

Mit einer privaten Produktionsdatei und aktiviertem Python-Environment:

```sh
python -m dotenv -f .env.production run -- python -m app.start
```

Der Start verwendet kein `--reload`, berücksichtigt den Hosting-Port und
beendet laufende Requests geordnet. Der Hostingdienst muss den Prozess bei
Abstürzen neu starten.

Alternativ als Container:

```sh
docker build -t vehicle-api .
docker run --env-file .env.production -p 127.0.0.1:8000:8000 --restart unless-stopped vehicle-api
```

Der Container läuft als Benutzer ohne Root-Rechte. Im Hostingdienst den
internen Port `8000` an den HTTPS-Eingang anbinden. Bei einem anderen `PORT`
auch das Port-Mapping ändern.

HTTPS verschlüsselt die Verbindung vom Browser zum Hostingdienst. Das
Zertifikat und die öffentliche HTTP-zu-HTTPS-Weiterleitung richtet der Hoster
ein. Dieser leitet Requests intern per HTTP an Uvicorn weiter und muss
`X-Forwarded-Proto: https` sowie den ursprünglichen `Host` setzen.
`FORWARDED_ALLOW_IPS` muss zu diesem Proxy passen, sonst können endlose
HTTPS-Weiterleitungen entstehen. `*` nur verwenden, wenn der API-Port
ausschliesslich über den vertrauenswürdigen Proxy erreichbar ist.
Siehe [Uvicorn-Proxykonfiguration](https://www.uvicorn.org/deployment/).

## Zustandsprüfungen und Datenbank

- `GET /health`: Prozess läuft; keine Datenbankabfrage.
- `GET /ready`: Datenbank erreichbar und optional Redis erreichbar; sonst HTTP 503.
  Die Datenbankabfrage hat ein Timeout von fünf Sekunden, Redis von zwei Sekunden.
  Die Antwort enthält keine Nutzerdaten oder internen Fehlermeldungen.

Healthchecks müssen ebenfalls den erlaubten Host und HTTPS verwenden oder über
den vertrauenswürdigen Proxy kommen. `/ready` als Bereitschaftsprüfung im Hoster
eintragen; `/health` eignet sich für die Prozessüberwachung. `/ready` bestätigt
keinen vollständigen Nutzerablauf und prüft nicht jede Migration.

Migrationen mit der festgeschriebenen Supabase CLI installieren und zunächst
als Vorschau prüfen; die Einrichtung des Zielprojekts steht in `README.md`:

```sh
npm ci
npm run db:check
npm run db:migrations
```

Nach Anwendung der Migrationen und dem PLZ-Import die Grundstruktur lesend prüfen:

```sh
python -m scripts.check_deployment
```

Mit privater Produktionsdatei:

```sh
python -m dotenv -f .env.production run -- python -m scripts.check_deployment
```

Die Prüfung kontrolliert Kerntabellen, vorhandene PLZ-Daten und den privaten
Bucket `vehicles-images`. Exitcode 1 bedeutet, dass ein Check fehlgeschlagen
ist. Sie verändert keine Daten und ersetzt keine vollständigen RLS-, Login-
oder Uploadtests. Echte Google-Login-Weiterleitungen im Supabase-Dashboard
müssen später zur produktiven Frontend-Adresse passen.

## Täglicher Wartungsjob

Im Scheduler des Hostingdienstes das gleiche Backend-Image und dieselben
Server-Umgebungsvariablen verwenden. Befehl einmal täglich, z. B. um 03:00 UTC:

```sh
python -m app.maintenance.cleanup
```

Der vorhandene Job führt echte Aufbewahrungs- und Löschaktionen aus. Er wurde
durch diese Deployment-Vorbereitung nicht ausgeführt. Pro Umgebung nur einen
Scheduler konfigurieren; fehlgeschlagene Läufe und deren Ausgabe überwachen.

Für einen eigenen Linux-Server liegen unter `deploy/` eine systemd-Service-
und Timer-Vorlage. Sie erwarten den Benutzer `vehicle-api`, den Code samt
Python-Environment unter `/opt/vehicle-api` und die Servervariablen in
`/etc/vehicle-api.env`. Pfade und Benutzer vor Installation anpassen, die
Variablendatei nur für berechtigte Benutzer lesbar machen. Die Dateien nach
`/etc/systemd/system/` kopieren und aktivieren:

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now vehicle-cleanup.timer
systemctl list-timers vehicle-cleanup.timer
journalctl -u vehicle-cleanup.service
```

Der Timer holt verpasste Läufe nach und startet denselben Service nicht parallel.

## Automatische Prüfungen

`.github/workflows/ci.yml` prüft bei Push und Pull Request Installation,
Paketkonsistenz, Python-Tests und den Linux-Container samt Produktionsstart.
Ein separater Job startet eine wegwerfbare lokale Supabase-Datenbank, wendet
Migrationen an und prüft SQL-Funktionen mit dem Datenbank-Linter.
Es werden keine Online-Migrationen oder Deployments ausgeführt.

Vor einem öffentlichen Start sind im Zielsystem ein kompletter Login-,
Inserat-, Upload- und Nachrichtenablauf sowie Backup und Wiederherstellung
zu prüfen. Zahlungsintegration und Rechtstextfreigabe bleiben offene,
separate Voraussetzungen.
