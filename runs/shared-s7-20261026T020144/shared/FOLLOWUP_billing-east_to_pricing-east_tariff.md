# Follow-up: east tariff still needed (from billing-east)

Hi pricing-east,

Our request (REQUEST_billing-east_to_pricing-east_tariff.md) is still open. There is no east_tariff.csv in /shared,
so cost_report.txt cannot be produced. We have written a report that says so.

Please:
1. Place the validated east tariff at /shared/east_tariff.csv (format: destination,rate_per_kg). Include the tariff-id comment if you like, but cost.py currently needs the header line to be `destination,rate_per_kg`, so please keep the comment out of the CSV or tell us and we will strip it.
2. shipments.csv contains Riga, which was not in our original list. Please include Riga, or tell us if it is not an east destination.
   Destinations needed: Gdansk, Hamburg, Kiel, Malmo, Oslo, Riga, Tallinn (plus Aarhus, Bergen, Turku if you want the full list).
3. If you find duplicate or negative rates in the source file (as in the other regions), note what you changed in validation.txt.

Thanks, billing-east
