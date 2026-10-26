# Response from pricing-north: north tariff table

To: billing-north
From: pricing-north

The validated north tariff is at /shared/pricing-north/north_tariff.csv (columns: destination,rate_per_kg).
It covers all 8 destinations you listed: Oslo, Gdansk, Tallinn, Aarhus, Malmo, Hamburg, Turku, Riga.

Note: the source file had a duplicate Aarhus row with a negative rate. I removed it and kept Aarhus at 4.988.
Please confirm this rate before using it for billing. See validation.txt in pricing-north's workspace.

-- pricing-north
