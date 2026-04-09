import argparse
import json
import logging
import os
from datetime import datetime
from pathlib import Path

import yaml
import snowflake.snowpark.functions as F
from snowflake.ml.feature_store import FeatureStore
from snowflake.snowpark import Session

from feature_store_helper import FeatureStoreHelper

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s")
logger = logging.getLogger(__name__)


def get_session(conf: dict) -> Session:
    connection_name = os.getenv("SNOWFLAKE_CONNECTION_NAME")
    if connection_name:
        session = Session.builder.config("connection_name", connection_name).create()
    else:
        conn_file = Path(__file__).parent / "connection.json"
        with open(conn_file) as f:
            conn_cfg = json.load(f)
        session = Session.builder.configs(
            {
                **conn_cfg,
                "database": conf["snowflake"]["database"],
                "schema": conf["snowflake"]["schema"],
                "role": conf["snowflake"]["role"],
                "warehouse": conf["snowflake"]["warehouse"],
            }
        ).create()
    session.sql(f"USE DATABASE {conf['snowflake']['database']}").collect()
    session.sql(f"USE SCHEMA {conf['snowflake']['schema']}").collect()
    session.sql(f"USE ROLE {conf['snowflake']['role']}").collect()
    return session


def publish_dataset(fs: FeatureStore, feature_views, conf: dict):
    dataset_name = conf["feature_store"]["dataset_name"]

    spine_sdf = feature_views[0].feature_df.group_by("CUSTOMER_ID").agg(
        F.lit(datetime.now().strftime("%Y-%m-%d %H:%M:%S")).as_("ASOF_DATE")
    )

    dataset = fs.generate_dataset(
        name=dataset_name,
        version=datetime.now().strftime("V_%Y%m%d_%H%M%S"),
        spine_df=spine_sdf,
        features=feature_views,
        spine_timestamp_col="ASOF_DATE",
    )
    logger.info(f"Published dataset: {dataset_name}")
    return dataset


def main(domain: str = "customer_features"):
    conf_path = Path(__file__).parent / "parameters.yml"
    with open(conf_path) as f:
        conf = yaml.safe_load(f)

    session = get_session(conf)
    db = conf["snowflake"]["database"]
    fs_schema = conf["feature_store"]["schema"]
    wh = conf["snowflake"]["warehouse"]

    source_schema = conf["snowflake"]["schema"]
    helper = FeatureStoreHelper(session, db, fs_schema, wh, source_schema=source_schema)

    logger.info("Available feature domains:")
    helper.list_domains().show()

    logger.info(f"Loading domain: {domain}")
    helper.load_domain(domain)

    logger.info("Registering entities and feature views...")
    fs, registered_fvs = helper.register_all()

    logger.info("Publishing Versioned Dataset...")
    publish_dataset(fs, registered_fvs, conf)

    logger.info("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Feature Store pipeline.")
    parser.add_argument("--domain", default="customer_features", help="Feature domain folder to load.")
    args = parser.parse_args()
    main(args.domain)
