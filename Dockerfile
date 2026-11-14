FROM golang:1.25-bookworm AS build

WORKDIR /src

COPY go.mod go.sum ./
RUN go mod download

COPY . .

RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o /out/myrag ./cmd/myrag

FROM debian:bookworm-slim

WORKDIR /app

COPY --from=build /out/myrag /app/myrag
COPY internal/web/templates /app/internal/web/templates

EXPOSE 8080 8081

ENTRYPOINT ["/app/myrag"]
CMD ["app"]
