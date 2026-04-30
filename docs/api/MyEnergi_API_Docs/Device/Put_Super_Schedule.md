# Put Super Schedule
**URL:** `https://api-docs.s18.myenergi.net/operations/putSuperSchedule`

**Endpoint:** `PUT /devices/{id}/super-schedule`

**Description:**
Configure up to 24 time-based charging slots for a Zappi in managed mode.

**Important Note:** 
*   Flash-write limit: Only 24 slot writes are allowed per rolling 60-minute window.
*   Managed mode must be enabled on the device.

**Path Parameters:**
*   `id` (string, required): Unique ID for the Zappi device.

**Request Body (JSON):**
```json
{
  "chargeSchedules": [
    {
      "startTime": "string",
      "endTime": "string",
      "mode": "string",
      "chargeRateWatts": 0,
      "chargeRateAmps": 0,
      "minChargeWatts": 0,
      "minChargeAmps": 0,
      "priority": 0,
      "operate3ph": true,
      "recurring": true
    }
  ]
}
```

**Security:**
*   **Bearer Auth**

**Responses:**
*   **200 OK:** Super schedule updated successfully.
