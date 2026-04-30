# Cancel Boost
**URL:** `https://api-docs.s18.myenergi.net/operations/sendCancelBoost`

**Endpoint:** `DELETE /devices/{id}/boost`

**Description:**
Sends a cancel boost command to stop the ongoing charging/boosting process initiated by a previous boost command. Useful for terminating sessions when energy requirements change.
*   **Note:** Works for both Zappi and Eddi devices.

**Path Parameters:**
*   `id` (string, required): Unique ID for the device.

**Security:**
*   **Bearer Auth**

**Responses:**
*   **204 No Content:** Boost cancelled successfully.
