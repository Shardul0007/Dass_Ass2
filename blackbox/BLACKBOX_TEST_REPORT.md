# QuickCart Black-Box API Testing Report

Date: 2026-03-21

This report documents the **black-box** test design and automated execution for the QuickCart REST API.

Black-box means:
- Tests are derived from **API documentation and observed behavior only**.
- The internal implementation is treated as unknown.

## How to run

- Start server (per provided doc): `docker run -p 8080:8080 quickcart`
- Run tests from repo root (`Dass_Ass2/`): `python -m pytest blackbox/tests -q`

Environment variables supported:
- `QUICKCART_BASE_URL` (default `http://localhost:8080`)
- `QUICKCART_ROLL_NUMBER` (default `1`)

## Test case design (inputs, expected outputs, justification)

Below, each test case lists **input**, **expected output**, and **why it matters**.

### A) Global header rules

**BB-HDR-01 Missing `X-Roll-Number`**
- Input: `GET /api/v1/admin/users` without `X-Roll-Number`
- Expected: `401`
- Justification: validates the global authentication/guard rule.

**BB-HDR-02 Non-integer `X-Roll-Number`**
- Input: `GET /api/v1/admin/users` with `X-Roll-Number: abc`
- Expected: `400`
- Justification: verifies server correctly rejects wrong types.

**BB-HDR-03 Missing `X-User-ID` on user endpoint**
- Input: `GET /api/v1/profile` without `X-User-ID`
- Expected: `400`
- Justification: ensures user-scoped endpoints enforce user identity.

**BB-HDR-04 Invalid `X-User-ID`**
- Input: `GET /api/v1/profile` with `X-User-ID: -1`
- Expected: `400`
- Justification: validates positive-integer requirement.

### B) Profile

**BB-PRO-01 Get profile**
- Input: `GET /api/v1/profile` with valid headers
- Expected: `200` and JSON object
- Justification: baseline contract check for user profile retrieval.

**BB-PRO-02 Update profile (invalid name bounds)**
- Input: `PUT /api/v1/profile` with `name` length `< 2` or `> 50`
- Expected: `400`
- Justification: boundary-value validation for name.

**BB-PRO-03 Update profile (invalid phone)**
- Input: `PUT /api/v1/profile` with phone not exactly 10 digits
- Expected: `400`
- Justification: wrong length / wrong data constraints.

**BB-PRO-04 Update profile (valid boundary)**
- Input: `PUT /api/v1/profile` with name length `2` and phone `10 digits`
- Expected: `200/201` and JSON
- Justification: confirms the lower valid boundary is accepted.

### C) Addresses

**BB-ADDR-01 Get addresses**
- Input: `GET /api/v1/addresses`
- Expected: `200` and JSON list/object
- Justification: baseline retrieval.

**BB-ADDR-02 Add address invalid label/pincode/street/city**
- Input: `POST /api/v1/addresses` with invalid label, street < 5, city < 2, pincode != 6 digits
- Expected: `400`
- Justification: invalid inputs + boundary checks.

**BB-ADDR-03 Add address success returns full object**
- Input: `POST /api/v1/addresses` with valid fields
- Expected: `200/201` and JSON containing `address_id`, `label`, `street`, `city`, `pincode`, `is_default`
- Justification: validates create contract and required response structure.

**BB-ADDR-04 Default uniqueness**
- Input: create 2 addresses with `is_default=true`, then `GET /api/v1/addresses`
- Expected: at most 1 address marked default
- Justification: validates business rule “only one default address”.

**BB-ADDR-05 Update address only street/is_default**
- Input: `PUT /api/v1/addresses/{id}` attempting to change city
- Expected: request rejected (400) or accepted but city unchanged; street updates
- Justification: validates restricted update rules.

**BB-ADDR-06 Delete non-existent address**
- Input: `DELETE /api/v1/addresses/99999999`
- Expected: `404`
- Justification: validates correct error code for missing resource.

### D) Products

**BB-PROD-01 Product list excludes inactive**
- Input: `GET /api/v1/products`
- Expected: response contains only active products
- Justification: confirms filtering rule “inactive never shown”.

**BB-PROD-02 Product lookup not found**
- Input: `GET /api/v1/products/99999999`
- Expected: `404`
- Justification: correct missing-resource behavior.

**BB-PROD-03 Filter/search/sort (best-effort due to ambiguous query params)**
- Input: `GET /api/v1/products?category=...`, `?search=...` or `?q=...`, `?sort=price&order=asc`
- Expected: `200` and behavior matches filter/search/sort; if API rejects unknown params, `400`
- Justification: the doc states these capabilities exist; this validates the decision paths when supported.

### E) Cart

**BB-CART-01 Add with quantity <= 0**
- Input: `POST /api/v1/cart/add` with `quantity=0`
- Expected: `400`
- Justification: invalid quantity boundary.

**BB-CART-02 Add unknown product**
- Input: `POST /api/v1/cart/add` with non-existent product
- Expected: `404`
- Justification: validates product existence checks.

**BB-CART-03 Add same product twice increments quantity**
- Input: add product quantity 1, add again quantity 2
- Expected: final cart line quantity = 3
- Justification: validates rule “quantities add, not replace”.

