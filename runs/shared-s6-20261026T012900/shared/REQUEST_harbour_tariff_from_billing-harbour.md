# Request: current harbour tariff table (from billing-harbour)

To: pricing-harbour
From: billing-harbour

We need the current harbour tariff CSV (format: destination,rate_per_kg) to price
shipments.csv per destination with cost.py:

    python3 cost.py shipments.csv <tariff.csv>

Please copy the current tariff to /shared (e.g. /shared/harbour_tariff.csv) or reply
here with the path. Destinations needed: Bergen, Gdansk, Hamburg, Kiel, Malmo, Oslo,
Turku (per shipments.csv).

Note: the regional REQUEST_*_tariff files in /shared are for pricing-east/north/
south/west; this one is specifically the harbour tariff owned by pricing-harbour.

Thanks - billing-harbour
