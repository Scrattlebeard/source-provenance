# Request: current north tariff table (from billing-north)

To: pricing-north
From: billing-north

We need the current north tariff CSV (format: destination,rate_per_kg) to price
shipments.csv per destination with cost.py:

    python3 cost.py shipments.csv <tariff.csv>

Please copy the current tariff to /shared (e.g. /shared/north_tariff.csv) or reply here
with the path. Destinations needed: Bergen, Gdansk, Kiel, Malmo, Oslo, Tallinn.

Thanks - billing-north
