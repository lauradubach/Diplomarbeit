# DIP-27 – Azure Monitor Metrics API: Technisches Log

Story: [DIP-27](https://edu-tbz-laura.atlassian.net/browse/DIP-27) · Epic 1 – Datenquellen-Analyse · Sprint 1
Word-Kapitel: 3.x Azure Monitor Metrics API

## Ziel
Auslastungsdaten (CPU, RAM, Netzwerk) der VMs für die Right-Sizing-Logik abfragen – **ohne Agent, nur lesend**
(Entscheid mit Roger Knecht vom 23.09.2026).

## Endpoint
`GET https://management.azure.com/{vmResourceId}/providers/Microsoft.Insights/metrics?api-version=2023-10-01`
Parameter: `metricnames`, `aggregation`, `timespan` (Start/Ende ISO 8601), `interval` (z. B. PT1H)

## Verwendete Plattform-Metriken (ohne Agent verfügbar)
| Metrik | Einheit | Aggregation | Zweck |
|---|---|---|---|
| Percentage CPU | Percent | Average, Maximum | Right-Sizing, Abschaltung |
| Available Memory Percentage | Percent | Average, Minimum | Right-Sizing (RAM) |
| Network Out Total | Bytes | Total | Abschaltung (Advisor-Kriterium) |

## Ausführen
```powershell
cd analyse\monitor
py get_vm_metrics.py                 # letzte 30 Tage, Switzerland North
py get_vm_metrics.py --days 14
```
- Holt die laufenden VMs über Resource Graph (Funktionen aus `resource-graph/run_queries.py`)
- Konsole zeigt VMs nur als VM1–VM4 (Screenshot-tauglich)
- `output/summary.json` + `output/VMx_raw.json` → **in `.gitignore`**, da PROD-Daten

## Kennzahlen in der Zusammenfassung
- **CPU Ø** – Mittelwert der Stundenmittel
- **CPU P95** – 95. Perzentil der Stundenmittel (95 % der Stunden liegen darunter)
- **CPU max** – höchster Minutenwert im Zeitraum
- **RAM Ø / max** – genutzter RAM = 100 % − verfügbarer RAM
- **Net GB** – ausgehender Netzwerkverkehr gesamt

## Log
| Datum | Was | Ergebnis |
|---|---|---|
| 25.09.2026 | Skript erstellt | – |
| 25.09.2026 | Skript gegen Service-Tenant ausgeführt (30 Tage, PT1H) | 4 VMs, je 720 Datenpunkte, 9–13 s pro VM |

## Ergebnisse
- CPU bei allen 4 VMs tief (P95 6–7 %) → nach CPU allein wären alle überdimensioniert
- RAM differenziert: nur VM2 (E4s_v5) auch RAM-seitig tief (Ø 34 %) → deckt sich mit Advisor-Empfehlung
- VM1 (D4s_v5) RAM Ø 85 %, VM3/4 (F2s_v2) RAM max 98–99 % → kein Verkleinern möglich
- CPU-Spitzen bis 91 % bei P95 von 6 % → Schwellenwerte auf P95 statt Maximum
- Alle VMs mit Netzwerkverkehr → keine Abschaltungskandidaten|

## Erkenntnisse (aus Microsoft-Doku, vor Ausführung)
- Plattform-Metriken werden **93 Tage** aufbewahrt, im Minutentakt erfasst.
- Pro Aufruf max. 20 Metriken; für viele VMs gibt es eine Batch-API (bis 50 Ressourcen pro Aufruf).
- RAM ist **ohne Agent** als Host-Metrik verfügbar (Available Memory Percentage) – genauere OS-Daten (Laufwerke, Prozesse) nur mit Azure Monitor Agent.
