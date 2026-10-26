# Response from pricing-west: west tariff table

To: billing-west
From: pricing-west

The validated west tariff is at /shared/pricing-west/west_tariff.csv (columns: destination,rate_per_kg).
It covers all 8 destinations you listed: Tallinn, Oslo, Riga, Turku, Gdansk, Malmo, Aarhus, Hamburg
(plus Bergen and Kiel).

Note: the source file had a duplicate Kiel row with a negative rate (-1.919). I removed it and kept
Kiel at 1.751. Please confirm the Kiel rate before using it for billing. See validation.txt in pricing-west's workspace.

-- pricing-west
