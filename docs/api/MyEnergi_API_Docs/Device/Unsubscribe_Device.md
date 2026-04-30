# Unsubscribe Device
**URL:** `https://api-docs.s18.myenergi.net/operations/deleteDeviceWebhooks`

**Endpoint:** `DELETE /devices/{id}/webhooks`

**Description:**
Stop receiving webhook notifications for a specific device.

**Path Parameters:**
*   `id` (string, required): Unique ID for the device.

**Security:**
*   **Bearer Auth**

**Responses:**
*   **204 No Content:** Unsubscribed successfully.
