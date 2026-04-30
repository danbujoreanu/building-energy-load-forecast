# Authorize
**URL:** `https://api-docs.s18.myenergi.net/paths/oauth2-authorize/get`

**Endpoint:** `GET https://auth.s18.myenergi.net/oauth2/authorize`

**Description:**
Initiates the OAuth 2.0 authorization flow. Redirects the user to a myenergi login page, where they can authorize your app by logging in.

After a successful login, the user will be redirected to the `redirect_uri` you've provided with a `code` query parameter, which can be exchanged for an access token using the `/oauth2/token` endpoint.

## Request
### Query Parameters
| Parameter | Type | Description |
| :--- | :--- | :--- |
| `state` | string | The state parameter is optional. It will be returned to you after the authorization flow as a query parameter. |
| `client_id` | string (required) | Your application's client ID. |
| `redirect_uri` | string (required) | The URL to redirect back to after authorization. |
| `response_type` | enum (required) | Must be `code`. |

## Sample Request (cURL)
```bash
curl --request GET \
  --url 'https://auth.s18.myenergi.net/oauth2/authorize?response_type=code'
```
