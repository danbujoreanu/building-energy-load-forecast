# Get Webhook Example Event
**URL:** `https://api-docs.s18.myenergi.net/operations/getWebhookExampleEvent`

**Endpoint:** `GET https://api.s18.myenergi.net/webhooks/example/{eventType}`

This endpoint provides an example event payload for testing purposes.

## Request
### Path Parameters
- `eventType` (string, required): The type of event to preview (e.g., `status_change`).

## Example Response
```json
{
  "status_change": {
    "timestamp": "2019-08-24T14:15:22Z",
    "status": "active",
    "state": "no_vehicle",
    "deviceStatus": "ev_not_connected",
    "faultType": "connector_lock_failure"
  }
}
```
