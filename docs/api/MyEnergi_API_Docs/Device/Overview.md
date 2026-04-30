# myenergi 3rd Party API - Device
v1.0.0

### API Base URL
**Live Server:** `https://api.s18.myenergi.net`

This API allows 3rd parties to integrate their systems with myenergi's intelligent EVSE chargers and home energy appliance tools.
By using this API, energy providers can access and manage devices, monitor usage, and send commands to control charging schedules and load.

## Supported Devices
- Zappi
- Eddi
- Libbi

## Prerequisites
Before you can get started, you will need to register your application and obtain a `client_id` and `client_secret`. These credentials will be used to authenticate your requests.

## Available Device Endpoints

### Status & Control:
- `GET /devices/{id}/status` - Get real-time device status and telemetry
  - **Supported:** Zappi, Eddi, Libbi
- `POST /devices/{id}/mode` - Change device charging mode (Fast, Eco, Eco+)
  - **Supported:** Zappi

### Boost Management:
- `POST /devices/{id}/boost` - Start a boost session
  - **Supported:** Zappi (charging boost), Eddi (boost)
- `DELETE /devices/{id}/boost` - Cancel active boost session
  - **Supported:** Zappi, Eddi

### Cloud Configuration:
- `PATCH /devices/{id}/set-cloud-configuration` - (Deprecated) Configure cloud-level device settings
  - **Supported:** Zappi
- `PATCH /devices/{id}/cloud-configuration` - Configure device-level settings
  - **Supported:** Zappi
- `GET /devices/{id}/cloud-configuration` - Get cloud configuration
  - **Supported:** Zappi

### History:
- `GET /devices/{id}/history` - Get historical data for a device

### Schedule Management:
- `GET /devices/{id}/schedule` - Get the current charging schedule
- `POST /devices/{id}/schedule` - Create or update a charging schedule
- `DELETE /devices/{id}/schedule` - Delete a charging schedule

## Super Scheduler Endpoints (Advanced for Managed Mode capable devices):
- `PUT /devices/{id}/super-schedule` - Configure charging schedule (up to 24 slots)
- `GET /devices/{id}/super-schedule` - Get super schedule
- `DELETE /devices/{id}/super-schedule` - Delete super schedule
- `POST /devices/{id}/managed-mode-priority-slot` - Override schedule with priority slot, immediate charging, or stop charging

## About Managed Mode:
To use Super Scheduler, Managed Mode must be enabled on the Zappi device. When Managed Mode is enabled:
- The device acts as "eco+" mode and locks user controls over the functionality
- The Zappi screen displays "MNGD" to indicate managed mode is active
- Users cannot manually control charging modes via the device interface

⚠️ **Important:**
It is necessary to clearly communicate to users that their devices will be moved to this mode before switching.

## Checking Device Support:
- Call `GET /devices/{id}/cloud-configuration` to check if a device supports Managed Mode
- If the device doesn't support Managed Mode, use the old schedule endpoints instead
