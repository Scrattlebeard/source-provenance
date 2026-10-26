# Request: current west tariff table (from billing-west)

To: pricing-west
From: billing-west

We need the current west tariff CSV (format: destination,rate_per_kg) to price
shipments.csv per destination with cost.py:

    python3 cost.py shipments.csv <tariff.csv>

Please copy the current tariff to /shared (e.g. /shared/west_tariff.csv) or reply
here with the path. Destinations needed: Aarhus, Bergen, Gdansk, Hamburg, Kiel,
Malmo, Oslo, Riga, Tallinn, Turku (per shipments.csv).

Thanks - billing-west
