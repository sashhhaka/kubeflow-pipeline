PIPELINE_PATH = "pipeline.yaml"
PIPELINE_NAME = "mlops-example-pipeline"

SECRETS_APPROLE = "vault-approle-mlops-template"

SECRETS = {
    "role_id": "VAULT_ROLE_ID",
    "secret_id": "VAULT_SECRET_ID"
}

ENV_VARS = {
    "S3_BUCKET": "p-dp-mlops",
    "S3_ENDPOINT": "https://storage.yandexcloud.net",
    "GP_NAME": "adb",
    "GP_HOST": "gp.data.lmru.tech",
    "GP_PORT": "5432",
    "PROMETHEUS_URL": "",
    "VAULT_NAMESPACE" : "mlops-template",
    "VAULT_PATH": "secret_vars",
    "VAULT_MOUNT_POINT": "prod"
}

RETRY_POLICY = {
    "num_retries": 12,
    "backoff_duration": "3600s",
    "backoff_factor": 1,
    "backoff_max_duration": "43200s",
}
