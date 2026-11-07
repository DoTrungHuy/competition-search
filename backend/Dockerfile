FROM maven:3.9-eclipse-temurin-21 AS build

ARG MAVEN_MIRROR_URL=""

WORKDIR /build

RUN if [ -n "$MAVEN_MIRROR_URL" ]; then \
      mkdir -p /root/.m2 && \
      printf '<settings><mirrors><mirror><id>mirror</id><mirrorOf>central</mirrorOf><url>%s</url></mirror></mirrors></settings>\n' "$MAVEN_MIRROR_URL" > /root/.m2/settings.xml; \
    fi

COPY pom.xml .
RUN mvn -q -DskipTests dependency:go-offline

COPY src ./src
RUN mvn -q -DskipTests package

FROM eclipse-temurin:21-jre

WORKDIR /app

RUN (command -v curl >/dev/null || (apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*)) \
    && useradd --system --uid 10001 --create-home appuser

COPY --from=build /build/target/competition-backend-*.jar /app/app.jar

USER 10001

EXPOSE 8080

ENTRYPOINT ["java", "-jar", "/app/app.jar"]
