"""
DIP-27 – Azure Monitor Metrics API: Auslastungsdaten der VMs

1. Holt die laufenden VMs einer Region über Resource Graph (wie DIP-7)
2. Fragt pro VM die Plattform-Metriken der Azure Monitor Metrics API ab (ohne Agent, nur lesend)
3. Speichert Rohdaten + Zusammenfassung unter output/ (NICHT committen – PROD-Daten!)

In der Konsole werden die VMs nur als VM1, VM2, ... angezeigt (Screenshot-tauglich).
Die Zuordnung zu den echten Namen steht in output/summary.json.

Aufruf:
    cd analyse\\monitor
    py get_vm_metrics.py                         # letzte 30 Tage, Switzerland North
    py get_vm_metrics.py --days 14 --region switzerlandnorth
"""

import argparse
import json
import statistics
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

# Funktionen aus DIP-7 wiederverwenden (Token + Resource-Graph-Abfrage)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "resource-graph"))
from run_queries import get_token, run_query  # noqa: E402

API_VERSION = "2023-10-01"
INTERVAL = "PT1H"  # stündliche Werte: genug Detail, überschaubare Datenmenge
METRICS = {
    "Percentage CPU": "average,maximum",
    "Available Memory Percentage": "average,minimum",
    "Network Out Total": "total",
}
OUTPUT_DIR = Path(__file__).resolve().parent / "output"

VM_QUERY = """
Resources
| where type =~ 'microsoft.compute/virtualmachines'
| where location =~ '{region}'
| extend vmSize = tostring(properties.hardwareProfile.vmSize),
         powerState = tostring(properties.extended.instanceView.powerState.code)
| where powerState =~ 'PowerState/running'
| project id, name, vmSize, timeCreated = tostring(properties.timeCreated)
| order by name asc
"""


def get_metrics(token: str, vm_id: str, start: datetime, end: datetime) -> dict:
    """Alle Metriken einer VM in einem Aufruf je Aggregationsgruppe."""
    headers = {"Authorization": f"Bearer {token}"}
    timespan = f"{start:%Y-%m-%dT%H:%M:%SZ}/{end:%Y-%m-%dT%H:%M:%SZ}"
    result = {}
    for metric, aggregation in METRICS.items():
        params = {
            "api-version": API_VERSION,
            "metricnames": metric,
            "aggregation": aggregation,
            "timespan": timespan,
            "interval": INTERVAL,
        }
        url = f"https://management.azure.com{vm_id}/providers/Microsoft.Insights/metrics"
        while True:
            resp = requests.get(url, headers=headers, params=params, timeout=60)
            if resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", "10"))
                print(f"    HTTP 429 – warte {wait}s")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            break
        values = resp.json().get("value", [])
        points = values[0]["timeseries"][0]["data"] if values and values[0].get("timeseries") else []
        result[metric] = points
    return result


def p95(values: list[float]) -> float | None:
    if len(values) < 2:
        return values[0] if values else None
    return statistics.quantiles(values, n=100, method="inclusive")[94]


def summarize(metrics: dict) -> dict:
    cpu = metrics.get("Percentage CPU", [])
    cpu_avg = [p["average"] for p in cpu if p.get("average") is not None]
    cpu_max = [p["maximum"] for p in cpu if p.get("maximum") is not None]
    mem = metrics.get("Available Memory Percentage", [])
    mem_avg = [p["average"] for p in mem if p.get("average") is not None]
    mem_min = [p["minimum"] for p in mem if p.get("minimum") is not None]
    net = metrics.get("Network Out Total", [])
    net_total = sum(p["total"] for p in net if p.get("total") is not None)

    def r(x):
        return round(x, 1) if x is not None else None

    return {
        "datenpunkte_cpu": len(cpu_avg),
        "cpu_avg_pct": r(statistics.mean(cpu_avg)) if cpu_avg else None,
        "cpu_p95_pct": r(p95(cpu_avg)),
        "cpu_max_pct": r(max(cpu_max)) if cpu_max else None,
        "ram_genutzt_avg_pct": r(100 - statistics.mean(mem_avg)) if mem_avg else None,
        "ram_genutzt_max_pct": r(100 - min(mem_min)) if mem_min else None,
        "netzwerk_out_gb": r(net_total / 1024**3),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Azure Monitor Metrics (DIP-27)")
    parser.add_argument("--days", type=int, default=30, help="Betrachtungszeitraum in Tagen (max. 93)")
    parser.add_argument("--region", default="switzerlandnorth")
    args = parser.parse_args()

    end = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    start = end - timedelta(days=min(args.days, 93))
    OUTPUT_DIR.mkdir(exist_ok=True)
    token = get_token()

    print(f"▶ Laufende VMs in {args.region} über Resource Graph abfragen")
    vms = run_query(token, VM_QUERY.format(region=args.region.lower()), None)["rows"]
    print(f"  → {len(vms)} VMs gefunden\n")

    summary = []
    print(f"▶ Metriken {start:%d.%m.%Y} – {end:%d.%m.%Y} ({args.days} Tage, Intervall {INTERVAL})")
    for i, vm in enumerate(vms, start=1):
        label = f"VM{i}"
        started = time.perf_counter()
        metrics = get_metrics(token, vm["id"], start, end)
        duration_ms = round((time.perf_counter() - started) * 1000)
        s = summarize(metrics)
        print(f"  {label} ({vm['vmSize']}): {s['datenpunkte_cpu']} Datenpunkte, {duration_ms} ms")
        (OUTPUT_DIR / f"{label}_raw.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        summary.append({"label": label, "name": vm["name"], "id": vm["id"], "vmSize": vm["vmSize"],
                        "timeCreated": vm.get("timeCreated"), **s})

    (OUTPUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\nZusammenfassung (CPU/RAM in %, Netzwerk in GB):")
    header = f"  {'VM':<5}{'Grösse':<18}{'Punkte':>7}{'CPU Ø':>8}{'CPU P95':>9}{'CPU max':>9}{'RAM Ø':>8}{'RAM max':>9}{'Net GB':>8}"
    print(header)

    def f(v):
        return "-" if v is None else v

    for s in summary:
        print(f"  {s['label']:<5}{s['vmSize']:<18}{s['datenpunkte_cpu']:>7}"
              f"{f(s['cpu_avg_pct']):>8}{f(s['cpu_p95_pct']):>9}{f(s['cpu_max_pct']):>9}"
              f"{f(s['ram_genutzt_avg_pct']):>8}{f(s['ram_genutzt_max_pct']):>9}{f(s['netzwerk_out_gb']):>8}")


if __name__ == "__main__":
    main()
