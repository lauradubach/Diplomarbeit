# Automatisiertes Azure-Kostenmanagement für Managed Service Provider

Prototyp im Rahmen der Diplomarbeit (HF Dipl. Informatiker/in, TBZ) von Laura Dubach.

## Worum geht's

Ein Python-basiertes Skript, das Azure-Verrechnungsdaten, Ressourcennutzung und Advisor-Empfehlungen kombiniert, um automatisierte, wirtschaftlich relevante Kostenoptimierungs-Empfehlungen für KMU-Kunden eines Managed Service Providers zu generieren – inkl. automatischer Ticket-Erstellung in Jira.

**Scope:** VM-bezogene Ressourcen, Region Switzerland North, CSP-Perspektive.
**Out of Scope:** Lizenzkosten, andere Azure-Services, Multi-Region, produktiver Einsatz.

## Was hier entsteht

- **Datenanbindung** an Cost Management/Billing API, Resource Graph API und Advisor API
- **Konfigurierbare Entscheidungslogik** mit Schwellenwerten für mind. 3 Empfehlungstypen (z. B. Right-Sizing, Reservierungen, Abschaltung ungenutzter Ressourcen)
- **Automatisierte Jira-Ticket-Erstellung** mit Ressourcenname, Empfehlungstyp, prognostizierter Einsparung und Massnahme
- **End-to-End-Nachweis** auf anonymisierten/synthetischen Testdaten in einem CSP-Test-Tenant

## Tech Stack

- Python, Azure SDK
- Jira REST API
- Power BI / Azure Workbooks (optionale Visualisierung)

## Status

In Entwicklung – Projektlaufzeit 14.09.–18.12.2026

## Hinweis zu Testdaten

Es werden ausschliesslich anonymisierte oder synthetisch generierte Testdaten verwendet. Es erscheinen keine echten Kundendaten in Code, Dokumentation oder Screenshots.