# Set cloud configuration for device
**URL:** `https://api-docs.s18.myenergi.net/operations/setCloudConfiguration`

**Endpoint:** `PATCH /devices/{id}/cloud-configuration`

**Description:**
Configures cloud features for a Zappi or Libbi device, including managed mode and auto scheduler.

**Request body:**
- `autoSchedulerEnabled`: Enables or disables the cloud-based auto scheduler feature (supported on Zappi and Libbi)
- `managedModeEnabled`: Enables or disables managed mode for cloud control (Zappi only — rejected with 400 for Libbi)

**Path Parameters:**
*   `id` (string, required): Unique ID for the device. Format: first two letters of device class capitalized, followed by the serial number (e.g., 'ZA123456' for a zappi)

**Security:**
*   **Bearer Auth**

**Responses:**
*   **200 OK:** Successful response.
