import argparse
import json
import logging.config
import os
import sys
from datetime import datetime
from typing import Tuple

import pandas as pd
from kfp.dsl import Metrics, Input, Output, Dataset
from kfp.dsl.executor import Executor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import Normalizer

sys.path.append(".")
from lib import config, connectors
from lib.logging_config import LOGGING_CONFIG

logging.config.dictConfig(LOGGING_CONFIG)
_log = logging.getLogger(__name__)


def preprcocess_and_split_data(data: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Normalize data.
    """
    target = data[config.TARGET].copy()
    features = data[config.FEATURES].copy()

    X_train, X_test, y_train, y_test = train_test_split(
        features,
        target,
        test_size=config.TEST_SIZE,
        random_state=42,
        shuffle=True,
        stratify=target,
    )

    norm = Normalizer()
    X_train_norm = pd.DataFrame(
        norm.fit_transform(X_train), columns=features.columns, index=X_train.index
    )
    X_test_norm = pd.DataFrame(
        norm.transform(X_test), columns=features.columns, index=X_test.index
    )

    return pd.concat([X_train_norm, y_train], axis=1), pd.concat(
        [X_test_norm, y_test], axis=1
    )


def prepare_data(data: Input[Dataset],
    metrics: Output[Metrics],
    train: Output[Dataset],
    test: Output[Dataset]) -> None:
    """
    Read train dataset from prevous step, normalize, save train and test splitted.
    """
    # Read data from previous step.
    dataset = pd.read_csv(data.path)
    train_data, test_data = preprcocess_and_split_data(dataset)
    _log.info("Task prepare data: datasets prepared.\n")

    # Log metrics (choose your own!)
    datestamp = datetime.now().strftime("%Y%m%d")
    metrics.log_metric("date", datestamp)
    metrics.log_metric("train_size", train_data.shape[0])
    metrics.log_metric("test_size", test_data.shape[0])
    metrics.log_metric("split", config.TEST_SIZE)

    train_data.to_csv(train.path, index_label=0)
    test_data.to_csv(test.path, index_label=0)

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
    executor = Executor(executor_input, prepare_data)
    executor.execute()
