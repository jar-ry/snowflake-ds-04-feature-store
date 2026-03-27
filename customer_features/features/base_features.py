from snowflake.ml.feature_store import FeatureView
from customer_features.entities import customer_entity
from snowflake.snowpark import DataFrame, Session


def create_draft_feature_view(
    session: Session,
    source_dfs: list[DataFrame],
    source_tables: list[str],
    database: str,
    schema: str,
) -> FeatureView:
    """Customer purchase-behaviour features joined from CUSTOMERS and PURCHASE_BEHAVIOR."""
    query = session.sql(
        f"""
        select
            c.CUSTOMER_ID,
            c.AGE,
            c.GENDER,
            c.ANNUAL_INCOME,
            c.LOYALTY_TIER,
            c.TENURE_MONTHS,
            c.SIGNUP_DATE,
            b.AVG_ORDER_VALUE,
            b.PURCHASE_FREQUENCY,
            b.RETURN_RATE,
            b.MONTHLY_CUSTOMER_VALUE,
            b.LAST_PURCHASE_DATE,
            b.TOTAL_ORDERS,
            b.UPDATED_AT as BEHAVIOR_UPDATED_AT
        from {database}.{schema}.CUSTOMERS c
        left join {database}.{schema}.PURCHASE_BEHAVIOR b
            on c.CUSTOMER_ID = b.CUSTOMER_ID
        """
    )

    return FeatureView(
        name="fv_customer_base",
        entities=[customer_entity],
        feature_df=query,
        timestamp_col="BEHAVIOR_UPDATED_AT",
        refresh_freq="60 minute",
        desc="Base customer and purchase behaviour features refreshed hourly.",
    ).attach_feature_desc(
        {
            "AGE": "Customer age.",
            "GENDER": "Customer gender.",
            "ANNUAL_INCOME": "Rounded annual income.",
            "LOYALTY_TIER": "Loyalty tier: low, medium, high.",
            "TENURE_MONTHS": "Months since account creation.",
            "AVG_ORDER_VALUE": "Average order value.",
            "PURCHASE_FREQUENCY": "Number of purchases per month.",
            "RETURN_RATE": "Product return rate.",
            "MONTHLY_CUSTOMER_VALUE": "Expected monthly customer value (regression target).",
            "TOTAL_ORDERS": "Total number of orders.",
        }
    )
