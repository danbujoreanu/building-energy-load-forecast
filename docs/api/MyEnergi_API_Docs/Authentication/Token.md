# Token
**URL:** `https://api-docs.s18.myenergi.net/paths/oauth2-token/post`

**Endpoint:** `POST https://auth.s18.myenergi.net/oauth2/token`

**Description:**
Exchanges the authorization code for an access token or the refresh token for an access token.

## Request
### Body (`application/x-www-form-urlencoded`)
| Parameter | Type | Description |
| :--- | :--- | :--- |
| `client_id` | string (required) | The `client_id` received during registration. |
| `client_secret` | string (required) | The `client_secret` received during registration. |
| `grant_type` | string (required) | Allowed values: `authorization_code`, `refresh_token`. |
| `redirect_uri` | string | Required if `grant_type` is `authorization_code`. |
| `code` | string | Required if `grant_type` is `authorization_code`. |
| `refresh_token` | string | Required if `grant_type` is `refresh_token`. |

## Sample Request (cURL)
```bash
curl --request POST \
  --url https://auth.s18.myenergi.net/oauth2/token \
  --header 'Accept: application/json' \
  --header 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode client_id= \
  --data-urlencode client_secret= \
  --data-urlencode grant_type=authorization_code \
  --data-urlencode redirect_uri=
```
