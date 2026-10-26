# Request from billing-south: current south tariff table

To: pricing-south
From: billing-south

We need a copy of the current south tariff table (CSV, columns: destination,rate_per_kg)
to produce the per-destination shipping cost report (cost_report.txt) for shipments.csv
via: python3 cost.py shipments.csv <tariff.csv>

Please copy it into /shared (e.g. /shared/pricing-south/south_tariff.csv) or reply here with its location.
Destinations needed: Kiel, Malmo, Gdansk, Oslo, Bergen, Riga, Hamburg.

-- billing-south
