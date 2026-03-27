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
    query = session.sql(
        f"""
        select
            c.CUSTOMER_ID,
            b.UPDATED_AT as BEHAVIOR_UPDATED_AT,
            case
                when c.TENURE_MONTHS = 0 then null
                else b.TOTAL_ORDERS / c.TENURE_MONTHS
            end as AVERAGE_ORDER_PER_MONTH,
            datediff('day', b.LAST_PURCHASE_DATE, b.UPDATED_AT) as DAYS_SINCE_LAST_PURCHASE,
            datediff('day', c.SIGNUP_DATE, b.UPDATED_AT) as DAYS_SINCE_SIGNUP,
            case
                when b.PURCHASE_FREQUENCY = 0 then null
                else 30 / b.PURCHASE_FREQUENCY
            end as EXPECTED_DAYS_BETWEEN_PURCHASES,
            round(
                datediff('day', b.LAST_PURCHASE_DATE, b.UPDATED_AT)
                - case
                    when b.PURCHASE_FREQUENCY = 0 then null
                    else 30 / b.PURCHASE_FREQUENCY
                  end,
                0
            ) as DAYS_SINCE_EXPECTED_LAST_PURCHASE_DATE
        from {database}.{schema}.CUSTOMERS c
        left join {database}.{schema}.PURCHASE_BEHAVIOR b
            on c.CUSTOMER_ID = b.CUSTOMER_ID
        """
    )

    return FeatureView(
        name="fv_customer_derived",
        entities=[customer_entity],
        feature_df=query,
        timestamp_col="BEHAVIOR_UPDATED_AT",
        refresh_freq="60 minute",
        desc="Derived customer features refreshed hourly.",
    ).attach_feature_desc(
        {
            "AVERAGE_ORDER_PER_MONTH": "Average number of orders per month.",
            "DAYS_SINCE_LAST_PURCHASE": "Days since last purchase.",
            "DAYS_SINCE_SIGNUP": "Days since signup.",
            "EXPECTED_DAYS_BETWEEN_PURCHASES": "Expected days between purchases.",
            "DAYS_SINCE_EXPECTED_LAST_PURCHASE_DATE": "Days since expected last purchase date.",
        }
    )
