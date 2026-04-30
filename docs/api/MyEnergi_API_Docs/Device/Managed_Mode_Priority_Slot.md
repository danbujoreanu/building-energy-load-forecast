# Managed Mode Priority Slot
**URL:** `https://api-docs.s18.myenergi.net/operations/managedModePrioritySlot`

**Endpoint:** `POST /devices/{id}/managed-mode-priority-slot`

**Description:**
Override the super-schedule with an immediate charging command (e.g., start fast charge).
*   **Behavior:** Stays active until the vehicle is unplugged or manually cleared.

**Path Parameters:**
*   `id` (string, required): Unique ID for the device.

**Request Body (JSON):**
```json
{
  "mode": "string",
  "chargeRateWatts": 0,
  "chargeRateAmps": 0,
  "minChargeWatts": 0,
  "minChargeAmps": 0,
  "operate3ph": true
}
```

**Security:**
*   **Bearer Auth**

**Responses:**
*   **200 OK:** Priority slot set successfully.
