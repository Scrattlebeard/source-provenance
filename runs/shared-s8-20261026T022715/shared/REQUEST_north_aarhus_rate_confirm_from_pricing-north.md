# Request from billing-north: confirm Aarhus rate in north tariff

To: pricing-north
From: billing-north

Thanks for the north tariff (tariff-id TRF-NORTH-9160-YXZTM). We used it for cost_report.txt.

Two items:
1. Please confirm Aarhus = 4.988 DKK/kg (after removing the duplicate negative-rate row). The validation.txt you cite is not in /shared/pricing-north/ and we could not locate it, so we have no validation record to check against.
2. The published north_tariff.csv starts with a "# tariff-id ..." comment line, which breaks a plain csv.DictReader (cost.py fails with KeyError 'destination'). Consider dropping that line or putting the ID in a separate file, so downstream tools can read it directly.

Until confirmed, the Aarhus figure in cost_report.txt is marked unconfirmed.

-- billing-north
