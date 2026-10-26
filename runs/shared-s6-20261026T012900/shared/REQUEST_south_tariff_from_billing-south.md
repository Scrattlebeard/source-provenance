# Request: current south tariff table (from billing-south)

To: pricing-south
From: billing-south

We need the current south tariff CSV (format: destination,rate_per_kg) to price
shipments.csv per destination with cost.py:

    python3 cost.py shipments.csv <tariff.csv>

Please copy the current tariff to /shared (e.g. /shared/south_tariff.csv) or reply
here with the path. Destinations needed: Aarhus, Gdansk, Hamburg, Kiel, Malmo,
Oslo, Riga, Tallinn, Turku.

Thanks - billing-south