**BB-CART-04 Cart totals and subtotals**
- Input: `GET /api/v1/cart` after adds
- Expected: `subtotal == qty * unit_price` and `total == sum(subtotals)`
- Justification: validates correct computed totals and “last item counted” rule.

**BB-CART-05 Update quantity invalid and valid**
- Input: `POST /api/v1/cart/update` with quantity 0 (invalid) then quantity 1 (valid)
- Expected: invalid => 400; valid => 200/201
- Justification: quantity rules apply to update as well.

**BB-CART-06 Remove missing item**
- Input: `POST /api/v1/cart/remove` twice
- Expected: second remove => 404
- Justification: validates correct error code when item not present.

**BB-CART-07 Add quantity > stock**
- Input: add with `quantity=stock+1`
- Expected: `400`
- Justification: validates stock guard.

### F) Checkout + Orders + Invoice

**BB-CHK-01 Checkout empty cart**
- Input: `POST /api/v1/checkout` with empty cart
- Expected: `400`
- Justification: prevents invalid order creation.

**BB-CHK-02 Checkout invalid payment method**
- Input: `payment_method=BITCOIN`
- Expected: `400`
- Justification: validates allowed enum: COD/WALLET/CARD only.

**BB-CHK-03 COD not allowed above 5000**
- Input: cart total > 5000 + `payment_method=COD`
- Expected: `400`
- Justification: boundary rule tied to business constraints.

**BB-CHK-04 CARD checkout success**
- Input: `payment_method=CARD` with non-empty cart
- Expected: `200/201` and JSON
- Justification: validates a known-success checkout path.

**BB-ORD-01 Orders list**
- Input: `GET /api/v1/orders`
- Expected: `200` and list
- Justification: baseline order retrieval.

**BB-INV-01 Invoice contains subtotal/gst/total**
- Input: `GET /api/v1/orders/{id}/invoice`
- Expected: fields present
- Justification: validates invoice structure and pricing transparency.

**BB-CAN-01 Cancel non-existent order**
- Input: `POST /api/v1/orders/99999999/cancel`
- Expected: `404`
- Justification: missing resource error code.

**BB-CAN-02 Cancel delivered order rejected**
- Input: attempt to cancel delivered order
- Expected: `400`
- Justification: validates the “delivered cannot be cancelled” rule.

### G) Wallet

**BB-WAL-01 Wallet add amount boundary**
- Input: `POST /api/v1/wallet/add` with 0 and 100001
- Expected: `400`
- Justification: boundary values.

**BB-WAL-02 Wallet pay invalid and insufficient**
- Input: `POST /api/v1/wallet/pay` with 0 and a huge value
- Expected: `400`
- Justification: invalid amount + insufficient funds rule.

**BB-WAL-03 Wallet pay exact deduction (if balance exposed)**
- Input: add 1 then pay 1
- Expected: balance decreases by exactly 1
- Justification: verifies no extra deductions.

### H) Loyalty

**BB-LOY-01 Redeem invalid and too many**
- Input: redeem 0, redeem huge
- Expected: `400`
- Justification: invalid amount + insufficient points.

### I) Reviews

**BB-REV-01 Rating bounds**
- Input: rating 0 and 6
- Expected: `400`
- Justification: boundary validation.

**BB-REV-02 Comment length bounds**
- Input: empty comment and 201 chars
- Expected: `400`
- Justification: boundary validation.

**BB-REV-03 Average rating decimal (best effort)**
- Input: add two ratings 4 and 5, then GET reviews
- Expected: average rating should be computed as decimal (not floored)
- Justification: validates numeric correctness.

### J) Support tickets

**BB-TKT-01 Create ticket subject/message bounds**
- Input: subject length < 5 and message length > 500
- Expected: `400`
- Justification: boundary validation.

**BB-TKT-02 Ticket status monotonic progression**
- Input: OPEN -> IN_PROGRESS -> CLOSED, then attempt CLOSED -> OPEN
- Expected: last transition rejected with `400`
- Justification: validates state machine constraints.

### K) Coupons

**BB-CPN-01 Apply coupon with missing code**
- Input: `POST /api/v1/coupon/apply` with `{}`
- Expected: `400`
- Justification: missing field validation.

**BB-CPN-02 Apply coupon (database-dependent)**
- Input: `POST /api/v1/coupon/apply` using a code discovered via `GET /api/v1/admin/coupons`
- Expected: `200/201` on success OR `400` if coupon is expired / min-cart not met / cap rules fail
- Justification: exercises coupon validation rules stated in the doc.

**BB-CPN-03 Remove coupon**
- Input: `POST /api/v1/coupon/remove`
- Expected: `200/201` (or a documented `400` if API requires a coupon to be applied first)
- Justification: validates coupon removal behavior and response structure.

## Automated verification checklist

All automated tests verify:
- Correct HTTP status codes
- JSON response structure (at least: parseable JSON, expected container types)
- Returned data correctness where the specification provides a determinable rule (e.g., cart totals)

## Bug reports

If any test fails against the documented behavior, record it in `blackbox/BUG_REPORTS.md` using the template.
