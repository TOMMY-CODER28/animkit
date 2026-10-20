# Script — Gaussian Sum

*(Drafted by the AI from the thin request "animate the Gauss pairing trick";
marked assumptions approved by the user: audience = students meeting the
formula for the first time, n = 100, ~20 s.)*

## Stage 1 — The claim

Show: 1 + 2 + 3 + ⋯ + 100 = ?
Say: how do you add up the first hundred numbers without adding them one by one?
Math: N = 100

## Stage 2 — Pair them up

Show: (1 + 100) + (2 + 99) + (3 + 98) + ⋯
Say: pair the first and last — every pair sums to 101
Math: 1+100 = 101, 2+99 = 101, 3+98 = 101 (assert all pairs equal 101)

## Stage 3 — Count the pairs

Show: 50 pairs × 101
Say: a hundred numbers make fifty pairs
Math: pairs = 50

## Stage 4 — The formula

Show: 1 + 2 + ⋯ + n = n(n + 1)/2, then with n = 100: 100·101/2 = 5050
Say: that's the formula — half of n times n plus one
Math: assert n(n+1)/2 == 5050 for n = 100
