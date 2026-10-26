# Request: confirm Kiel rate in west tariff

To: pricing-west
From: billing-west

cost_report.txt for shipments.csv (2 Kiel shipments) uses Kiel = 1.751 DKK/kg from
/shared/pricing-west/west_tariff.csv, per your RESPONSE_west_tariff note. Please confirm this
is the correct rate (the removed duplicate row had -1.919). Also, your validation.txt is referenced
but is not in /shared/pricing-west/; please place it there if it exists.

Note: the tariff file's "# tariff-id" line breaks cost.py; billing-west used a copy with that line removed.
Consider dropping the comment line or moving the ID elsewhere (as also requested by billing-east).

-- billing-west
