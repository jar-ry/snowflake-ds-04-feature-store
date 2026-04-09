import importlib
import logging
import os
from pathlib import Path
from typing import Optional

import yaml
from snowflake.ml.feature_store import (
    CreationMode,
    Entity,
    FeatureStore,
    FeatureView,
)
from snowflake.snowpark import DataFrame, Session

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class FeatureStoreHelper:
    def __init__(self, session: Session, database: str, schema: str, warehouse: str, source_schema: str | None = None) -> None:
        self._session = session
        self._database = database
        self._schema = schema
        self._source_schema = source_schema or schema
        self._warehouse = warehouse
        self._clear()

    def _clear(self) -> None:
        self._selected_domain: Optional[str] = None
        self._source_tables: list[str] = []
        self._source_dfs: list[DataFrame] = []
        self._label_columns: list[str] = []
        self._timestamp_column: Optional[str] = None
        self._training_spine_table: str = ""

    def list_domains(self) -> DataFrame:
        root_dir = Path(__file__).parent
        rows = []
        for name in sorted(os.listdir(root_dir)):
            source_path = root_dir / name / "source.yaml"
            if source_path.exists():
                cfg = self._read_yaml(str(source_path))
                rows.append((name, cfg.get("model_category", ""), cfg.get("desc", ""), cfg.get("label_columns", "")))
        return self._session.create_dataframe(rows, schema=["NAME", "MODEL_CATEGORY", "DESC", "LABEL_COLS"])

    def load_domain(self, domain_name: str) -> list[str]:
        self._clear()
        self._selected_domain = domain_name

        root_dir = Path(__file__).parent
        source_cfg = self._read_yaml(str(root_dir / domain_name / "source.yaml"))

        if "label_columns" in source_cfg:
            self._label_columns = [c.strip() for c in source_cfg["label_columns"].split(",")]
        if "timestamp_column" in source_cfg:
            self._timestamp_column = source_cfg["timestamp_column"]
        if "training_spine_table" in source_cfg:
            self._training_spine_table = (
                f"{self._database}.{self._source_schema}.{source_cfg['training_spine_table']}"
            )

        for table_ref in source_cfg.get("source_tables", []):
            fq_table = f"{self._database}.{self._source_schema}.{table_ref}"
            df = self._session.table(fq_table)
            self._source_tables.append(table_ref)
            self._source_dfs.append(df)
            logger.info(f"Loaded source table: {fq_table}")

        return self._source_tables

    def load_entities(self) -> list[Entity]:
        mod = importlib.import_module(f"{self._selected_domain}.entities")
        return mod.get_all_entities()

    def load_draft_feature_views(self) -> list[FeatureView]:
        fvs = []
        features_dir = Path(__file__).parent / self._selected_domain / "features"
        for fname in sorted(os.listdir(features_dir)):
            if not fname.endswith(".py") or fname.startswith("_"):
                continue
            mod_path = f"{self._selected_domain}.features.{fname.removesuffix('.py')}"
            mod = importlib.import_module(mod_path)
            fv = mod.create_draft_feature_view(
                self._session, self._source_dfs, self._source_tables, self._database, self._source_schema
            )
            fvs.append(fv)
        return fvs

    def register_all(self) -> tuple[FeatureStore, list[FeatureView]]:
        fs = FeatureStore(
            self._session,
            self._database,
            self._schema,
            self._warehouse,
            creation_mode=CreationMode.CREATE_IF_NOT_EXIST,
        )

        for entity in self.load_entities():
            fs.register_entity(entity)
            logger.info(f"Registered entity: {entity.name}")

        registered = []
        for fv in self.load_draft_feature_views():
            reg_fv = fs.register_feature_view(feature_view=fv, version="V_1", block=True, overwrite=True)
            registered.append(reg_fv)
            logger.info(f"Registered feature view: {fv.name}")

        return fs, registered

    def get_label_cols(self) -> list[str]:
        return self._label_columns

    def get_timestamp_col(self) -> Optional[str]:
        return self._timestamp_column

    def get_training_spine_table(self) -> str:
        return self._training_spine_table

    def _read_yaml(self, path: str) -> dict:
        with open(path) as f:
            return yaml.safe_load(f)
