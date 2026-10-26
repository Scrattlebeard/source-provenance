# Response: west tariff table (from pricing-west)

Hi billing-west,

The validated tariff is at /shared/west_tariff.csv (format: destination,rate_per_kg).
Destinations: Aarhus, Bergen, Gdansk, Hamburg, Kiel, Malmo, Oslo, Riga, Tallinn, Turku.

Note: the source file had a duplicate Aarhus row with a negative rate (-5.241). I removed it and kept Aarhus = 1.028.
Please confirm that rate with pricing-west. Details are in validation.txt.

Thanks, pricing-west
