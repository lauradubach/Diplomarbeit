# DIP-7 – Resource Graph API: Technisches Log

Story: [DIP-7](https://edu-tbz-laura.atlassian.net/browse/DIP-7) · Epic 1 – Datenquellen-Analyse · Sprint 1
Word-Kapitel: 3.2 Resource Graph API

## Ziel
Ressourcenmetadaten (VMs + direkt assoziierte Komponenten, Switzerland North) per Resource Graph abfragen
und die Felder identifizieren, die die Entscheidungslogik (Epic 2) braucht.

## Setup
```powershell
py -m pip install azure-identity requests
az login --tenant <SERVICE_TENANT_ID>
```
Benötigte Rolle: **Reader** auf den abgefragten Subscriptions (Resource Graph zeigt nur, was RBAC erlaubt).

## Ausführen
```powershell
py run_queries.py                                   # alle zugänglichen Subscriptions, Region Switzerland North
py run_queries.py --region all                      # ohne Regionsfilter
py run_queries.py --region westeurope               # andere Region
py run_queries.py --subscriptions <SUB_ID>          # nur bestimmte Subscriptions
py run_queries.py --only 00_vm_powerstate_overview  # einzelne Abfrage
```
Resultate landen in `output/*.json` → **in `.gitignore`**, da PROD-Daten.
Für Screenshots in der Doku: Subscription-IDs / Kundennamen schwärzen.

## Abfragen
| Datei | Zweck | Regionsfilter | Empfehlungstyp |
|---|---|---|---|
| 00_vm_powerstate_overview | VMs pro Subscription, Region, Power State | nein | Überblick |
| 01_vm_overview | VMs pro Subscription/Region | nein | Überblick |
| 02_vm_inventory | VM-Inventar mit Grösse, OS, Power State, Lizenz, Tags | ja | Right-Sizing, Reservierung |
| 03_vm_stopped_deallocated | Gestoppte/deallokierte VMs | nein | Abschaltung |
| 04_unattached_disks | Nicht angehängte Managed Disks | nein | Abschaltung/Aufräumen |
| 05_unassociated_public_ips | Nicht zugeordnete Public IPs | nein | Abschaltung/Aufräumen |
| 06_orphaned_nics | NICs ohne VM | nein | Aufräumen (kostenneutral) |
| 07_reservation_candidates | Laufende VMs nach Grösse + Region | nein | Reservierung |
| 08_vm_with_disks_join | VM + OS-Disk-SKU (Join) | ja | Right-Sizing (assoziierte Komponenten) |

## Log
| Datum | Was | Ergebnis |
|---|---|---|
| 23.09.2026 | Abfragen Q1–Q8 + Skript erstellt | – |
| 23.09.2026 | Q1–Q8 gegen Subscription aus DIP-6 ausgeführt | 0 Treffer – keine VM-Ressourcen in dieser Subscription |
| 23.09.2026 | Q1–Q8 gegen zweite Subscription ausgeführt | Q1=1, Q3=2, Q4=1, Q6=1, übrige 0 – VMs ausserhalb Switzerland North, keine laufend |
| 23.09.2026 | Skript erweitert: `--region`, Abfrage aller Subscriptions, neue Abfrage Q0 | – |
| 23.09.2026 | Q0 über alle Subscriptions, ohne Regionsfilter | 4 VMs running (Switzerland North), 2 deallocated (West Europe) |
| 23.09.2026 | Q0–Q8 über alle Subscriptions (Region Switzerland North) | Q2=4, Q3=2, Q4=3, Q5=0, Q6=1, Q7=3, Q8=4; Antwortzeit 0.5–1.2 s, keine Paginierung nötig |
| offen | Join mit Cost-Management-Daten über `tolower(id)` | wird in DIP-16 verifiziert |

## Erkenntnisse
- **Tenant-weit abfragen:** Bei einzelnen Subscriptions wurden die laufenden VMs zunächst nicht gefunden. Ohne `--subscriptions` fragt das Skript alle zugänglichen Subscriptions ab – für das CSP-Szenario zuverlässiger.
- **Join-Schlüssel zu Cost Management:** `ResourceId` in Cost Management ist klein geschrieben → in allen Abfragen `tolower(id)`.
- **Keine Metriken:** Resource Graph liefert keine CPU-/RAM-Auslastung. Für Right-Sizing braucht es Azure Monitor Metrics oder Advisor als Proxy → mit Roger klären.
- **Keine Historie:** Nur aktueller Zustand; wie lange eine VM schon deallokiert ist, ist nicht direkt ablesbar.
- **Stopped ≠ Deallocated:** `stopped` verursacht weiterhin Compute-Kosten.
- Hinweis für DIP-8: Advisor-Empfehlungen sind auch über die Tabelle `AdvisorResources` in Resource Graph abfragbar.