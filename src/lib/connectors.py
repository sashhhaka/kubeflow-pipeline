import io
import json
import logging
import os
import pickle
from typing import Any, Dict, List, Optional

import boto3
import hvac
import pandas as pd
import psycopg2


class GreenplumConnector:
    """
    Connector for communicating with GreenPlum.
    Parameters for connection can be either given to function
    or provided as environmental variables.

    If provide as environmental variables:
      - GP_DB as database: GreenPlum database
      - GP_USER as user: GreenPlum user
      - GP_PASS as password: GreenPlum user's password
      - GP_HOST as host: GreenPlum host
      - GP_PORT as port: GreenPlum port

    """

    def __init__(
        self,
        database: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[str] = None,
    ) -> None:
        self._log = logging.getLogger(__name__)

        if database is None:
            database = os.getenv("GP_DB", None)
            assert database is not None, "GP_DB env not found"

        if user is None:
            user = os.getenv("GP_USER", None)
            assert user is not None, "GP_USER env not found"

        if password is None:
            password = os.getenv("GP_PASS", None)
            assert password is not None, "GP_PASS env not found"

        if host is None:
            host = os.getenv("GP_HOST", None)
            assert host is not None, "GP_HOST env not found"

        if port is None:
            port = os.getenv("GP_PORT", None)
            assert port is not None, "GP_PORT env not found"

        try:
            self.con = psycopg2.connect(
                database=os.getenv("GP_DB"),
                user=os.getenv("GP_USER"),
                password=os.getenv("GP_PASS"),
                host=os.getenv("GP_HOST"),
                port=os.getenv("GP_PORT"),
            )
        except psycopg2.OperationalError as e:
            self._log.error(e)
        self._log.info("GP Connector: Connection to GP established.")

    def execute(self, query: str) -> pd.DataFrame:
        """
        Execute SQL query.

        :param query: Query as text.
        :return: Dataframe with data from query.
        """
        try:
            data = pd.read_sql_query(query, self.con)
        except Exception as e:
            self._log.error("GP Connector: GP data download failed with %s.", e)
            data = pd.DataFrame()
        return data

    def close_conenction(self) -> None:
        """
        Close SQL connection.
        """
        self.con.close()


