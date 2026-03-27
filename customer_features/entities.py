from snowflake.ml.feature_store import Entity


customer_entity = Entity(
    name="CUSTOMER",
    join_keys=["CUSTOMER_ID"],
    desc="Primary key for a retail customer.",
)


def get_all_entities() -> list[Entity]:
    return [customer_entity]
