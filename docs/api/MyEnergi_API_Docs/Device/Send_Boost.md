# Send Boost
**URL:** `https://api-docs.s18.myenergi.net/operations/sendBoost`

**Endpoint:** `POST /devices/{id}/boost`

**Description:**
Sends a charge or boost command to the specified device. Required parameters vary by device type.

**Path Parameters:**
*   `id` (string, required): Unique ID for the device.

**Request Body (JSON - Zappi Example):**
```json
{
  "mode": "normal",
  "parameters": {
    "energy": 10,
    "targetTime": "2026-04-30T22:00:00Z"
  },
  "durationMinutes": 60
}
```
*   `mode`: `normal` or `smart`.
*   `energy`: Amount of energy in kWh (1-99).
*   `targetTime`: Required only for `smart` mode (ISO-8601).

**Security:**
*   **Bearer Auth**

**Responses:**
*   **204 No Content:** Boost command sent successfully.