class S3Connector:
    """
    Connector for communicating with S3.
    Parameters for connection can be either given to function
    or provided as environmental variables.

    If provide as environmental variables:
      - S3_ENDPOINT for s3_endpoint: usually https://storage.yandexcloud.net
      - S3_KEY_ID for s3_key_id: aws(yandex) key id
      - S3_ACCESS_KEY for s3_access_key: aws(yandex) secret key
      - S3_BUCKET for s3_bucket: s3 bucket name

    """

    def __init__(
        self,
        s3_endpoint: Optional[str] = None,
        s3_key_id: Optional[str] = None,
        s3_access_key: Optional[str] = None,
        s3_bucket: Optional[str] = None,
    ) -> None:
        self._log = logging.getLogger(__name__)

        if s3_endpoint is None:
            s3_endpoint = os.getenv("S3_ENDPOINT", None)
            assert s3_endpoint is not None, "S3_ENDPOINT env not found"

        if s3_key_id is None:
            s3_key_id = os.getenv("S3_KEY_ID", None)
            assert s3_key_id is not None, "S3_KEY_ID env not found"

        if s3_access_key is None:
            s3_access_key = os.getenv("S3_ACCESS_KEY", None)
            assert s3_access_key is not None, "S3_ACCESS_KEY env not found"

        if s3_bucket is None:
            self.bucket = os.getenv("S3_BUCKET", None)
            assert self.bucket is not None, "S3_BUCKET env not found"
        else:
            self.bucket = s3_bucket

        self.s3_session = boto3.session.Session().client(
            service_name="s3",
            endpoint_url=s3_endpoint,
            aws_access_key_id=s3_key_id,
            aws_secret_access_key=s3_access_key,
        )
        try:
            self.s3_session.head_bucket(Bucket=self.bucket)
        except self.s3_session.exceptions.ClientError:
            self._log.info("S3Connector: Access to S3 denied.")

        self.s3_resource = boto3.resource(
            "s3",
            endpoint_url=s3_endpoint,
            aws_access_key_id=s3_key_id,
            aws_secret_access_key=s3_access_key,
        )

        try:
            self.s3_session.list_objects(Bucket=self.bucket)
        except self.s3_session.exceptions.NoSuchBucket:
            self._log.error("S3Connector: There is no %s on s3.", self.bucket)

        self._log.info("S3Connector: Connection successfully inited.")

    def clean_s3(self, folders: List[str], n: int) -> None:
        """
        Clean S3 folders, leaving the last N objects.

        :param folders: Which folders to clean.
        :param n: How many last files to leave in each folder.
        """
        for folder in folders:
            list_of_files = self.list_folder(folder)
            if list_of_files:
                if len(list_of_files) > n:
                    for obj_name in list_of_files[:-n]:
                        self.s3_session.delete_object(
                            Bucket=self.bucket,
                            Key=obj_name,
                        )
            self._log.info(
                "S3Connector: Clean-up s3 %s up to %i versions.", folder, n
            )

    def list_folder(self, folder: str) -> List[str]:
        """
        List objects in a folder.

        :param name: Folder name.
        :return: List of files' names.
        """
        s3_session, bucket = self.s3_session, self.bucket

        list_of_files = [
            x["Key"] for x in s3_session.list_objects(Bucket=bucket)["Contents"]
        ]
        if f"{folder}/" not in list_of_files:
            raise NameError(
                f"S3Connector: Folder {folder} not found in bucket {bucket}."
            )
        list_of_files = [
            x.split(f"{folder}/")[1] for x in list_of_files if f"{folder}" in x
        ]
        list_of_files.sort()

        return list_of_files

    def load_file(self, filename: str) -> pd.DataFrame:
        """
        Load file by name. Support pkl, csv and json extensions.

        :param filename: File name.
        :return: Dataframe.
        """
        s3_session, bucket = self.s3_session, self.bucket
        try:
            file = s3_session.get_object(Bucket=bucket, Key=filename)
        except s3_session.exceptions.NoSuchKey:
            self._log.error("S3Connector: There is no %s in %s." , filename, bucket)

        _, fextension = os.path.splitext(filename)
        if fextension == ".pkl":
            dataset = pickle.loads(file["Body"].read())
        elif fextension == ".csv":
            dataset = pd.read_csv(file["Body"])
        elif fextension == ".json":
            obj = self.s3_resource.Object(bucket_name=bucket, key=filename)
            dataset = json.load(obj.get()["Body"])
            dataset = pd.DataFrame(dataset)
        else:
            raise NotImplementedError(f"S3Connector: {fextension} not yet supported.")

        return dataset

    def save_table(self, data: pd.DataFrame, filename: str) -> None:
        """
        Save table to S3. Supported extensions are pkl and csv.

        :param filename: File name.
        """
        filebuffer = io.BytesIO()
        _, fextension = os.path.splitext(filename)
        if fextension == ".csv":
            data.to_csv(filebuffer, index=False)
        elif fextension == ".pkl":
            data.to_pickle(filebuffer, protocol=4)
        else:
            raise ValueError(
                f"S3_connector: Supported formats are csv or pkl, not {fextension}!"
            )
        s3_resource, bucket = self.s3_resource, self.bucket
        s3_resource.Object(bucket, filename).put(Body=filebuffer.getvalue())
        self._log.info("S3_connector: Table saved to S3 : %s", filename)
        
    def save_model(self, model:Any, filename:str) -> None:
        """
        Save model to S3 in pkl format.

        :param model: Model.
        :param filename: Model file name.
        """
        obj = pickle.dumps(model)
        s3_resource, bucket = self.s3_resource, self.bucket
        s3_resource.Object(bucket, filename).put(Body=obj)
        self._log.info("S3_connector: Model saved to S3 : %s", filename)
        
    def read_model(self, filename:str) -> None:
        """
        Read pkl-format model from S3.

        :param filename: Model file name.
        :return: Model.
        """
        s3_session, bucket = self.s3_session, self.bucket
        try:
            obj = s3_session.get_object(Bucket=bucket, Key=filename)
        except s3_session.exceptions.NoSuchKey:
            self._log.error("S3Connector: There is no %s in %s." , filename, bucket)
        model = pickle.loads(obj["Body"].read())
        
        return model


