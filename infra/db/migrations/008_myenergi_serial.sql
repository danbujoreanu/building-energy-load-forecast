-- Migration 008: Add myenergi_serial to households
-- Problem: households.hardware_id stores the MPRN (electricity meter reference number,
--          e.g. '10306822417'), but myenergi_readings.hub_serial stores the MyEnergi
--          hub serial (e.g. '21509692'). These are two separate physical devices.
--          The Free Saturday panels (DAN-132) JOIN on hardware_id = hub_serial,
--          which never matches, causing all Free Saturday panels to show 0 / no data.
-- Fix:    Add a dedicated myenergi_serial column. Free Saturday queries JOIN on this.
-- Applied: 2026-05-07

ALTER TABLE households ADD COLUMN IF NOT EXISTS myenergi_serial TEXT;

-- Populate for the single household (MPRN 10306822417, MyEnergi hub 21509692)
UPDATE households
SET myenergi_serial = '21509692'
WHERE hardware_id = '10306822417';

-- Verify
SELECT id, hardware_id, myenergi_serial, has_eddi FROM households;
