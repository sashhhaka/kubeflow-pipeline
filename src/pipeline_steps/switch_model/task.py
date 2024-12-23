import argparse
import json
import logging.config
import os
import pandas as pd
import pickle
import sys

from kfp.dsl import Artifact, Metrics, Input, Output, Dataset, InputPath, Model
from kfp.dsl.executor import Executor
from sklearn.metrics import f1_score

sys.path.append(".")
from lib import config, connectors
from lib.logging_config import LOGGING_CONFIG

logging.config.dictConfig(LOGGING_CONFIG)
_log = logging.getLogger(__name__)


def switch_model(model: Input[Model],
                 test: Input[Dataset],
                 metrics: Output[Metrics]) -> None:
    """
    Switch inference model based on f1 score.
    """
    # Read new and current model from S3.
    s3_con = connectors.S3Connector()
    current_model = s3_con.load_file("template/models/inference_model.pkl")
    with open(model.path, "rb") as f:
        new_model = pickle.load(f)

    # Read test data from previous steps.
    test = pd.read_csv(test.path)
    _log.info("Task switch model: models and test data downloaded from S3.\n")

    # Train model.
    X_test, y_test = test[config.FEATURES], test[config.TARGET]
    y_pred_current = current_model.predict(X_test)
    y_pred_new = new_model.predict(X_test)
    _log.info("Task switch model: predictions made.\n")

    # Choose model.
    f1_score_current = f1_score(y_test, y_pred_current, average="macro")
    f1_score_new = f1_score(y_test, y_pred_new, average="macro")
    if f1_score_new > f1_score_current:
        s3_con.save_model(new_model, "template/models/inference_model.pkl")
        _log.info("Task switch model: new model saved for inference.\n")
    else:
        _log.info("Task switch model: current model left for inference.\n")

    # Log metrics.
    metrics.log_metric("f1score_current", f1_score_current)
    metrics.log_metric("f1score_new", f1_score_new)
    _log.info("Task switch model: metrics collected.\n")


if __name__ == "__main__":
    vault_con = connectors.VaultConnector()
    vault_con.set_secrets_as_envvars(
        path=os.getenv("VAULT_PATH"), mount_point=os.getenv("VAULT_MOUNT_POINT")
    )
    _log.info("Secrets imported from vault\n")
    parser = argparse.ArgumentParser()
    parser.add_argument("--executor_input", type=str, required=True)
    args = parser.parse_args()

    executor_input = json.loads(args.executor_input)
    _log.info(executor_input)
    os.environ["CLUSTER_SPEC"] = '{"task":{"type":"false"}}'
    executor = Executor(executor_input, switch_model)
    executor.execute()
