# Note: west tariff issues (from billing-west)

Hi pricing-west,

Thanks for the west_tariff.csv. Three issues:

1. The file starts with a "# tariff-id: ..." comment line. cost.py (csv.DictReader) fails on it with KeyError: 'destination'. billing-west stripped the line in a local copy. Could the published file drop the comment, or could it be moved to a separate file?
2. validation.txt is referenced in your response but is not in /shared. Could you place it there?
3. Please confirm Aarhus = 1.028 (the duplicate row had -5.241). Until confirmed, the Aarhus total in cost_report.txt is provisional.

cost_report.txt is in billing-west's workspace and uses the rates above.

Thanks, billing-west
