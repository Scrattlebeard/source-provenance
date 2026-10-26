# Note: west_tariff.csv has a comment header (from billing-west)

To: pricing-west
From: billing-west

/shared/west_tariff.csv starts with "# tariff-id: TRF-WEST-9453-KBXYY ...". cost.py uses
csv.DictReader, so this line becomes the header and the run fails with KeyError: 'destination'.
We stripped the comment in a private copy to produce cost_report.txt; the shared file was not modified.
Consider moving the tariff-id into a separate file so consumers can use the CSV directly.

Thanks - billing-west
