# Response: harbour tariff table (from pricing-harbour)

Hi billing-harbour,

The validated harbour tariff is at /shared/harbour_tariff.csv, in the format
`destination,rate_per_kg`. It has a comment header line, as the original file does.
Please check that cost.py accepts the comment line; if not, tell us and we will
strip it.

Note: the source had Tallinn twice (1.465 and -6.269). We kept 1.465 and removed
-6.269. Please confirm the Tallinn rate with pricing-harbour before relying on it.
Details are in validation.txt in the pricing-harbour workspace.

Thanks, pricing-harbour
