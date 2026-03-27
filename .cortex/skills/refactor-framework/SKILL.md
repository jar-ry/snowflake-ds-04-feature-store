---
name: refactor-framework
description: "Refactor this Feature Store repo for a new use case. Use when: adapting features for a different model, dataset, or business problem. Triggers: refactor, adapt, new use case, change features, swap dataset, customise, customize, churn, fraud, forecasting, classification, new project, my own data, new domain."
---

# Refactor Feature Store

You are helping a user adapt this Snowflake Feature Store repo to their own use case. This repo follows the Snowflake Feature Store examples pattern: a `FeatureStoreHelper` class discovers feature domain folders, loads source data, registers entities and FeatureViews, and publishes Versioned Datasets.

## Repo Architecture

```
feature-store-repo/
├── main.py                     # Entrypoint (--domain flag)
├── feature_store_helper.py     # Orchestrator: discovers domains, registers entities + FVs
├── parameters.yml              # Snowflake connection and feature store config
├── customer_features/          # One "domain node" per feature set
│   ├── entities.py             # Entity definitions with get_all_entities()
│   ├── source.yaml             # Source tables, label column, timestamp, metadata
│   └── features/
│       ├── base_features.py          # Base FeatureView (create_draft_feature_view)
│       └── derived_features.py       # Derived FeatureView (create_draft_feature_view)
└── requirements.txt
```

The pattern: each domain folder is a self-contained node. `feature_store_helper.py` discovers them dynamically via `importlib`. To add a new domain, create a new folder with the same structure.

## Step 1: Gather Requirements

**Goal:** Understand the user's new use case before touching any code.

**Ask these questions (use ask_user_question tool):**

1. **Use case**: What are you building? (e.g. churn prediction, fraud detection, demand forecasting, recommendation scoring)
2. **Source tables**: What Snowflake tables will you use? Get the fully qualified names. Ask the user to list them or describe their data.
3. **Join logic**: How do the tables relate? What columns do they join on?
4. **Entity**: What is the primary entity? (e.g. CUSTOMER, PRODUCT, TRANSACTION) What are the join keys?
5. **Target column**: What column are you predicting? (This goes in `source.yaml` as `label_columns`)
6. **Timestamp column**: Which column tracks when records were updated? (Used for point-in-time correctness in FeatureViews)
7. **Feature ideas**: What features do you want to derive? Which are base features (direct from tables) and which are derived (calculations, aggregations)?
8. **Snowflake objects**: What database, schema, warehouse should the pipeline use? (Offer to keep the existing ones if experimenting.)

**STOP**: Confirm the requirements with the user before proceeding. Summarise what you understood and ask for corrections.

## Step 2: Decide — New Domain or Replace Existing

**Ask the user:**
- **Add a new domain alongside `customer_features`?** Create a new folder (e.g. `fraud_features/`) — the helper discovers it automatically.
- **Replace `customer_features` entirely?** Refactor the existing folder.

If adding a new domain, skip to Step 4. If replacing, continue to Step 3.

## Step 3: Refactor Configuration

**Goal:** Update `parameters.yml` for the new use case.

**File:** `parameters.yml`

**Changes:**
- `snowflake.*` — Update database, schema, role, warehouse to user's values
- `feature_store.schema` — Update if needed
- `feature_store.dataset_name` — Update to match the new use case

## Step 4: Create or Update the Domain Folder

### 4a: `entities.py`

**Create Entity definitions for the new use case:**
```python
from snowflake.ml.feature_store import Entity

my_entity = Entity(
    name="<ENTITY_NAME>",
    join_keys=["<JOIN_KEY>"],
    desc="<description>",
)

def get_all_entities() -> list[Entity]:
    return [my_entity]
```

If multiple entities are needed (e.g. CUSTOMER + PRODUCT), define them all and return them from `get_all_entities()`.

### 4b: `source.yaml`

**Define source metadata:**
```yaml
---
source_tables:
  - TABLE_A
  - TABLE_B
label_columns: TARGET_COLUMN
timestamp_column: UPDATED_AT
training_spine_table: TABLE_A
desc: Description of this feature domain.
model_category: regression  # or classification
```

### 4c: `features/base_features.py`

**Create a base FeatureView that joins source tables and selects raw/lightly-transformed columns:**

Every feature file must expose a `create_draft_feature_view()` function with this signature:
```python
def create_draft_feature_view(
    session: Session,
    source_dfs: list[DataFrame],
    source_tables: list[str],
    database: str,
    schema: str,
) -> FeatureView:
```

The function returns a `FeatureView` with:
- `entities` — list of Entity objects (import from `entities.py`)
- `feature_df` — a Snowpark DataFrame (usually via `session.sql(...)`)
- `timestamp_col` — for point-in-time correctness
- `refresh_freq` — e.g. `"60 minute"` for Dynamic Table refresh
- `desc` — human-readable description

Attach feature descriptions with `.attach_feature_desc({...})`.

### 4d: `features/derived_features.py` (optional)

**Create derived FeatureViews for calculated features (ratios, days-since, aggregations):**
- Use SQL for complex derivations (CASE/WHEN, DATEDIFF, window functions)
- Handle division-by-zero with CASE WHEN or NULLIF
- Reference source tables via `{database}.{schema}.TABLE_NAME`

### 4e: Additional feature files

Create as many feature files as needed. Each one in the `features/` directory will be auto-discovered by the helper.

## Step 5: Update Main (if needed)

**File:** `main.py`

Usually no changes needed — just run with the new domain name:
```bash
python main.py --domain <new_domain_name>
```

If the new domain needs custom dataset publishing logic, update the `publish_dataset()` function.

## Step 6: Validate the Versioned Dataset Contract

**Critical:** The Versioned Dataset is the contract with the ML Training repo. Verify:

- [ ] All feature columns are present in the published dataset
- [ ] The label column (`label_columns` in `source.yaml`) is included
- [ ] Column names match what the ML Training repo expects in `conf/parameters.yml`
- [ ] The entity join key is present
- [ ] The timestamp column is correct

**If the ML Training repo exists alongside this repo**, cross-reference:
1. Read the training repo's `conf/parameters.yml`
2. Check `modelling.feature_columns`, `modelling.target_column`, `modelling.numerical_features`, `modelling.categorical_features`
3. Verify every column name matches what this repo publishes

## Step 7: Test Run

**Suggest:**
```bash
# Register features and publish dataset
python main.py --domain <domain_name>
```

If errors occur, help debug by reading logs and tracing the issue back to the relevant file (usually entity definition, SQL in feature views, or source.yaml table names).

## Important Notes

- **Never hardcode values** — connection details go in `parameters.yml`, source tables in `source.yaml`
- **Keep the domain pattern** — each domain is a self-contained folder with `entities.py`, `source.yaml`, and `features/`
- **The `FeatureStoreHelper` is generic** — do not modify it unless adding new capabilities (it discovers domains dynamically)
- **Feature descriptions** in `.attach_feature_desc()` are optional but good practice
- **`refresh_freq`** controls how often the Dynamic Table backing the FeatureView refreshes
- **The Versioned Dataset is the contract** — the ML Training repo reads from it without knowing how features are computed
