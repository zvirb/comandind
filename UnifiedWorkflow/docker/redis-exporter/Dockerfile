# The official redis_exporter image is built from scratch and does not contain
# any shell or utilities like curl, which are needed for the health check.
# This Dockerfile uses a multi-stage build to create a new image based on
# Alpine, which includes curl, and then copies the exporter binary into it.

FROM oliver006/redis_exporter:v1.59.0 AS source

FROM alpine:latest

RUN apk --no-cache add curl su-exec
COPY --from=source /redis_exporter /redis_exporter

CMD ["/redis_exporter"]