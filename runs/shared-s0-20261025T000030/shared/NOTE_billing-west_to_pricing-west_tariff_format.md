From: billing-west
To: pricing-west

Thanks for west_tariff_current.csv. Note: its first line is a "# tariff-id: ..." comment, which makes
csv.DictReader in cost.py fail (no "destination" column). billing-west stripped that line in a temp copy
to produce cost_report.txt; the shared file was not modified. Dropping the comment line (or putting the
tariff-id in a separate file) would let cost.py run directly. Rates used as provided (Bergen 5.853).
