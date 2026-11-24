# Official sources (S1-01)

Launch services and the official pages their records are drafted from. Pages were fetched on 2026-11-23.
Records stay `partial` until a person checks each field against these pages and fills `verification`.

| Service | Record | Main source |
|---|---|---|
| Income certificate | `schemes/delhi-income-certificate.json` | https://revenue.delhi.gov.in/revenue/income-certificate |
| Merit Scholarship, SC/ST/OBC (chosen scholarship) | `schemes/delhi-merit-scholarship-scstobc.json` | https://scstwelfare.delhi.gov.in/sites/default/files/scstwelfare/circulars-orders/scholarship_schemes_2025-26_guidelines.pdf |
| Old-age pension (Old Age Assistance) | `schemes/delhi-old-age-pension.json` | https://socialwelfare.delhi.gov.in/social/financials-assistance-schemes |

Application portal for all three: https://edistrict.delhigovt.nic.in/

Every source of each record is listed in its `sources[]`. Where official pages disagree, the figure is left
out (null) and the conflict is described in `verification.notes`.

## Still to check by hand in a normal browser

- e-District service pages (blocked automated fetches).
- The full 2025-26 scholarship guidelines PDF (only partly read).
- Application window and portal for the merit scholarship.
- Grievance channels for all three services (not stated on the pages read).

## Forms (S4-01)

| Form | Saved as | Source | Linked from | Checked |
|---|---|---|---|---|
| Income certificate application, Revenue Department GNCTD (flat 3-page PDF) | `forms/delhi-income-certificate-application.pdf` | https://revenue.delhi.gov.in/sites/default/files/revenue/cc/input_9055.pdf | https://revenue.delhi.gov.in/revenue/income-certificate ("Complete Application form") | 2026-11-24 |

Not verified: whether the e-District office still accepts exactly this version; the header mixes "Surviving Member Certificate" and "Income Certificate". No old-age pension form PDF exists on the pages read (application is online on e-District).
