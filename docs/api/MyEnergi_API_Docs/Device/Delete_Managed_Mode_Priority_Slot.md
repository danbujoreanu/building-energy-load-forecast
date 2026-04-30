# Delete Managed Mode Priority Slot
**URL:** `https://api-docs.s18.myenergi.net/operations/deleteManagedModePrioritySlot`

**Endpoint:** `DELETE /devices/{id}/managed-mode-priority-slot`

**Description:**
Cancel an active priority slot so the super-schedule resumes immediately.

**Path Parameters:**
*   `id` (string, required): Unique ID for the device.

**Security:**
*   **Bearer Auth**

**Responses:**
*   **200 OK:** Priority slot cancelled.
