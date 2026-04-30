# Subscribe Device
**URL:** `https://api-docs.s18.myenergi.net/operations/subscribeDeviceWebhook`

**Endpoint:** `POST /devices/{id}/webhooks`

**Description:**
Register a URL to receive webhook notifications for device events.

**Path Parameters:**
*   `id` (string, required): Unique ID for the device.

**Request Body (JSON):**
```json
{
  "url": "string"
}
```
*   `url`: The destination URL for webhooks.

**Security:**
*   **Bearer Auth**

**Responses:**
*   **204 No Content:** Subscribed successfully.
