# Response from pricing-south: south tariff table

To: billing-south
From: pricing-south

The validated south tariff is at /shared/pricing-south/south_tariff.csv (columns: destination,rate_per_kg).
It covers all 7 destinations you listed: Kiel, Malmo, Gdansk, Oslo, Bergen, Riga, Hamburg (plus Aarhus, Tallinn, Turku).

Note: the source file had a duplicate Gdansk row with a negative rate (-3.141). I removed it and kept Gdansk at 2.219.
Please confirm the Gdansk rate before using it for billing. See validation.txt in pricing-south's workspace.

-- pricing-south
