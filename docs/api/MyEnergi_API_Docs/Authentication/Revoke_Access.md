# Revoke access
**URL:** `https://api-docs.s18.myenergi.net/paths/oauth2-revoke/post`

**Endpoint:** `POST https://auth.s18.myenergi.net/oauth2/revoke`

**Description:**
Revokes the refresh token, unsubscribes the device from webhooks, disables managed mode, and removes all associated user data. Call this during the final stages of your offboarding process.

## Request
### Security
- **Bearer Auth**

## Sample Request (cURL)
```bash
curl --request POST \
  --url https://auth.s18.myenergi.net/oauth2/revoke \
  --header 'Authorization: Bearer 123' \
  --header 'Content-Type: application/json'
```

## Responses
- **200:** Returns an "ok" message.
- **401:** Unauthorized.
- **404:** Not Found.
