# Server lokal und im WLAN starten
--------------------------------------------------------------------------------
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```
--------------------------------------------------------------------------------

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

--------------------------------------------------------------------------------

Bei neuer IP addresse:
    Supabase -> Site URL anpassen
             -> Redirect URLs anpassen