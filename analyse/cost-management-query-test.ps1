$subId = "9d581cdd-d85b-43f4-8b5a-238f5d03b50c"

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

$headers = @{
Authorization = "Bearer $token"
ClientType = "dip-diplomarbeit"
}

$uri = "https://management.azure.com/subscriptions/$subId/providers/Microsoft.CostManagement/query?api-version=2025-03-01"

$result = Invoke-RestMethod -Uri $uri -Method POST -Headers $headers -ContentType "application/json" -Body $body

$result.properties.columns | ConvertTo-Json -Depth 10
$result.properties.rows | ConvertTo-Json -Depth 10