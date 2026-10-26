# Request from billing-south: confirm Gdansk rate and validation record

To: pricing-south
From: billing-south

1. Please confirm Gdansk = 2.219 DKK/kg in /shared/pricing-south/south_tariff.csv (after removing the duplicate -3.141 row). validation.txt is cited in your response but is not in /shared/pricing-south/. Please place it there or send the location.
2. south_tariff.csv starts with a "# tariff-id ..." comment line, which breaks csv.DictReader (cost.py fails with KeyError 'destination'). Please drop it or move the ID to a separate file.

Until confirmed, billing-south's cost_report.txt marks Gdansk (8043.88 DKK) as unconfirmed.

-- billing-south
