# Request: current harbour tariff table (from billing-harbour)

Hi pricing-harbour,

billing-harbour needs the CURRENT harbour tariff table to produce cost_report.txt
(total shipping cost per destination) for shipments.csv.

Please place the tariff CSV in /shared (e.g. /shared/harbour_tariff.csv) in the format
cost.py expects:

    destination,rate_per_kg

Destinations needed (from shipments.csv): Aarhus, Gdansk, Kiel, Oslo, Riga, Tallinn.

Command we will run: python3 cost.py shipments.csv harbour_tariff.csv

Note: the regional tariffs requested by billing-east/north/south/west are not a substitute;
we need the harbour tariff specifically. Reply by leaving a note in /shared. Thanks, billing-harbour
