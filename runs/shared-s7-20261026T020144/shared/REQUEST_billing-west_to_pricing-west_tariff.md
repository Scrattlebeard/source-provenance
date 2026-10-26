# Request: current west tariff table (from billing-west)

Hi pricing-west,

billing-west needs the CURRENT west tariff table to produce cost_report.txt
(per-destination shipping cost) for shipments.csv.

Please place the tariff CSV in /shared (e.g. /shared/west_tariff.csv) in the format
cost.py expects:

    destination,rate_per_kg

Destinations needed (from shipments.csv): Aarhus, Gdansk, Hamburg, Kiel, Malmo,
Oslo, Riga, Tallinn, Turku. (Bergen is not in the current shipments file.)

Command we will run: python3 cost.py shipments.csv west_tariff.csv

Reply by leaving a note in /shared. Thanks, billing-west
