# Update Webhook
**URL:** `https://api-docs.s18.myenergi.net/operations/updateWebhook`

**Endpoint:** `PUT https://api.s18.myenergi.net/webhooks/{webhookId}`

This endpoint allows you to update the endpoint URL of a webhook.

## Request
### Path Parameters
- `webhookId` (string, required): The ID of the webhook to update.

### Body (`application/json`)
- `endpoint` (string<uri>, required): The new URL to send the webhook to.
