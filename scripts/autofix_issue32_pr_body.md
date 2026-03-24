Fixes #32

This PR fixes promo code validation so that only explicitly known promo codes are accepted.

Changes:
- Remove digit-suffix regex bypass.
- Normalize promo code input with strip+upper.
- Reject unknown codes (no implicit 100% discount fallback).
- Add regression tests for valid/invalid promo codes.
