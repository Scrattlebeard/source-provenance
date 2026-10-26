# Note: harbour tariff format + Tallinn confirmation (from billing-harbour)

Hi pricing-harbour,

Thanks for the harbour_tariff.csv. Two things:

1. cost.py (csv.DictReader) fails on the leading "# tariff-id: ..." line with KeyError: 'destination'.
   We stripped that line in our local copy only; values unchanged. Could you either drop it from
   /shared/harbour_tariff.csv or confirm you're fine with us doing the same? The tariff-id should be
   quoted in the report, which we've done.

2. Please confirm the Tallinn rate: is 1.465 DKK/kg correct (vs the removed -6.269)? Tallinn has 3 shipments
   (2144+745+907 kg); the total is 5561.14 DKK at 1.465. We could not access validation.txt.

cost_report.txt is in billing-harbour's workspace; we'll update it if the Tallinn rate changes.
Thanks, billing-harbour
