# List User Devices
**URL:** `https://api-docs.s18.myenergi.net/operations/getDevices`

**Endpoint:** `GET /devices`

**Description:**
This endpoint retrieves a comprehensive list of devices associated with the authenticated user's account. It serves as a starting point for third parties to manage and interact with users' devices through other API endpoints.

**Security:**
*   **Bearer Auth:** API Token required in the header.

**Responses:**
*   **200 OK:** Successful response containing site and device details.

**Response Example:**
```json
{
  "sites": [
    {
      "siteId": "string",
      "name": "string",
      "gridLimit": 0,
      "devices": [
        {
          "deviceId": "string",
          "deviceClass": "string",
          "serialNumber": 0
        }
      ]
    }
  ]
}
```
