# Delete Charging Schedule
**URL:** `https://api-docs.s18.myenergi.net/operations/deleteSchedule`

**Endpoint:** `DELETE /devices/{id}/schedule`

**Description:**
This endpoint allows 3rd parties to delete a charging schedule set for a specific device, allowing them to modify or remove their energy management plans as needed.

**Path Parameters:**
*   `id` (string, required): Unique ID for the device. Format: first two letters of device class capitalized, followed by the serial number (e.g., 'ZA123456' for a zappi)

**Security:**
*   **Bearer Auth**

**Responses:**
*   **200 OK:** Schedule deleted successfully.
