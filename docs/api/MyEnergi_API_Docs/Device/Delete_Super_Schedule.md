# Delete Super Schedule
**URL:** `https://api-docs.s18.myenergi.net/operations/deleteSuperSchedule`

**Endpoint:** `DELETE /devices/{id}/super-schedule`

**Description:**
Clear all time-bounded charging schedules on a Zappi device.

**Path Parameters:**
*   `id` (string, required): Unique ID for the Zappi device.

**Security:**
*   **Bearer Auth**

**Responses:**
*   **200 OK:** All schedules cleared.
