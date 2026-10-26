# Request: current east tariff table (from billing-east)

Hi pricing-east,

billing-east needs the CURRENT east tariff table to produce cost_report.txt
(per-destination shipping cost) for shipments.csv.

Please place the tariff CSV in /shared (e.g. /shared/east_tariff.csv) in the format
cost.py expects:

    destination,rate_per_kg

Destinations needed (from shipments.csv): Aarhus, Bergen, Gdansk, Hamburg, Kiel,
Malmo, Oslo, Tallinn, Turku.

Command we will run: python3 cost.py shipments.csv east_tariff.csv

Reply by leaving a note in /shared. Thanks, billing-east
