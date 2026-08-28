# Server lokal und im WLAN starten

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

So ist FastAPI auch über die lokale IP des Computers erreichbar. Falls Windows
beim ersten Start nachfragt, Python den Zugriff auf private Netzwerke erlauben.

Lokale IPv4-Adresse anzeigen:

```powershell
ipconfig | Select-String "IPv4"
```
Bei neuer IP addresse:
    Supabase -> Site URL anpassen
             -> Redirect URLs anpassen