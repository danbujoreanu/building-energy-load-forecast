# User information
**URL:** `https://api-docs.s18.myenergi.net/paths/oauth2-userinfo/get`

**Endpoint:** `GET https://auth.s18.myenergi.net/oauth2/userinfo`

**Description:**
Returns user profile information associated with the access token.

## Request
### Security
- **Bearer Auth**

## Sample Request (cURL)
```bash
curl --request GET \
  --url https://auth.s18.myenergi.net/oauth2/userinfo \
  --header 'Accept: application/json' \
  --header 'Authorization: Bearer 123'
```

## Responses
- **200:** User profile information successfully retrieved.
  - **Body (`application/json`):**
    ```json
    {
      "user_id": "string"
    }
    ```
- **401:** Unauthorized.
- **403:** Forbidden.
