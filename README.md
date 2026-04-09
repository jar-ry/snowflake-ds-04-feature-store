# Split Repo ML on Snowflake — Feature Store

Feature engineering, Feature Store registration, and Versioned Dataset publishing for the blog post: **Split Repo ML on Snowflake: Separating Feature Store and Model Training**

This repo handles the **feature side** of the split-repo pattern. It loads raw data, engineers features, registers FeatureViews, and publishes Versioned Datasets that downstream consumers (like the [ML Training repo](https://github.com/jar-ry/snowflake-ds-04-ml-training)) read from.

## Repo Structure

```
feature-store-repo/
├── main.py                     # Pipeline entrypoint
├── feature_store_helper.py     # Orchestrator: discovers domains, registers entities + feature views
├── parameters.yml              # Snowflake connection and feature store config
├── requirements.txt
├── .gitignore
├── customer_features/          # Feature domain (one "node" in the pipeline)
│   ├── entities.py             # Entity definitions (CUSTOMER)
│   ├── source.yaml             # Source tables, label column, metadata
│   └── features/
│       ├── base_features.py          # Base customer + purchase-behaviour features
│       └── derived_features.py       # Derived features (averages, days-since, etc.)
└── README.md
```

## How It Works

The repo follows the same pattern as the [Snowflake Feature Store examples](https://github.com/snowflakedb/snowflake-ml-python/tree/main/snowflake/ml/feature_store/examples):

- **`feature_store_helper.py`** — A `FeatureStoreHelper` class that discovers feature domain folders, loads source data, registers entities, and creates draft feature views via dynamic import.
- **Each domain folder** (e.g. `customer_features/`) is a self-contained node containing:
  - `entities.py` — Entity definitions with a `get_all_entities()` function
  - `source.yaml` — Metadata: source tables, label columns, timestamp column, description
  - `features/` — One Python file per FeatureView, each exposing a `create_draft_feature_view()` function

To add a new feature domain, create a new folder with the same structure and `main.py --domain <folder_name>` will pick it up automatically.

## Quick Start

```python
from feature_store_helper import FeatureStoreHelper

helper = FeatureStoreHelper(session, "RETAIL_REGRESSION_DEMO", "FEATURE_STORE", "RETAIL_REGRESSION_DEMO_WH", source_schema="DS")
helper.list_domains()                           # Show available feature domains
helper.load_domain("customer_features")         # Load source tables
entities = helper.load_entities()               # Get Entity objects
fvs = helper.load_draft_feature_views()         # Get draft FeatureView objects
fs, registered = helper.register_all()          # Register everything in one call
```

Or run the full pipeline:

```bash
export SNOWFLAKE_CONNECTION_NAME=<your_connection>
python main.py --domain customer_features
```

## The Contract

The **Versioned Dataset** is the interface between this repo and the ML Training repo. This repo publishes it; the training repo reads it. Neither repo imports code from the other.

## Connection

`main.py` checks the `SNOWFLAKE_CONNECTION_NAME` env var first. If not set, it reads `connection.json` from the project root (copy from `connection.json.example`) and merges those credentials with database/schema/role/warehouse from `parameters.yml`.

## Setup

See the [setup repo](https://github.com/jar-ry/snowflake-ds-setup) for environment and Snowflake object creation.

## Related Repos

| Repo | Description |
|------|-------------|
| [snowflake-ds-setup](https://github.com/jar-ry/snowflake-ds-setup) | Environment setup, data generation, and helper utilities (run this first) |
| [snowflake-ds-04-ml-training](https://github.com/jar-ry/snowflake-ds-04-ml-training) | ML Training repo: consumes Versioned Datasets, trains, deploys, monitors |
| [snowflake-ds-03-ml-jobs-framework](https://github.com/jar-ry/snowflake-ds-03-ml-jobs-framework) | Single-repo version of this pipeline (Part 4) |
