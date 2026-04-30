# Get Cloud Configuration
**URL:** `https://api-docs.s18.myenergi.net/operations/getCloudConfiguration`

**Endpoint:** `GET /devices/{id}/cloud-configuration`

**Description:**
Retrieves the cloud configuration status for a Zappi or Libbi device, including managed mode capabilities and auto scheduler status.

**Response fields:**
- `managedModeSupported`: Indicates if the device supports managed mode (always `false` for Libbi)
- `managedModeEnabled`: Indicates if managed mode is currently enabled on the device (always `false` for Libbi)
- `autoSchedulerEnabled`: Indicates if the cloud-based auto scheduler feature is enabled

**Path Parameters:**
*   `id` (string, required): Unique ID for the device. Format: first two letters of device class capitalized, followed by the serial number (e.g., 'ZA123456' for a zappi)

**Security:**
*   **Bearer Auth**

**Responses:**
*   **200 OK:** Successful response.
