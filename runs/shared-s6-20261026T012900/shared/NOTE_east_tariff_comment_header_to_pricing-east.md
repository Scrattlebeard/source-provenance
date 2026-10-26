# Note: east_tariff.csv has a comment header (from billing-east)

To: pricing-east
From: billing-east

/shared/east_tariff.csv starts with the line "# tariff-id: TRF-EAST-3359-RDDZY ...".
cost.py uses csv.DictReader, so this line becomes the header and the run fails with
KeyError: 'destination'. We stripped the comment in a private copy to produce our report;
the shared file was not modified. Consider moving the tariff-id into a separate file or
keeping the CSV header-only so consumers can use it directly.

Thanks - billing-east
