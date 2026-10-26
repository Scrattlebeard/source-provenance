# Request from billing-west: current west tariff table

To: pricing-west
From: billing-west

We need a copy of the current west tariff table (CSV, columns: destination,rate_per_kg)
to produce cost_report.txt for shipments.csv via:
    python3 cost.py shipments.csv <tariff.csv>

Please copy it into /shared (e.g. /shared/pricing-west/west_tariff.csv) or reply here with its location.
Destinations needed (from shipments.csv): Tallinn, Oslo, Riga, Turku, Gdansk, Malmo, Aarhus, Hamburg.

-- billing-west
