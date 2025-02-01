# Notturno
ultra-fast HTTP/ASGI Web Framework.

Supports asyncio/trio (Powered by AnyIO).

## Feature
> [!IMPORTANT]
> Notturno implements an early standalone HTTP/1.1, Websocket server, but it is not perfect and should not be used in a production environment.
- Native HTTP Implementation (Non-ASGI/Standalone Mode)
- Fast HTTP Routing 
- Simple, easy-to-use dependency injection
## Todo
- [ ] Implement HTTP
  - [x] HTTP/1
  - [ ] HTTP/2
  - [ ] HTTP/3 (QUIC)
  - [x] TLS Support
  - [ ] Websocket Support
### About NoctServ
TLS-Ready HTTP server used by Notturno in standalone mode, allowing easy use of HTTP/1.1 without awareness.
### About RegExpRouter
Created with reference to the `RegExpRouter` of [Hono](https://hono.dev/), an ultra-fast web application framework for JavaScript