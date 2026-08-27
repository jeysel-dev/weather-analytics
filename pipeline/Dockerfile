FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    requests==2.33.0 \
    google-cloud-bigquery==3.27.0 \
    dbt-bigquery==1.7.8 \
    db-dtypes==1.3.1 \
    pyarrow==23.0.1

WORKDIR /app

# Copia o pipeline e o projeto dbt
COPY pipeline/ /app/pipeline/
COPY dbt/      /app/dbt/

# Usa o profiles.yml.example como profiles.yml do container.
# Valores sensíveis são injetados em runtime via variáveis de ambiente.
RUN cp /app/pipeline/dbt_profiles.yml.example /app/pipeline/profiles.yml

CMD ["bash", "/app/pipeline/run_pipeline.sh"]
