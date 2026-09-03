# SAD Client Targets

All clients use one versioned SAD API. They differ only in packaging and device integration.

## Web / PWA
Installable browser client. Same-origin deployment is preferred for Beta. Service worker caches only the application shell; authenticated API responses are never cached.

## Windows
Use a thin wrapper around the web client after the PWA/API contract is stable. Keep endpoint selection configurable so the client can move from cloud to private-server hosting.

## Android + iOS
Use one shared mobile codebase after the PWA path is validated. Required device integrations are secure token storage, explicit microphone permission, file/photo picker, notifications, endpoint switching, and bounded offline lesson/progress cache. Do not place owner credentials, unrestricted memory, or long-lived secrets in ordinary app storage.

## Endpoint profiles
Examples:
- local: `http://127.0.0.1:8765`
- temporary cloud: `https://sad.example.com`
- future private server: `https://sad.home.example`

Remote profiles require HTTPS. Changing profiles must not modify the SAD API contract or earned Forge mastery.
