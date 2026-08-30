import argparse
import csv
from pathlib import Path

from app.db.supabase import get_supabase

FIELD_ALIASES = {
    "postal_code": ("postal_code", "plz", "postleitzahl"),
    "locality": ("locality", "ortschaftsname", "ortschaft", "ortsbez18"),
    "canton": ("canton", "kanton", "kantonskuerzel", "kantonskürzel"),
}


def _find_field(headers: list[str], aliases: tuple[str, ...]) -> str:
    normalized = {header.strip().lower(): header for header in headers}
    for alias in aliases:
        if alias in normalized:
            return normalized[alias]
    raise ValueError(f"Keine passende Spalte für {aliases[0]} gefunden.")


def read_records(path: Path) -> list[dict[str, str]]:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        text = path.read_text(encoding="cp1252")
    dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
    reader = csv.DictReader(text.splitlines(), dialect=dialect)
    headers = reader.fieldnames or []
    fields = {name: _find_field(headers, aliases) for name, aliases in FIELD_ALIASES.items()}
    unique_rows = {
        (
            row[fields["postal_code"]].strip(),
            row[fields["locality"]].strip(),
            row[fields["canton"]].strip().upper(),
        )
        for row in reader
        if row.get(fields["postal_code"]) and row.get(fields["locality"]) and row.get(fields["canton"])
    }
    return [
        {"postal_code": postal_code, "locality": locality, "canton": canton}
        for postal_code, locality, canton in sorted(unique_rows)
    ]


def import_file(path: Path) -> int:
    records = read_records(path)
    supabase = get_supabase()
    for start in range(0, len(records), 500):
        supabase.table("swiss_postal_codes").upsert(
            records[start:start + 500], on_conflict="postal_code,locality,canton"
        ).execute()
    return len(records)


def main() -> None:
    parser = argparse.ArgumentParser(description="Importiert das amtliche Schweizer PLZ-Verzeichnis.")
    parser.add_argument("csv_file", type=Path)
    args = parser.parse_args()
    print(f"{import_file(args.csv_file)} PLZ-/Ort-Kombinationen importiert.")


if __name__ == "__main__":
    main()
