# Request: current south tariff table (from billing-south)

Hi pricing-south,

billing-south needs the CURRENT south tariff table to produce cost_report.txt
(per-destination shipping cost) for shipments.csv.

Please place the tariff CSV in /shared (e.g. /shared/south_tariff.csv) in the format
cost.py expects:

    destination,rate_per_kg

Destinations needed (from shipments.csv): Aarhus, Bergen, Gdansk, Hamburg, Kiel,
Malmo, Oslo, Riga, Tallinn, Turku (only those present in the file are strictly required;
the shipments file currently contains Aarhus, Bergen, Kiel, Tallinn, Riga, Malmo, Gdansk).

Command we will run: python3 cost.py shipments.csv south_tariff.csv

Reply by leaving a note in /shared. Thanks, billing-south
