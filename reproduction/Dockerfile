FROM eclipse-temurin:11-jdk-jammy@sha256:b4330742dc3e03d393e8449d84b7229100a1277bda9dfac9fa7277702609f4a3
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    maven build-essential git curl ca-certificates python3 python3-venv \
    postgresql-client fontconfig fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*
RUN python3 -m venv /opt/plot-env && /opt/plot-env/bin/pip install --no-cache-dir \
    numpy==1.26.4 pandas==2.2.3 matplotlib==3.9.2 seaborn==0.13.2 \
    jupyter==1.1.1 nbconvert==7.16.4
RUN mkdir -p /opt/sbt && curl -fL --retry 3 \
    https://repo.maven.apache.org/maven2/org/scala-sbt/sbt-launch/1.10.7/sbt-launch-1.10.7.jar \
    -o /opt/sbt/sbt-launch.jar
ENV PATH="/opt/plot-env/bin:${PATH}"
ENV JAVA_TOOL_OPTIONS="-XX:ActiveProcessorCount=2 -Xmx3g -Djava.awt.headless=true"
WORKDIR /workspace
