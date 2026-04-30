# Change Device Supply Mode
**URL:** `https://api-docs.s18.myenergi.net/operations/changeDeviceSupplyMode`

**Endpoint:** `POST /devices/{id}/mode`

**Description:**
Allows users to change the energy supply mode for a specific device to optimize energy usage based on needs or cost-saving strategies.

**Path Parameters:**
*   `id` (string, required): Unique ID for the device.

**Request Body (JSON):**
*   `supplyMode` (string, required): The target energy mode.
    *   Allowed values: `eco`, `eco+`, `fast`, `off`.

**Security:**
*   **Bearer Auth**

**Responses:**
*   **204 No Content:** Mode changed successfully.
