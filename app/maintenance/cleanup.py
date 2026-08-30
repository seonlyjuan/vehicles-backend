import argparse
import json

from app.maintenance.service import run_retention_cleanup


def main() -> None:
    parser = argparse.ArgumentParser(description="Führt die konfigurierten Aufbewahrungs- und Löschjobs aus.")
    parser.parse_args()
    print(json.dumps(run_retention_cleanup(), indent=2))


if __name__ == "__main__":
    main()
