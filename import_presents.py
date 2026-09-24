import csv
import os
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_PUBLISHABLE_KEY = os.environ["SUPABASE_PUBLISHABLE_KEY"]

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_PUBLISHABLE_KEY,
)

CSV_FILE = Path("presents.txt")
TABLE_NAME = "cadeaus"


def as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y", "ja"}


if not CSV_FILE.exists():
    raise FileNotFoundError(
        "presents.txt niet gevonden. Controleer de bestandsnaam en start "
        "het script vanuit je projectmap."
    )

rows_to_insert = []

with CSV_FILE.open(newline="", encoding="utf-8-sig") as file:
    reader = csv.DictReader(file)

    for row in reader:
        name = (row.get("Name") or "").strip()
        link = (row.get("Link") or "").strip()
        bought = as_bool(row.get("Bought") or "false")

        if name:
            rows_to_insert.append(
                {
                    "name": name,
                    "link": link or None,
                    "bought": bought,
                }
            )

if not rows_to_insert:
    raise ValueError("Geen geldige cadeaus gevonden in presents.txt.")

result = supabase.table(TABLE_NAME).insert(rows_to_insert).execute()

print(f"{len(result.data)} cadeaus geïmporteerd in de tabel '{TABLE_NAME}'.")