# Create Charging Schedule
**URL:** `https://api-docs.s18.myenergi.net/operations/createSchedule`

**Endpoint:** `POST /devices/{id}/schedule`

**Description:**
This endpoint allows 3rd parties to set a charging schedule for a specific device. This capability is crucial for managing energy usage effectively according to the user's needs and preferences.

**Path Parameters:**
*   `id` (string, required): Unique ID for the device. Format: first two letters of device class capitalized, followed by the serial number (e.g., 'ZA123456' for a zappi)

**Request Body (JSON):**
```json
{
  "schedule": [
    {
      "days": [0],
      "startHour": 0,
      "startMinute": 0,
      "duration": 0
    }
  ]
}
```
*   `days`: Array of integers (0-6, where 0 is Sunday).
*   `startHour`: 0-23.
*   `startMinute`: 0-59.
*   `duration`: Duration in minutes.

**Security:**
*   **Bearer Auth**

**Responses:**
*   **201 Created:** Schedule created successfully.
