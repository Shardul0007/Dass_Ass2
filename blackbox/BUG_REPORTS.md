# QuickCart API — Bug Reports

Use one section per bug found.

## Bug <N>: <Short title>

- **Endpoint tested**: `<METHOD> /api/v1/...`
- **Category**: Status code | Validation | JSON schema | Data correctness | Business rule

### Request

- Method: `<METHOD>`
- URL: `<FULL_URL>`
- Headers:
  - `X-Roll-Number: <value>`
  - `X-User-ID: <value>` (if applicable)
  - `Content-Type: application/json` (if applicable)
- Body (JSON):

```json
{
  "example": "..."
}
```

### Expected result (per API doc)

- Status: `<EXPECTED_STATUS>`
- JSON structure: `<expected keys/types>`
- Behavior: `<expected rule>`

### Actual result observed

- Status: `<ACTUAL_STATUS>`
- Body:

```json
{
  "actual": "..."
}
```

### Notes

- Why this is a defect: <short explanation>
- Reproducibility: Always / Sometimes
- Severity: Low / Medium / High
