# Get Device Status
**URL:** `https://api-docs.s18.myenergi.net/operations/getStatus`

**Endpoint:** `GET /devices/{id}/status`

**Description:**
This endpoint retrieves the latest telemetry data for a specific device, providing a snapshot of its current status, power usage, and performance. 
*   **Note:** The response structure varies by device type (Zappi, Eddi, Harvi, Libbi). The device type is determined by the `id` prefix (e.g., 'ZA' for Zappi).

**Path Parameters:**
*   `id` (string, required): Unique ID for the device.

**Security:**
*   **Bearer Auth**

**Response Example (Zappi):**
```json
{
  "deviceId": "string",
  "deviceClass": "ZA",
  "serialNumber": 0,
  "status": "string",
  "power": 0,
  "voltage": 0,
  "frequency": 0,
  "temperature": 0
}
```
