# ── Build stage ──────────────────────────────────────────────────────────────
FROM maven:3.9.6-eclipse-temurin-21 AS builder
WORKDIR /build
COPY pom.xml .
# Cache dependencies
RUN mvn dependency:go-offline -q
COPY src ./src
RUN mvn package -DskipTests -q

# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM eclipse-temurin:21-jre-jammy
WORKDIR /app

# Create storage directory
RUN mkdir -p /app/storage/videos

COPY --from=builder /build/target/video-service-*.jar app.jar

EXPOSE 8081

ENTRYPOINT ["java", \
  "-Xmx512m", \
  "-XX:+UseContainerSupport", \
  "-jar", "app.jar"]
