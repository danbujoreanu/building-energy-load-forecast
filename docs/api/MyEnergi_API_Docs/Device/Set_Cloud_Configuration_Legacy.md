# Set cloud configuration for device (legacy) [Deprecated]
**URL:** `https://api-docs.s18.myenergi.net/operations/setCloudConfigurationLegacy`

**Endpoint:** `PATCH /devices/{id}/set-cloud-configuration`

**Description:**
Configures cloud features for a Zappi or Libbi device. This endpoint is deprecated but functions similarly to the non-legacy version.

**Path Parameters:**
*   `id` (string, required): Unique ID for the device. Format: first two letters of device class capitalized, followed by the serial number (e.g., 'ZA123456' for a zappi)

**Security:**
*   **Bearer Auth**

**Responses:**
*   **200 OK:** Successful response.
