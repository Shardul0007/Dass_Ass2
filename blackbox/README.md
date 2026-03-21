# Black Box API Testing — QuickCart (pytest + requests)

## Prerequisites

1) Load and run the provided Docker image (as per the doc):

- `docker load -i quickcart_image.tar`
- `docker run -p 8080:8080 quickcart`

2) Python deps (in your venv):

- `pip install pytest requests`

## How tests authenticate

Every request must include:

- `X-Roll-Number`: an integer
- `X-User-ID`: a positive integer that exists (for non-admin endpoints)

The test suite uses admin endpoints (which only require `X-Roll-Number`) to discover a valid user id and sample product/coupon ids at runtime.

## Running the black-box tests

From `Dass_Ass2/`:

- `python -m pytest blackbox/tests -q`

## Configuration (optional)

By default tests assume `http://localhost:8080`.

You can override with environment variables:

- `QUICKCART_BASE_URL` (default: `http://localhost:8080`)
- `QUICKCART_ROLL_NUMBER` (default: `1`)

Example:

- PowerShell: `$env:QUICKCART_BASE_URL = "http://localhost:8080"`
