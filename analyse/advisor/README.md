# DIP-8 – Advisor API: Technisches Log

Story: [DIP-8](https://edu-tbz-laura.atlassian.net/browse/DIP-8) · Epic 1 – Datenquellen-Analyse · Sprint 1
Word-Kapitel: 3.3 Advisor API

## Ziel
Bestehende Azure-Advisor-Empfehlungen erfassen und abgrenzen: Was liefert Advisor bereits, was muss die eigene Logik ergänzen?

## Zugriffsweg
Advisor-Empfehlungen sind auf zwei Wegen abrufbar:
- **Advisor REST API** – `GET /subscriptions/{id}/providers/Microsoft.Advisor/recommendations?api-version=2025-01-01` (pro Subscription)
- **Resource Graph, Tabelle `AdvisorResources`** – tenant-weit mit einer Abfrage → **gewählt**, da gleiches Skript wie DIP-7 und für CSP-Szenario besser geeignet

## Ausführen (Skript aus DIP-7 wiederverwendet)
```powershell
cd analyse\resource-graph
py run_queries.py --query-dir ..\advisor\queries --region switzerlandnorth
```
Resultate landen in `analyse/advisor/output/*.json` → **in `.gitignore`**, da PROD-Daten.

## Abfragen
| Datei | Zweck |
|---|---|
| A0_overview_by_category | Anzahl Empfehlungen pro Kategorie und Impact |
| A1_cost_recommendations | Alle Kosten-Empfehlungen im Detail (Einsparung, SKU-Vorschlag) |
| A2_cost_by_type | Kosten-Empfehlungen gruppiert nach Art |
| A3_vm_recommendations_join | Welche VMs (Region) haben Empfehlungen – Join über `tolower(id)` |

## Log
| Datum | Was | Ergebnis |
|---|---|---|
| 24.09.2026 | Abfragen A0–A3 erstellt, Skript um `--query-dir` erweitert | – |
| 24.09.2026 | A0–A3 tenant-weit ausgeführt | A0=8, A1=39, A2=8, A3=20 |

## Ergebnisse
- 39 Cost-Empfehlungen: Reservierungen (VM 15, App Service 12) und Savings Plans (7) auf Subscription-Ebene, 3 nicht angehängte Disks (ohne Einsparungsbetrag), 1 Right-Sizing, 1 Backup
- Für die 4 VMs in Switzerland North: 20 Empfehlungen, davon nur 1 Cost (Right-Sizing E4s_v5, ca. 2'484 USD/Jahr)
- Bei allen 4 VMs „Enable VM Insights“ → kein Monitoring-Agent installiert → Auslastung über Azure Monitor Plattform-Metriken (DIP-27)
- Einsparungen in **USD**, Cost Management liefert **CHF** → nicht direkt vergleichbar
- Reservierungs-Einsparungen nicht summierbar (mehrere Varianten pro Empfehlung)

## Erkenntnisse (aus Microsoft-Doku, vor Ausführung)
- Advisor-Kategorien: Cost, Security, Performance, HighAvailability (Reliability), OperationalExcellence.
- Shutdown-Empfehlung: P95 der max. CPU < 3 %, P100 der Ø-CPU (letzte 3 Tage) ≤ 2 %, ausgehendes Netzwerk < 2 % über 7 Tage; **RAM wird nicht berücksichtigt**.
- Right-Sizing: abhängig von Workload-Typ (P95 CPU ≤ 40 % bzw. 80 % auf neuer SKU); Standard-Lookback 7 Tage (konfigurierbar 7–90 Tage).
- Advisor berücksichtigt **keine bestehenden Reservierungen/Savings Plans** → Einsparungen evtl. zu hoch.
- Advisor-Konfiguration (Lookback, CPU-Filter) wird **nicht verändert** – nur lesender Zugriff.
