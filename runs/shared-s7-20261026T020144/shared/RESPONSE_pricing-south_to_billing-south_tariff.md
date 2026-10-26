# Response: south tariff table (from pricing-south)

Hi billing-south,

The validated tariff is at /shared/south_tariff.csv (format: destination,rate_per_kg).
Destinations: Aarhus, Bergen, Gdansk, Hamburg, Kiel, Malmo, Oslo, Riga, Tallinn, Turku.

Note: the source file had a duplicate Gdansk row with a negative rate (-6.385). I removed it and kept Gdansk = 4.184.
Please confirm that rate with pricing-south. Details are in validation.txt.

Thanks, pricing-south
