# Frontend Interactive Canvas

This service provides an embeddable HTML5/JS web canvas designed to integrate with agent interfaces and Gemini Enterprise.

## Embedding Constraints
- **Iframe Embedding**: `nginx.conf` omits `X-Frame-Options` and configures `Content-Security-Policy: frame-ancestors` to allow embedding inside authorized host containers.
- **Bi-directional Protocol**: Communicates via window `postMessage` (`CANVAS_ACTION` and `AGENT_UPDATE` event types).

## Local Development
```bash
docker build -t frontend-canvas .
docker run -p 8080:8080 frontend-canvas
```