class VaultConnector:
    """
    Connector for reading secrets from Vault.
    Parameters for connection can be either given to function
    or provided as environmental variables.

    If provide as env variables:
      - VAULT_ROLE_ID for role_id
      - VAULT_SECRET_ID for secret_id
      - VAULT_NAMESPACE for namespace

    :param role_id: Vault role id.
    :param secret_id: Vault secret id.
    :param namespace: Vault namespace.
    """

    def __init__(
        self,
        role_id: Optional[str] = None,
        secret_id: Optional[str] = None,
        namespace: Optional[str] = None,
    ) -> None:
        if role_id is None:
            role_id = os.getenv("VAULT_ROLE_ID", None)
            assert role_id is not None, "VAULT_ROLE_ID env not found"

        if secret_id is None:
            secret_id = os.getenv("VAULT_SECRET_ID", None)
            assert secret_id is not None, "VAULT_SECRET_ID env not found"

        if namespace is None:
            namespace = os.getenv("VAULT_NAMESPACE", None)
            assert namespace is not None, "VAULT_NAMESPACE env not found"

        self.client = hvac.Client(url="https://vault.lmru.tech/", namespace=namespace)

        self.client.auth.approle.login(
            role_id=role_id,
            secret_id=secret_id,
        )

        self._log = logging.getLogger(__name__)
        self._log.info("Vault Connector: Connection to Vault established.")

    def get_connector(self) -> hvac.Client:
        """
        HVac Client.
        """
        return self.client

    def _get_secrets(
        self, path: Optional[str] = None, mount_point: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get a dictionary of all keys and secrets.

        :param path: Vault path.
        :param mount_point: Vault mount point.
        :return: Secrets.
        """
        if path is None:
            path = "/"

        if mount_point is None:
            mount_point = "/"

        secrets_dict = self.client.secrets.kv.v2.read_secret(
            path=f"{path}", mount_point=f"{mount_point}"
        )["data"]["data"]

        return secrets_dict

    def list_secrets_keys(
        self, path: Optional[str] = None, mount_point: Optional[str] = None
    ) -> None:
        """
        List secrets' keys.

        :param path: Vault path.
        :param mount_point: Vault mount point.
        :return: Secrets' keys.
        """
        secrets_dict = self._get_secrets(path, mount_point)
        return secrets_dict.keys()

    def set_secrets_as_envvars(
        self, path: Optional[str] = None, mount_point: Optional[str] = None
    ) -> None:
        """
        Set all secrets from Vault as environmental variables.

        :param path: Vault path.
        :param mount_point: Vault mount point.
        """

        secrets_dict = self._get_secrets(path, mount_point)

        for key, value in secrets_dict.items():
            os.environ[key] = value

    def set_secrets_list_as_envvars(
        self,
        secrets: List[str],
        path: Optional[str] = None,
        mount_point: Optional[str] = None,
    ) -> None:
        """
        Set only secrets with keys from the secrets param list
        as environmental variables.

        :param path: Vault path.
        :param mount_point: Vault mount point.
        :param secrets: Secrets' keys.
        """

        secrets_dict = self._get_secrets(path, mount_point)

        for key in secrets:
            os.environ[key] = secrets_dict[key]
