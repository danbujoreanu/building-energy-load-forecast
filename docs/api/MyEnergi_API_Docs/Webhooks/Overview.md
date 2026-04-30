# myenergi 3rd Party API - Webhooks

## Prerequisites
Before you can get started, you will need to register your application and obtain a `client_id` and `client_secret`. Please contact myenergi to get these credentials.

## Getting Started
To start receiving webhooks, you need to create a webhook endpoint in your application. Once you have an endpoint, you can use the `Set Webhook` endpoint to register it with myenergi.

You can also subscribe to device-specific webhooks by using the `POST /devices/{id}/webhooks` endpoint—this can happen at any time, but usually after you've obtained a user-level access token.

## Events
Supported event types:
- `status_change` - Triggers when a device state has changed.
- `telemetry` - Triggers whenever there is a data update from the device.
- `command_status` - Triggers when a command's status has changed.
- `access_revoke` - Triggers when a user has revoked their access.
- `preferences_change` - Triggers when a user changes preferences in the customer app.

## Delivery and Retries
Your endpoint should respond with `200 OK` in less than a second. If the webhook doesn't respond with a `200 OK`, it will be retried up to **5 times** over **12 hours** with an exponential backoff.

## Security
Requests to your endpoint will include a `X-Myenergi-Signature` header confirming the request is from myenergi. You can verify the signature by calculating the `HMAC SHA1` of the request body using your `client_secret` and comparing it to the value of the `X-Myenergi-Signature` header.

**Node.js Example:**
```javascript
const myenergiSignature = Buffer.from(req.headers['X-Myenergi-Signature'], 'utf8');
const hmac = createHmac('sha1', your_client_secret);
const signature = Buffer.from(
  'sha1=' + hmac.update(JSON.stringify(body)).digest('hex'),
  'utf8'
).toString("utf8");

if (!crypto.timingSafeEqual(signature, myenergiSignature)) {
  throw new Error("Signature invalid");
}
```
