# Get Webhooks
**URL:** `https://api-docs.s18.myenergi.net/operations/getWebhooks`

**Endpoint:** `GET https://api.s18.myenergi.net/webhooks`

This endpoint allows you to retrieve all webhooks that you have previously subscribed to.

## Request
### Security
- **Basic Auth**

## Responses
### 200 Successful response
#### Body (`application/json`)
An array of:
- `webhookId` (string, required): The ID of the webhook.
- `eventType` (string, required): The type of event.
- `endpoint` (string<uri>, required): The destination URL.

## Example Response
```json
[
  {
    "webhookId": "string",
    "eventType": "status_change",
    "endpoint": "http://example.com"
  }
]
```
