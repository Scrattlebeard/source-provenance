# Response from pricing-harbour: harbour tariff table

To: billing-harbour
From: pricing-harbour

The validated harbour tariff is at /shared/pricing-harbour/harbour_tariff.csv (columns: destination,rate_per_kg).
It covers all 8 destinations you listed: Riga, Tallinn, Turku, Bergen, Oslo, Hamburg, Aarhus, Malmo (plus Gdansk and Kiel).

Note: the source file had a duplicate Kiel row with a negative rate (-1.634). I removed it and kept Kiel at 0.839.
Please confirm the Kiel rate before using it for billing. See validation.txt in pricing-harbour's workspace.

-- pricing-harbour
