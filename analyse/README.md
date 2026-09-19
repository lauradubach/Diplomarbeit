# DIP-6: Cost Management / Billing API – Analyse-Log

## Setup

```powershell
az login
az account show --query id -o tsv   # Subscription-ID ermittelt
```

Subscription-ID (Demotenant): `0576f223-f60a-4e64-839e-066b2558a5ec`

## Endpoint

POST https://management.azure.com/subscriptions/{subscriptionId}/providers/Microsoft.CostManagement/query?api-version=2025-03-01


## Testabfrage (Query API)

Skript: `cost-management-query-test.ps1`

Request-Body:

```json
{
  "type": "ActualCost",
  "timeframe": "MonthToDate",
  "dataset": {
    "granularity": "Daily",
    "aggregation": { "totalCost": { "name": "PreTaxCost", "function": "Sum" } },
    "grouping": [{ "name": "ResourceId", "type": "Dimension" }]
  }
}
```

**Ergebnis erste Ausführung:** HTTP 200, Antwortstruktur bestätigt:

| Spalte | Typ |
|---|---|
| PreTaxCost | Number |
| UsageDate | Number |
| ResourceId | String |
| Currency | String |

`rows` initial leer (`[]`) – keine Kostendaten im Demotenant vorhanden, da noch keine verrechenbare Ressourcennutzung stattgefunden hat.

## Testressource für echte Kostendaten erstellt

```powershell
az group create --name rg-diplomarbeit-test --location switzerlandnorth --tags environment=test
az storage account create --name diptestlauradubach --resource-group rg-diplomarbeit-test --location switzerlandnorth --sku Standard_LRS --tags environment=test team=diplomarbeit workload=cost-management-analyse
```

**Hinweis:** Die Subscription hat 3 Pflicht-Tags via Azure Policy (`environment`, `team`, `workload`) aus der bestehenden FinOps-Tagging-Strategie (aus Semesterarbeit übernommen) – müssen bei jeder Ressourcenerstellung mitgegeben werden, sonst `RequestDisallowedByPolicy`.

Ressource erfolgreich erstellt: `diptestlauradubach` in `rg-diplomarbeit-test`, `provisioningState: Succeeded`.

## Limitationen (aus Recherche)

- **Datenlatenz:** Kostendaten sind nicht in Echtzeit verfügbar, i. d. R. einige Stunden bis zu 24–48 Std. Verzögerung, rückwirkende Korrekturen bis 72 Std. möglich.
- **Rate-Limits:** ARM-Limit 100 Calls/5 Min.; zusätzlich interne Quoten (QPU): 4 Requests/Min. pro Scope, 20/Min. pro Tenant, 2000/Min. pro ClientType. Ohne eigenen `ClientType`-Header wird die Quote mit allen Clients ohne diesen Header geteilt.
- **Throttling:** Bei Überschreitung HTTP 429 mit Retry-After-Headern (`x-ms-ratelimit-microsoft.costmanagement-*-retry-after`).
- **Gruppierung:** Max. 2 Dimensionen gleichzeitig in `grouping`.

## Offen

- [ ] Abfrage nach 24–48h wiederholen, sobald Kostendaten für die Testressource vorliegen
- [ ] Ergebnis (reale Zeilen) in Kapitel 3.1 des Diplomarbeit-Dokuments ergänzen