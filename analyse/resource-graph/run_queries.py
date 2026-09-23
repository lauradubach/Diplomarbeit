"""
DIP-7 – Azure Resource Graph API: Analyse-Skript

Führt alle *.kql-Dateien im Ordner queries/ gegen die Resource Graph REST API aus
und speichert die Resultate als JSON unter output/ (NICHT committen – PROD-Daten!).

Authentifizierung: DefaultAzureCredential (nutzt z.B. eine bestehende `az login`-Session).
Keine hartcodierten Credentials (vgl. Definition of Done, Kap. 2.6).

Aufruf:
    pip install azure-identity requests
    az login --tenant <TENANT_ID>
    python run_queries.py --subscriptions <SUB_ID> [<SUB_ID> ...]
    python run_queries.py --subscriptions <SUB_ID> --only 02_vm_inventory
    python run_queries.py                                  # alle zugänglichen Subscriptions
    python run_queries.py --region westeurope              # andere Region
    python run_queries.py --region all                     # ohne Regionsfilter
"""

import argparse
import json
import time
from pathlib import Path

import requests
from azure.identity import DefaultAzureCredential

API_URL = "https://management.azure.com/providers/Microsoft.ResourceGraph/resources"
API_VERSION = "2024-04-01"
PAGE_SIZE = 1000  # Maximum pro Antwort laut API ($top 1..1000)

BASE_DIR = Path(__file__).parent
QUERY_DIR = BASE_DIR / "queries"
OUTPUT_DIR = BASE_DIR / "output"


def get_token() -> str:
    credential = DefaultAzureCredential()
    return credential.get_token("https://management.azure.com/.default").token


def respect_throttling(response: requests.Response) -> None:
    """Resource Graph: Standard-Quote ~15 Abfragen / 5 Sek. pro Benutzer."""
    remaining = response.headers.get("x-ms-user-quota-remaining")
    resets_after = response.headers.get("x-ms-user-quota-resets-after")  # Format hh:mm:ss
    if remaining is not None and int(remaining) <= 1 and resets_after:
        h, m, s = (int(x) for x in resets_after.split(":"))
        wait = h * 3600 + m * 60 + s + 1
        print(f"  Quote fast erschöpft – warte {wait}s")
        time.sleep(wait)


def run_query(token: str, query: str, subscriptions: list[str] | None) -> dict:
    """Führt eine KQL-Abfrage aus und sammelt alle Seiten ($skipToken)."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = {
        "query": query,
        "options": {"$top": PAGE_SIZE, "resultFormat": "objectArray"},
    }
    if subscriptions:  # ohne Angabe: alle Subscriptions, auf die der Benutzer Zugriff hat
        body["subscriptions"] = subscriptions
    rows, pages, total = [], 0, None

    while True:
        started = time.perf_counter()
        resp = requests.post(API_URL, params={"api-version": API_VERSION}, headers=headers, json=body, timeout=60)
        duration_ms = round((time.perf_counter() - started) * 1000)

        if resp.status_code == 429:
            retry = int(resp.headers.get("Retry-After", "5"))
            print(f"  HTTP 429 (Throttling) – Retry nach {retry}s")
            time.sleep(retry)
            continue
        resp.raise_for_status()

        payload = resp.json()
        pages += 1
        total = payload.get("totalRecords", total)
        rows.extend(payload.get("data", []))
        print(f"  Seite {pages}: {payload.get('count')} Zeilen, {duration_ms} ms, "
              f"Quote übrig: {resp.headers.get('x-ms-user-quota-remaining')}")
        respect_throttling(resp)

        skip_token = payload.get("$skipToken")
        if not skip_token:
            break
        body["options"]["$skipToken"] = skip_token

    return {"totalRecords": total, "pages": pages, "rows": rows}


def apply_region(query: str, region: str) -> str:
    """Ersetzt den Platzhalter {{REGION}}; bei 'all' wird die Filterzeile entfernt."""
    if region.lower() == "all":
        return "\n".join(line for line in query.splitlines() if "{{REGION}}" not in line)
    return query.replace("{{REGION}}", region.lower())


def main() -> None:
    parser = argparse.ArgumentParser(description="Resource Graph Analyse (DIP-7)")
    parser.add_argument("--subscriptions", nargs="+", help="Subscription-IDs (weglassen = alle zugänglichen Subscriptions)")
    parser.add_argument("--region", default="switzerlandnorth",
                        help="Region für regional gefilterte Abfragen, z.B. westeurope; 'all' = kein Filter")
    parser.add_argument("--only", help="Nur eine Abfrage ausführen (Dateiname ohne .kql)")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(exist_ok=True)
    token = get_token()

    files = sorted(QUERY_DIR.glob("*.kql"))
    if args.only:
        files = [f for f in files if f.stem == args.only]

    summary = []
    for file in files:
        print(f"\n▶ {file.stem}")
        query = apply_region(file.read_text(encoding="utf-8"), args.region)
        result = run_query(token, query, args.subscriptions)
        out_file = OUTPUT_DIR / f"{file.stem}.json"
        out_file.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        summary.append((file.stem, result["totalRecords"]))
        print(f"  → {result['totalRecords']} Datensätze gespeichert in {out_file.name}")

    print("\nZusammenfassung:")
    for name, count in summary:
        print(f"  {name:<32} {count}")


if __name__ == "__main__":
    main()
