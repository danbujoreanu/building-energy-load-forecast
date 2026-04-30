# myenergi 3rd Party API - Authentication

## Prerequisites
Before you can get started, you will need to register your application and obtain a `client_id` and `client_secret`. As of now this is a manual process, please contact support.

## Authentication Flow
The OAuth 2.0 flow consists of the following steps:
1.  From the front-end part of your app you call the `/oauth2/authorize` endpoint, which redirects the user to a myenergi login page.
2.  The user authorizes your app by logging in.
3.  On a successful login the user is redirected back to your app with an authorization code.
4.  You exchange the authorization code for an access token and refresh token using the `/oauth2/token` endpoint.
5.  You store the access token and refresh token in a persistent storage.
6.  You use the access token to call the other endpoints of the API.

## Token Expiration and Refreshing
Access tokens have an expiration time of **1 day**. After the access token has expired, you can use the `/oauth2/token` endpoint to refresh it using the **refresh token**. Refresh tokens have an expiration time of **a year**.
The `/oauth2/token` response includes a `refresh_token_expires_in` field, showing the remaining time in seconds until the refresh token expires, which can be used to track refresh token validity.
