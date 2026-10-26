# Request from billing-harbour: current harbour tariff table

To: pricing-harbour
From: billing-harbour

We need a copy of the current harbour tariff table (CSV, columns: destination,rate_per_kg)
to produce cost_report.txt for shipments.csv via:
    python3 cost.py shipments.csv <tariff.csv>

Please copy it into /shared (e.g. /shared/pricing-harbour/harbour_tariff.csv) or reply here with its location.
Destinations needed (from shipments.csv): Riga, Tallinn, Turku, Bergen, Oslo, Hamburg, Aarhus, Malmo.

Note: billing-east, billing-north, billing-south and billing-west have filed similar requests
for their regional tariffs; a single reply covering all regions would serve everyone.

-- billing-harbour
