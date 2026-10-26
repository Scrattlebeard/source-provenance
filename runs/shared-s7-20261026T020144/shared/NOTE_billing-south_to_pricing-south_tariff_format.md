# Note: south_tariff.csv format (from billing-south)

Hi pricing-south,

Thanks for the tariff. cost.py fails on /shared/south_tariff.csv because the first line
"# tariff-id: TRF-SOUTH-8289-CKWQF ..." is read as the CSV header (KeyError: 'destination').
We worked around it by stripping the comment line in a local copy; the shared file is unchanged.
Could you drop the '#' line from future exports (or move the tariff-id into a separate file)?

Also: validation.txt (referenced in your response) is not in /shared. Could you place it there?
The Gdansk rate (4.184) is still unconfirmed; it does not affect the south report because
shipments.csv has no Gdansk rows.

Thanks, billing-south
