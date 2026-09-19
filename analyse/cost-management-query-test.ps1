$token = az account get-access-token --resource https://management.azure.com --query accessToken -o tsv

$body = @'
{
  "type": "ActualCost",
  "timeframe": "MonthToDate",
  "dataset": {
    "granularity": "Daily",
    "aggregation": { "totalCost": { "name": "PreTaxCost", "function": "Sum" } },
    "grouping": [{ "name": "ResourceId", "type": "Dimension" }]
  }
}
'@

Invoke-RestMethod `
  -Uri "https://management.azure.com/subscriptions/0576f223-f60a-4e64-839e-066b2558a5ec/providers/Microsoft.CostManagement/query?api-version=2025-03-01" `
  -Method POST `
  -Headers @{ Authorization = "Bearer $token"; ClientType = "dip-diplomarbeit" } `
  -ContentType "application/json" `
  -Body $body