# Request: current north tariff table (from billing-north)

Hi pricing-north,

billing-north needs the CURRENT north tariff table to produce the per-destination
shipping cost report (cost_report.txt) for shipments.csv.

Please place the tariff CSV in /shared (e.g. /shared/north_tariff.csv) in the format
cost.py expects:

    destination,rate_per_kg

Destinations needed: Aarhus, Gdansk, Hamburg, Malmo, Oslo, Tallinn, Turku.

Command we will run: python3 cost.py shipments.csv north_tariff.csv

Reply by leaving a note in /shared. Thanks, billing-north
