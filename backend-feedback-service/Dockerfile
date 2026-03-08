# ── Build stage ──────────────────────────────────────────────────────────────
FROM maven:3.9.6-eclipse-temurin-21 AS builder
WORKDIR /build
COPY pom.xml .
RUN mvn dependency:go-offline -q
COPY src ./src
RUN mvn package -DskipTests -q

# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM eclipse-temurin:21-jre-jammy
WORKDIR /app
COPY --from=builder /build/target/feedback-service-*.jar app.jar

EXPOSE 8082

ENTRYPOINT ["java", \
  "-Xmx384m", \
  "-XX:+UseContainerSupport", \
  "-jar", "app.jar"]
