# Internal Ledger Model
## Relationships

```
LedgerTransaction (1) → (many) LedgerEntry → (1) Account
```
Account = bucket (e.g. revenue, stripe_clearing)
LedgerEntry = amount change on one account (+ / -)
LedgerTransaction = one business event grouping entries

## Money Flow
Example: user pays £10
```
user_balance -1000
revenue +1000
```
Both entries belong to the same transaction.

## Balance
```
balance(account) = SUM(entries.amount)
```
No stored balance
Computed from entries

## Invariant
```
SUM(entries in a transaction) = 0
```
Money is moved, never created

## Context
This ledger is the internal source of truth for money movement,
before reconciliation with external systems like Stripe.
