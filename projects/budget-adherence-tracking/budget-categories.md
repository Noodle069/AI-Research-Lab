# Budget categories (category level only)

Source: user's file `/Users/alphakings/Downloads/Offset_Budget_Master_and_Expanded.pdf` (read 2026-09-30). Item-level detail, provider names and personal names are deliberately not copied here; the app's config should be built from the source file when needed. Amounts are AUD per month.

| # | Category | Regular | Sinking | Total monthly transfer | What is included (generic) |
|---|---|---|---|---|---|
| 1 | House + Core Bills | 6,698.91 | 888.34 | 7,587.25 | Mortgage, council rates, water, building and contents insurance, electricity, pool, internet, phone, streaming and app subscriptions |
| 2 | Groceries + Household | 1,100.00 | 0.00 | 1,100.00 | Groceries, cleaning, toiletries, household basics |
| 3 | Eating Out + Convenience | 400.00 | 0.00 | 400.00 | Coffee, takeaway, restaurants, delivery |
| 4 | Medical + Psychology | 1,041.00 | 370.49 | 1,411.49 | Practitioner fees, pharmacy, health insurance, screening |
| 5 | Car + Transport | 432.90 | 547.10 | 980.00 | Fuel, vehicle insurance, rego, servicing, tyres, maintenance, tolls, club |
| 6 | Flights + Holidays | 0.00 | 800.00 | 800.00 | Flights, accommodation, travel costs, holiday fund |
| 7 | Personal + Fun | 473.00 | 215.00 | 688.00 | Barber, lotteries, clothing, events, misc |
| 8 | Gifts + Family + Child | 120.00 | 275.00 | 395.00 | Child school costs, gifts, birthdays, family |
| 9 | Emergency + Buffer | none | none | none (all income lands here first) | Emergency fund with a $50,000 minimum floor; unexpected repairs, appliances, medical surprises paid from it |
| 10 | Spare / future use | none | none | 0.00 | Unallocated |
| | **Total planned** | **10,265.81** | **3,096.93** | **13,361.74** | |

## Structure observed in the source (VERIFIED from the file)
- The source calls each category an "offset account": all income lands in the Buffer first, then planned transfers move out to each category.
- Two budget layers per category: "Actual / regular" (routine monthly spending) and "Sinking" (money set aside for irregular or future bills, e.g. rates, insurance, rego, holidays).
- Categories 9 and 10 have no monthly budget amount.
- Small rounding differences between the master table and the expanded items are noted as intentional.

## Data note (updated 2026-10-01)
The source PDF prints a Sinking total of 3,096.93. Its Sinking category rows sum to 3,095.93, and each row also equals the sum of its own item lines on pages 2-4 (checked by the main agent: categories 1, 4, 5, 6, 7 and 8 all match). The printed grand total 13,361.74 equals Regular 10,265.81 + 3,095.93; with 3,096.93 it would be 13,362.74.
The user said on 2026-10-01 that 3,096.93 is the total sinking fund for all categories. That leaves a $1.00 difference that no category row or item line accounts for. The app config keeps the row values (3,095.93) because they are supported by the item detail; the app should show totals computed from the rows. If the user wants an extra $1.00 somewhere, they need to say which category. UNRESOLVED, low impact.
