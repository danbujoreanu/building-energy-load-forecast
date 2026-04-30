# Set Webhook
**URL:** `https://api-docs.s18.myenergi.net/operations/createWebhook`

**Endpoint:** `POST https://api.s18.myenergi.net/webhooks`

This endpoint allows you to subscribe to global webhook events.

## Request
### Security
- **Basic Auth**

### Body (`application/json`)
- `eventType` (string, required): The type of OpenAPI event to subscribe to.
    - Allowed values: `status_change`, `telemetry`, `command_status`, `command_verification`, `access_revoke`, `preferences_change`
- `endpoint` (string<uri>, required): The URL to send the webhook to.

## Example Request (cURL)
```bash
curl --request POST \
  --url https://api.s18.myenergi.net/webhooks \
  --header 'Accept: application/json' \
  --header 'Authorization: Basic 123' \
  --data '{
    "eventType": "status_change",
    "endpoint": "http://example.com"
  }'
```
