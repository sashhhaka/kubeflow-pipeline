FROM docker-local-dataplatform.art.lmru.tech/dataplatform/mlops/kubeflow-pipeline/kfp-upload:v2

USER root

COPY kubeflow_pipeline/pipeline.py /pipeline/pipeline.py
COPY kubeflow_pipeline/kfp_vars.py /pipeline/kubeflow_pipeline/kfp_vars.py

WORKDIR /pipeline

ARG KUBEFLOW_USERNAME
ARG KUBEFLOW_PASSWORD
ARG PIPELINE_PATH
ARG PIPELINE_NAME
ARG NAMESPACE

ENV KUBEFLOW_USERNAME=$KUBEFLOW_USERNAME
ENV KUBEFLOW_PASSWORD=$KUBEFLOW_PASSWORD
ENV PIPELINE_PATH=$PIPELINE_PATH
ENV PIPELINE_NAME=$PIPELINE_NAME
ENV NAMESPACE=$NAMESPACE

RUN python pipeline.py &&\
    python -u task_upload_pipeline.py