# Nocturne
ultra-fast HTTP/ASGI Web Framework.

Supports asyncio/trio (Powered by AnyIO).

## Feature
> [!IMPORTANT]
> Nocturne implements an early standalone HTTP/1.1, Websocket server, but it is not perfect and should not be used in a production environment.
- Native HTTP Implementation (Non-ASGI/Standalone Mode)
- Fast HTTP Routing 
## Todo
- [ ] Implement HTTP
  - [x] HTTP/1
  - [ ] HTTP/2
  - [ ] HTTP/3 (QUIC)
  - [x] TLS Support
  - [ ] Websocket Support
### About NoctServ
TLS-Ready HTTP server used by Nocturne in standalone mode, allowing easy use of HTTP/1.1 without awareness.
### About RegExpRouter
Created with reference to the `RegExpRouter` of [Hono](https://hono.dev/), an ultra-fast web application framework for JavaScript
## Benchmark
以下の表に、各フレームワークでのベンチマーク結果をまとめました。

| Framework        | Reqs/sec | Avg Latency | Max Latency | Throughput |
|------------------|--------------------------|--------------------------|--------------------------|--------------------------|
| FastAPI          | 3112.71                  | 30.33ms                  | 317.33ms                 | 669.73KB/s               |
| Native ASGI      | 2010.86                  | 48.44ms                  | 500.22ms                 | 429.49KB/s               |
| Quart            | 3542.18                  | 26.74ms                  | 278.96ms                 | 760.31KB/s               |
| Starlette        | 14134.67                 | 6.90ms                   | 16.10ms                  | 2.45MB/s                 |
| Sanic            | 3576.66                  | 26.55ms                  | 30.84ms                  | 786.95KB/s               |
| Nocturne HTTP    | 3182.42                  | 29.75ms                  | 312.40ms                 | 740.26KB/s               |