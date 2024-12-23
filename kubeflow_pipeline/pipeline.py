import sys
from kfp import dsl
from kfp import kubernetes
from kfp.compiler.compiler import Compiler
from kfp.dsl import (container_component, ContainerSpec, Artifact, Dataset, Input, Output, OutputPath, Model,
                     Metrics, ClassificationMetrics)

sys.path.append(".")
sys.path.append("..")
from kubeflow_pipeline.kfp_vars import ENV_VARS, SECRETS, SECRETS_APPROLE, RETRY_POLICY, PIPELINE_PATH


team_name = "dataplatform"
project_name = "mlops/project-template"
tag = "master"


@container_component
def download_data(
    metrics: Output[Metrics],
    data: Output[Dataset]
):
    return ContainerSpec(
        image=f"docker-local-{team_name}.art.lmru.tech/{team_name}/{project_name}/base-image:{tag}",
        command=["python", "pipeline_steps/download_data/task.py"],
        args=[
        "--executor_input",
            dsl.PIPELINE_TASK_EXECUTOR_INPUT_PLACEHOLDER,
    ]
)

@container_component
def prepare_data(
    data: Input[Dataset],
    metrics: Output[Metrics],
    train: Output[Dataset],
    test: Output[Dataset]
):
    return ContainerSpec(
        image=f"docker-local-{team_name}.art.lmru.tech/{team_name}/{project_name}/base-image:{tag}",
        command=["python", "pipeline_steps/prepare_data/task.py"],
        args=[
        "--executor_input",
            dsl.PIPELINE_TASK_EXECUTOR_INPUT_PLACEHOLDER,
    ]
)

@container_component
def train_model(
    train: Input[Dataset],
    test: Input[Dataset],
    metrics: Output[ClassificationMetrics],
    model: Output[Model],
):
    return ContainerSpec(
        image=f"docker-local-{team_name}.art.lmru.tech/{team_name}/{project_name}/base-image:{tag}",
        command=["python", "pipeline_steps/train_model/task.py"],
        args=[
        "--executor_input",
            dsl.PIPELINE_TASK_EXECUTOR_INPUT_PLACEHOLDER,
    ]
)

from typing import NamedTuple
@container_component
def switch_model(
    model: Input[Model],
    test: Input[Dataset],
    metrics: Output[Metrics],
):
    return ContainerSpec(
        image=f"docker-local-{team_name}.art.lmru.tech/{team_name}/{project_name}/base-image:{tag}",
        command=["python", "pipeline_steps/switch_model/task.py"],
        args=[
        "--executor_input",
            dsl.PIPELINE_TASK_EXECUTOR_INPUT_PLACEHOLDER,
    ]
)


@container_component
def inference_model(
    metrics: Output[Metrics],
):
    return ContainerSpec(
        image=f"docker-local-{team_name}.art.lmru.tech/{team_name}/{project_name}/base-image:{tag}",
        command=["python", "pipeline_steps/model_inference/task.py"],
        args=[
        "--executor_input",
            dsl.PIPELINE_TASK_EXECUTOR_INPUT_PLACEHOLDER,
    ]
)


def prepare_task(task):
    # Установка retry политик.
    task.set_retry(**RETRY_POLICY)

    # Добавление секретов.
    for (key, value) in SECRETS.items():
        kubernetes.use_secret_as_env(task,
                                     secret_name=SECRETS_APPROLE,
                                     secret_key_to_env={key: value})

    # Добавление переменных окружения.
    for (key, value) in ENV_VARS.items():
        task.set_env_variable(name=key, value=value)
        
    task = task.set_caching_options(enable_caching=False)

    return task

                
@dsl.pipeline(name="project_template")
def pipeline():
    
    task_download_data = download_data()
    task_download_data = prepare_task(task_download_data)

    task_prepare_data = prepare_data(data = task_download_data.outputs["data"])
    task_prepare_data = prepare_task(task_prepare_data)

    task_train_model = train_model(train = task_prepare_data.outputs["train"], test = task_prepare_data.outputs["test"])
    task_train_model = prepare_task(task_train_model)

    task_switch_model = switch_model(model= task_train_model.outputs["model"], test = task_prepare_data.outputs["test"])
    task_switch_model = prepare_task(task_switch_model)


if __name__ == "__main__":
    Compiler().compile(pipeline_func=pipeline, package_path=PIPELINE_PATH)
