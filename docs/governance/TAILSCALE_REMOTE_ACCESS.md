# Tailscale Remote Access
*Secure remote access to NUC services from anywhere*
*Set up: 2026-05-10 | Account: dan.bujoreanu@gmail.com*

---

## What Tailscale Does

Tailscale creates a private encrypted network (WireGuard-based) between your devices.
Every device gets a stable private IP (`100.x.x.x`) and a DNS hostname (`device.tailXXXX.ts.net`).
Traffic is peer-to-peer and end-to-end encrypted — Tailscale's servers only broker the connection, they never see your data.

**Is it secure?** Yes. WireGuard encryption, no ports exposed to the internet, only devices in your tailnet (account) can connect. Safer than VPN, simpler than SSH tunnels.

---

## Devices in the Tailnet

| Device | Tailscale IP | Tailscale hostname | Always on? |
|--------|-------------|-------------------|-----------|
| Intel NUC (192.168.68.119) | `100.79.58.122` | `intelnuc.tailc0b176.ts.net` | ✅ Yes |
| MacBook Pro (192.168.68.118) | `100.99.162.48` | `dans-macbook-pro.tailc0b176.ts.net` | When awake |
| iPhone 14 | `100.125.155.87` | `iphone-14.tailc0b176.ts.net` | When app active |

---

## All Services: Home WiFi vs Tailscale

| Service | Home WiFi | Via Tailscale (anywhere) | Always on? |
|---------|-----------|--------------------------|-----------|
| **🌿 Gardening Streamlit** | `192.168.68.119:8501` | http://intelnuc.tailc0b176.ts.net:8501 | ✅ NUC |
| **⚡ Sparc Energy Intel Chat** | `192.168.68.119:8502` | http://intelnuc.tailc0b176.ts.net:8502 | ✅ NUC |
| **⚡ Sparc Grafana** | `192.168.68.119:3001` | http://intelnuc.tailc0b176.ts.net:3001 | ✅ NUC |
| **🌱 Gardening Grafana** | `192.168.68.119:3000` | http://intelnuc.tailc0b176.ts.net:3000 | ✅ NUC |
| **🔧 n8n Automation** | `192.168.68.119:5678` | http://intelnuc.tailc0b176.ts.net:5678 | ✅ NUC |
| **📊 Portainer** | `192.168.68.119:9000` | http://intelnuc.tailc0b176.ts.net:9000 | ✅ NUC |
| **🔌 Sparc API** | `192.168.68.119:8000` | http://intelnuc.tailc0b176.ts.net:8000 | ✅ NUC |

**Bookmark these two (work from anywhere, even on 4G):**
- 🌿 Gardening: http://intelnuc.tailc0b176.ts.net:8501
- ⚡ Sparc Intel: http://intelnuc.tailc0b176.ts.net:8502

*"Not secure" browser warning on these URLs is normal — HTTP inside Tailscale is encrypted at the WireGuard layer.*

---

## Setup Record

### NUC (installed 2026-05-10)
```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --authkey=tskey-auth-...
sudo systemctl enable tailscaled
```

### Mac
```bash
brew install tailscale
tailscale up
```

### iPhone
App Store → "Tailscale" → sign in with Google account → toggle on

---

## Auth Key Notes

- Keys live at: https://login.tailscale.com/admin/settings/keys
- Settings used: **Ephemeral OFF**, **Tags OFF**
- Key prefix: `tskey-auth-kYohXJaNZi11CNTRL-...` (full key stored in NUC `~/sparc/.env`)
- Expiry: 90 days from 2026-05-10 → expires **2026-08-08**
- After key expires: NUC stays in tailnet permanently. Key only needed to add NEW devices.
- To add a new device later: generate a new key at the link above

---

## Tailscale Admin Console

https://login.tailscale.com/admin/machines — see all devices, their IPs, online status

---

## Troubleshooting

**"Device not reachable on Tailscale"**
```bash
# On NUC:
sudo systemctl status tailscaled
sudo tailscale status
# Should show: NUC IP, Mac IP, iPhone IP all listed
```

**"NUC dropped off Tailscale after reboot"**
```bash
ssh dan@192.168.68.119 "sudo systemctl enable tailscaled && sudo tailscale up"
```

**"Connection slow over Tailscale"**
- Usually means relay routing (DERP server) instead of direct. Check: `tailscale ping nuc`
- Direct connection works when both devices are on standard NAT. DERP is fallback — still encrypted, just ~20ms slower.

---

*See also: NUC_SERVICES_DIRECTORY.md (full services list)*
