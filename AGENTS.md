# Feature Store Repo — Agent Guide

## What This Repo Is

The **feature engineering side** of a split-repo ML pattern. This repo loads raw data, engineers features, registers FeatureViews in the Snowflake Feature Store, and publishes Versioned Datasets that downstream consumers (the ML Training repo) read from.

It never touches model training, promotion, or inference. The contract between this repo and the ML Training repo is a **Versioned Dataset**.

**Use case:** Customer value features for a retail regression model.

## Repo Structure

```
├── main.py                          # Pipeline entrypoint (--domain flag)
├── feature_store_helper.py          # Orchestrator: discovers domains, registers entities + FVs
├── parameters.yml                   # Snowflake connection and feature store config
├── requirements.txt                 # Python dependencies
├── customer_features/               # One "domain node" per feature set
│   ├── entities.py                  # Entity definitions (CUSTOMER)
│   ├── source.yaml                  # Source tables, label column, metadata
│   └── features/
│       ├── base_features.py         # Base customer + purchase-behaviour features
│       └── derived_features.py      # Derived features (averages, days-since, etc.)
└── connection.json.example          # Snowflake credentials template
```

## Environment

Uses the shared `snowflake_ds` conda environment from the setup repo, or install from `requirements.txt`:

```bash
pip install -r requirements.txt
```

## How to Run

```bash
export SNOWFLAKE_CONNECTION_NAME=<your_connection>
python main.py --domain customer_features
```

Or use programmatically:

```python
from feature_store_helper import FeatureStoreHelper
helper = FeatureStoreHelper(session, "RETAIL_REGRESSION_DEMO", "FEATURE_STORE", "RETAIL_REGRESSION_DEMO_WH", source_schema="DS")
helper.load_domain("customer_features")
fs, registered_fvs = helper.register_all()
```

## Snowflake Connection

`main.py` checks `SNOWFLAKE_CONNECTION_NAME` env var first. If not set, it reads `connection.json` from the project root (copy from `connection.json.example`) and merges those credentials with database/schema/role/warehouse from `parameters.yml`.

## Configuration

All config lives in `parameters.yml`:

- **snowflake** — database, schema, role, warehouse
- **feature_store** — schema, entity name, join keys, FeatureView name/version, refresh frequency, dataset name

## Key Snowflake Objects

- **Database:** `RETAIL_REGRESSION_DEMO`
- **Schemas:** `DS` (raw data), `FEATURE_STORE`
- **Entity:** `CUSTOMER` (join key: `CUSTOMER_ID`)
- **FeatureViews:** `FV_CUSTOMER_BASE`, `FV_CUSTOMER_DERIVED` (backed by Dynamic Tables, 60-minute refresh)
- **Dataset:** `TRAINING_DATASET` (versioned, immutable)

## Architecture Notes

- `feature_store_helper.py` dynamically discovers feature domain folders (e.g. `customer_features/`), imports their entities and feature modules, and registers everything.
- `FeatureStoreHelper` accepts a `source_schema` parameter (defaults to the feature store schema). Source table lookups and feature view SQL use `source_schema`, while entity/FeatureView registration uses the feature store schema. This separates raw data (`DS`) from feature store objects (`FEATURE_STORE`).
- Each domain folder is self-contained: `entities.py` defines entities with `get_all_entities()`, `source.yaml` declares source tables, and `features/*.py` each expose `create_draft_feature_view()`.
- To add a new feature domain, create a new folder with the same structure and run `python main.py --domain <folder_name>`.
- The spine DataFrame uses `strftime('%Y-%m-%d %H:%M:%S')` for the AS-OF date (not just `%Y-%m-%d`) to avoid midnight timestamp issues with point-in-time joins.

## The Contract

This repo publishes a **Versioned Dataset**. The ML Training repo reads it by name and version. Neither repo imports code from the other.

## Common Modifications

- **Add features:** Create a new `.py` file in `customer_features/features/` exposing `create_draft_feature_view()`
- **Add a new feature domain:** Create a new folder (e.g. `product_features/`) with `entities.py`, `source.yaml`, and `features/`
- **Change refresh frequency:** Edit `refresh_freq` in `parameters.yml`
- **Refactor for a different use case:** Use the `refactor-framework` Cortex Code skill (`.cortex/skills/refactor-framework/SKILL.md`)
