import argparse
import json
import logging.config
import os
import sys

from kfp.dsl import Metrics, Output, Dataset
from kfp.dsl.executor import Executor
from sklearn.datasets import load_wine

sys.path.append(".")
from lib import connectors
from lib.logging_config import LOGGING_CONFIG

logging.config.dictConfig(LOGGING_CONFIG)
_log = logging.getLogger(__name__)


def download_data(metrics: Output[Metrics], data: Output[Dataset]) -> None:
    """
    Download data from any source.
    We use toy wine dataset.
    """

    # Download data.
    frame = load_wine(as_frame=True)
    dataset = frame["data"]
    dataset["target"] = frame["target"]
    # Save dataset as output.
    dataset.to_csv(data.path, index=False, encoding='utf-8')

    # Save metrics as output.
    with open(metrics.path, "w") as f:
        json.dump({"test": "test"}, f)
    metrics.name = "metrics"

    _log.info("Task download data: artifacts uploaded.\n")


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
    executor = Executor(executor_input, download_data)
    executor.execute()
