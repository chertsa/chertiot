# Caddy with layer4 (MQTTS TLS termination, D8). Pinned versions come from .env via build args.
ARG CADDY_VERSION=2.11.4
FROM caddy:${CADDY_VERSION}-builder AS builder
ARG CADDY_L4_VERSION=42db5690dea1
ENV GOFLAGS=-p=1
RUN xcaddy build --with github.com/mholt/caddy-l4@${CADDY_L4_VERSION}
FROM caddy:${CADDY_VERSION}
COPY --from=builder /usr/bin/caddy /usr/bin/caddy
