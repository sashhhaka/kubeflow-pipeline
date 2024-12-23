import argparse
import json
import logging.config
import os
import pandas as pd
import pickle
import sys

from datetime import datetime
from kfp.dsl import Artifact, ClassificationMetrics, Input, Output, Dataset, Model
from kfp.dsl.executor import Executor
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import confusion_matrix

sys.path.append(".")
from lib import config, connectors
from lib.logging_config import LOGGING_CONFIG

logging.config.dictConfig(LOGGING_CONFIG)
_log = logging.getLogger(__name__)


def train_model(train: Input[Dataset],
                test: Input[Dataset],
                metrics: Output[ClassificationMetrics],
                model: Output[Model]) -> None:
    """
    Read train dataset, normalize, save train and test splitted for the next steps.
    """
    # Read data from previous step.
    train_dataset = pd.read_csv(train.path)
    test_dataset = pd.read_csv(test.path)
    _log.info("Task train model: datasets prepared.\n")

    # Train model.
    X_train, y_train = train_dataset[config.FEATURES], train_dataset[config.TARGET]
    X_test, y_test = test_dataset[config.FEATURES], test_dataset[config.TARGET]
    clf = RandomForestClassifier()
    clf.fit(X_train, y_train)
    y_pred = clf.predict(X_test)
    _log.info("Task train model: model trained.\n")

    # Log metrics.
    metrics.log_confusion_matrix(sorted(y_train.unique()),
                                 confusion_matrix(y_test, y_pred).tolist())
    _log.info("Task train model: metrics collected.\n")

    # Save model for next step.
    with open(model.path, "wb") as f:
        pickle.dump(clf, f)
    _log.info(f"Task train model: model saved to {model.path}.\n")


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
    executor = Executor(executor_input, train_model)
    executor.execute()
