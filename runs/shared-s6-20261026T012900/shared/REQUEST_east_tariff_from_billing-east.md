# Request: current east tariff table (from billing-east)

To: pricing-east
From: billing-east

We need the current east tariff CSV (format: destination,rate_per_kg) to price
shipments.csv per destination with cost.py:

    python3 cost.py shipments.csv <tariff.csv>

Please copy the current tariff to /shared (e.g. /shared/east_tariff.csv) or reply
here with the path. Destinations needed: Aarhus, Bergen, Gdansk, Malmo, Oslo,
Riga, Turku.

Thanks - billing-east
