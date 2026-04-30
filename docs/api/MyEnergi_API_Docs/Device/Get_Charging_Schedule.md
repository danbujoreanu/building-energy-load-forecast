# Get Charging Schedule
**URL:** `https://api-docs.s18.myenergi.net/operations/getSchedule`

**Endpoint:** `GET /devices/{id}/schedule`

**Description:**
This endpoint allows 3rd parties to retrieve the charging schedule set for a specific device, providing insights into their planned charging periods and energy usage.
This information can be useful for monitoring and adjusting the schedule to optimize energy consumption and costs.

**Path Parameters:**
*   `id` (string, required): Unique ID for the device. Format: first two letters of device class capitalized, followed by the serial number (e.g., 'ZA123456' for a zappi)

**Security:**
*   **Bearer Auth**

**Responses:**
*   **200 OK:** Successful response containing site and device details.

**Response Example:**
```json
{
  "schedule": [
    null
  ]
}
```
