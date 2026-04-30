# Get Super Schedule
**URL:** `https://api-docs.s18.myenergi.net/operations/getSuperSchedule`

**Endpoint:** `GET /devices/{id}/super-schedule`

**Description:**
Retrieve active time-bounded charging schedules for a Zappi device.

**Requirements:**
*   Device must be a Zappi.
*   Managed mode must be enabled.

**Path Parameters:**
*   `id` (string, required): Unique ID for the Zappi device.

**Security:**
*   **Bearer Auth**

**Responses:**
*   **200 OK:** Successful response.
