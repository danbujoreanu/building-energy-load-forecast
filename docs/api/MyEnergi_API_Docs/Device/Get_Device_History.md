# Get Device History
**URL:** `https://api-docs.s18.myenergi.net/operations/getHistory`

**Endpoint:** `GET /devices/{id}/history`

**Description:**
Retrieve historical data (energy, power, status) for a specific device.

**Path Parameters:**
*   `id` (string, required): Unique ID for the device (e.g., 'ZA123456').

**Query Parameters:**
*   `from` (string, ISO 8601): Start date/time.
*   `to` (string, ISO 8601): End date/time.
*   `resolution` (string): Data resolution (e.g., "1min", "1h").

**Security:**
*   **Bearer Auth**

**Responses:**
*   **200 OK:** Successful response.
