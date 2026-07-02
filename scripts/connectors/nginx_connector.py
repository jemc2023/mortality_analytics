from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone

import requests
from pyspark.sql import DataFrame, functions as F, types as T


BASE_URL_ENV = "WHO_MORTALITY_BASE_URL"
DEFAULT_BASE_URL = "https://q7k0jp9j-8000.use2.devtunnels.ms/"
DBFS_STAGING_DIR = "dbfs:/tmp/who_mortality"
TARGET_SCHEMA = "sandbox"

SOURCE_SYSTEM = "WHO Mortality Database"
COUNTRY_CODE = "GTM"
COUNTRY_NAME = "Guatemala"
REGION_CODE = "CSA"
REGION_NAME = "Central and South America"

LOW_COUNT_THRESHOLD = 5
SUPPRESS_LOW_COUNTS = False
MIN_REASONABLE_YEAR = 1900
MAX_REASONABLE_YEAR = datetime.now(timezone.utc).year + 1
MAX_REASONABLE_COUNT = 1_000_000_000

INDICATOR_HEADER_PREFIX = (
    "Indicator Code,Indicator Name,Year,Sex,Age group code,Age Group,Number,"
    "Percentage of cause-specific deaths out of total deaths"
)
POPULATION_HEADER_PREFIX = "Year,Age group code,Age group,Sex,Population"

WHO_AGE_GROUP_CODE_MAP = {
    "age_all": "all",
    "age00": "0",
    "age01_04": "1-4",
    "age05_09": "5-9",
    "age10_14": "10-14",
    "age15_19": "15-19",
    "age20_24": "20-24",
    "age25_29": "25-29",
    "age30_34": "30-34",
    "age35_39": "35-39",
    "age40_44": "40-44",
    "age45_49": "45-49",
    "age50_54": "50-54",
    "age55_59": "55-59",
    "age60_64": "60-64",
    "age65_69": "65-69",
    "age70_74": "70-74",
    "age75_79": "75-79",
    "age80_84": "80-84",
    "age85_over": "85+",
    "age55_74": "55-74",
    "age75_over": "75+",
}

WHO_AGE_GROUP_LABEL_MAP = {
    "all": "all",
    "[all]": "all",
    "0": "0",
    "[0]": "0",
    "1-4": "1-4",
    "[1-4]": "1-4",
    "5-9": "5-9",
    "[5-9]": "5-9",
    "10-14": "10-14",
    "[10-14]": "10-14",
    "15-19": "15-19",
    "[15-19]": "15-19",
    "20-24": "20-24",
    "[20-24]": "20-24",
    "25-29": "25-29",
    "[25-29]": "25-29",
    "30-34": "30-34",
    "[30-34]": "30-34",
    "35-39": "35-39",
    "[35-39]": "35-39",
    "40-44": "40-44",
    "[40-44]": "40-44",
    "45-49": "45-49",
    "[45-49]": "45-49",
    "50-54": "50-54",
    "[50-54]": "50-54",
    "55-59": "55-59",
    "[55-59]": "55-59",
    "60-64": "60-64",
    "[60-64]": "60-64",
    "65-69": "65-69",
    "[65-69]": "65-69",
    "70-74": "70-74",
    "[70-74]": "70-74",
    "75-79": "75-79",
    "[75-79]": "75-79",
    "80-84": "80-84",
    "[80-84]": "80-84",
    "85+": "85+",
    "[85+]": "85+",
    "55-74": "55-74",
    "[55-74]": "55-74",
    "75+": "75+",
    "[75+]": "75+",
}

SEX_MAP = {
    "both": "all",
    "bothsexes": "all",
    "male": "male",
    "males": "male",
    "female": "female",
    "females": "female",
    "all": "all",
    "unknown": "unknown",
}


@dataclass(frozen=True)
class SourceSpec:
    file_name: str
    remote_path: str
    header_prefix: str
    target_table: str
    table_kind: str
    source_kind: str


SOURCE_SPECS = (
    SourceSpec("deaths_by_age_group_gtm.csv", "deaths_by_age_group_gtm.csv", INDICATOR_HEADER_PREFIX, "sandbox.raw_who_mortality_deaths_by_age_group_gtm", "deaths_by_age_group", "indicator"),
    SourceSpec("population_distribution_gtm.csv", "population_distribution_gtm.csv", POPULATION_HEADER_PREFIX, "sandbox.raw_who_mortality_population_distribution_gtm", "population_distribution", "population"),
    SourceSpec("overview_causes_gtm.csv", "overview_causes_gtm.csv", INDICATOR_HEADER_PREFIX, "sandbox.raw_who_mortality_overview_causes_gtm", "overview_causes", "indicator"),
    SourceSpec("detailed_causes_gtm.csv", "detailed_causes_gtm.csv", INDICATOR_HEADER_PREFIX, "sandbox.raw_who_mortality_detailed_causes_gtm", "detailed_causes", "indicator"),
)


def snake_case(value: str) -> str:
    text = re.sub(r"[^0-9A-Za-z]+", "_", value.strip())
    return re.sub(r"_+", "_", text).strip("_").lower()


def normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).replace("\ufeff", "").strip().strip('"')
    text = re.sub(r"\s+", " ", text)
    return text or None


def source_url(base_url: str, remote_path: str) -> str:
    return f"{base_url.rstrip('/')}/{remote_path.lstrip('/')}"


def dbfs_path(file_name: str) -> str:
    return f"{DBFS_STAGING_DIR}/{file_name}"


def fetch_text(url: str) -> str:
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    return response.text


def split_metadata_and_csv(raw_text: str, header_prefix: str) -> tuple[dict[str, str], str]:
    lines = [line.rstrip("\r") for line in raw_text.splitlines() if normalize_text(line)]
    header_idx = next(i for i, line in enumerate(lines) if normalize_text(line).lower().startswith(header_prefix.lower()))

    metadata: dict[str, str] = {}
    for line in lines[:header_idx]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key_norm = snake_case(key)
        value_norm = normalize_text(value)
        if key_norm in {"region_code", "region_name", "country_code", "country_name", "export_date", "source_location"} and value_norm:
            metadata[key_norm] = value_norm

    cleaned_csv = "\n".join(line.rstrip(",") for line in lines[header_idx:])
    return metadata, cleaned_csv


def write_dbfs_text(path: str, text: str) -> None:
    dbutils.fs.mkdirs(path.rsplit("/", 1)[0])
    dbutils.fs.put(path, text, overwrite=True)


def read_csv(path: str) -> DataFrame:
    return (
        spark.read.format("csv")
        .option("header", "true")
        .option("inferSchema", "true")
        .option("mode", "PERMISSIVE")
        .option("quote", '"')
        .option("escape", '"')
        .load(path)
    )


def normalize_column_names(df: DataFrame) -> DataFrame:
    return df.toDF(*[snake_case(column) for column in df.columns])


def normalize_string_columns(df: DataFrame) -> DataFrame:
    result = df
    for field in df.schema.fields:
        if isinstance(field.dataType, T.StringType):
            result = result.withColumn(
                field.name,
                F.when(
                    F.col(field.name).isNull() | (F.length(F.trim(F.col(field.name))) == 0),
                    F.lit(None).cast("string"),
                ).otherwise(F.regexp_replace(F.trim(F.col(field.name)), r"\s+", " ")),
            )
    return result


def map_values(df: DataFrame, column_name: str, mapping: dict[str, str]) -> DataFrame:
    expr = F.create_map(*[item for pair in mapping.items() for item in (F.lit(pair[0]), F.lit(pair[1]))])
    return df.withColumn(column_name, F.coalesce(F.element_at(expr, F.col(column_name)), F.col(column_name)))


def sanitize_year(df: DataFrame) -> DataFrame:
    year = F.col("year").cast("int")
    return df.withColumn("year", F.when((year >= MIN_REASONABLE_YEAR) & (year <= MAX_REASONABLE_YEAR), year).otherwise(F.lit(None).cast("int")))


def sanitize_non_negative(df: DataFrame, column_name: str, max_value: float = MAX_REASONABLE_COUNT) -> DataFrame:
    value = F.col(column_name).cast("double")
    return df.withColumn(column_name, F.when(value.isNull(), F.lit(None).cast("double")).when((value < 0) | (value > max_value), F.lit(None).cast("double")).otherwise(value))


def sanitize_percentage(df: DataFrame, column_name: str) -> DataFrame:
    value = F.col(column_name).cast("double")
    return df.withColumn(column_name, F.when(value.isNull(), F.lit(None).cast("double")).when((value < 0) | (value > 100), F.lit(None).cast("double")).otherwise(value))


def sanitize_rate(df: DataFrame, column_name: str) -> DataFrame:
    value = F.col(column_name).cast("double")
    return df.withColumn(column_name, F.when(value.isNull(), F.lit(None).cast("double")).when(value < 0, F.lit(None).cast("double")).otherwise(value))


def harmonize_sex(df: DataFrame) -> DataFrame:
    result = df.withColumn("sex", F.lower(F.trim(F.col("sex"))))
    result = map_values(result, "sex", SEX_MAP)
    return result.withColumn("sex", F.when(F.col("sex").isNull(), F.lit("unknown")).otherwise(F.col("sex")))


def harmonize_age_fields(df: DataFrame) -> DataFrame:
    result = df.withColumn("age_group_code", F.lower(F.trim(F.col("age_group_code"))))
    result = result.withColumn("age_group", F.lower(F.trim(F.col("age_group"))))
    result = map_values(result, "age_group_code", WHO_AGE_GROUP_CODE_MAP)
    result = map_values(result, "age_group", WHO_AGE_GROUP_LABEL_MAP)
    result = result.withColumn("age_group_code", F.when(F.col("age_group_code").isNull(), F.lit("unknown")).otherwise(F.col("age_group_code")))
    return result.withColumn("age_group", F.when(F.col("age_group").isNull(), F.col("age_group_code")).otherwise(F.col("age_group")))


def normalize_icd10_like(value: str | None) -> str | None:
    text = normalize_text(value)
    return text.upper().replace(" ", "") if text else None


def add_metadata(df: DataFrame, metadata: dict[str, str], spec: SourceSpec, base_url: str) -> DataFrame:
    export_date_raw = metadata.get("export_date")
    export_ts = F.to_timestamp(F.lit(export_date_raw), "M/d/yyyy h:mm:ss a") if export_date_raw else F.lit(None).cast("timestamp")
    return (
        df.withColumn("source_system", F.lit(SOURCE_SYSTEM))
        .withColumn("country_code", F.lit(metadata.get("country_code", COUNTRY_CODE)))
        .withColumn("country_name", F.lit(metadata.get("country_name", COUNTRY_NAME)))
        .withColumn("region_code", F.lit(metadata.get("region_code", REGION_CODE)))
        .withColumn("region_name", F.lit(metadata.get("region_name", REGION_NAME)))
        .withColumn("source_export_date_raw", F.lit(export_date_raw))
        .withColumn("source_export_ts", export_ts)
        .withColumn("source_location", F.lit(metadata.get("source_location")))
        .withColumn("source_file", F.lit(spec.file_name))
        .withColumn("source_url", F.lit(source_url(base_url, spec.remote_path)))
        .withColumn("table_kind", F.lit(spec.table_kind))
        .withColumn("privacy_class", F.lit("aggregated_public"))
        .withColumn("ingestion_ts", F.current_timestamp())
    )


def record_hash(df: DataFrame, key_columns: list[str]) -> DataFrame:
    values = [F.coalesce(F.col(column).cast("string"), F.lit("")) for column in key_columns]
    return df.withColumn("record_hash", F.sha2(F.concat_ws("||", *values), 256))


def privacy_flags(df: DataFrame, count_column: str | None = None) -> DataFrame:
    result = df.withColumn("sensitive_cell_flag", F.lit(False))
    if count_column and count_column in result.columns:
        result = result.withColumn("sensitive_cell_flag", F.when(F.col(count_column).isNull(), F.lit(False)).otherwise(F.col(count_column) < LOW_COUNT_THRESHOLD))
        if SUPPRESS_LOW_COUNTS:
            result = result.withColumn(count_column, F.when(F.col(count_column) < LOW_COUNT_THRESHOLD, F.lit(None).cast("double")).otherwise(F.col(count_column)))
    return result


def deduplicate(df: DataFrame, key_columns: list[str]) -> DataFrame:
    return df.dropDuplicates(key_columns)


def finalize(df: DataFrame, columns: list[str]) -> DataFrame:
    return df.select(*[column for column in columns if column in df.columns])


def standardize_indicator_frame(df: DataFrame) -> DataFrame:
    result = df.withColumn("indicator_code", F.upper(F.trim(F.col("indicator_code"))))
    result = result.withColumn("indicator_name", F.regexp_replace(F.trim(F.col("indicator_name")), r"\s+", " "))
    result = result.withColumn("sex", F.when(F.col("sex") == "", F.lit(None).cast("string")).otherwise(F.col("sex")))
    result = harmonize_sex(result)
    result = result.withColumn("age_group_code", F.when(F.col("age_group_code") == "", F.lit(None).cast("string")).otherwise(F.col("age_group_code")))
    result = result.withColumn("age_group", F.when(F.col("age_group") == "", F.lit(None).cast("string")).otherwise(F.col("age_group")))
    result = harmonize_age_fields(result)
    result = sanitize_year(result)
    result = sanitize_non_negative(result, "number")
    result = sanitize_percentage(result, "percentage_of_cause_specific_deaths_out_of_total_deaths")
    result = sanitize_rate(result, "age_standardized_death_rate_per_100_000_standard_population")
    result = sanitize_rate(result, "death_rate_per_100_000_population")
    result = result.withColumn("who_indicator_code", F.col("indicator_code"))
    result = result.withColumn("icd10_code_standard", F.lit(None).cast("string"))
    result = result.withColumn("icd10_group", F.lower(F.regexp_replace(F.col("indicator_name"), r"[^a-zA-Z0-9]+", "_")))
    result = result.withColumn("icd10_group", F.regexp_replace(F.col("icd10_group"), r"_+", "_"))
    result = result.withColumn("icd10_group", F.regexp_replace(F.col("icd10_group"), r"^_|_$", ""))
    result = result.withColumn("icd10_group", F.when(F.col("icd10_group") == "", F.lit(None).cast("string")).otherwise(F.col("icd10_group")))
    result = privacy_flags(result, "number")
    result = record_hash(result, ["indicator_code", "year", "sex", "age_group_code", "age_group"])
    result = deduplicate(result, ["indicator_code", "year", "sex", "age_group_code", "age_group"])
    return finalize(result, [
        "indicator_code",
        "indicator_name",
        "who_indicator_code",
        "icd10_code_standard",
        "icd10_group",
        "year",
        "sex",
        "age_group_code",
        "age_group",
        "number",
        "percentage_of_cause_specific_deaths_out_of_total_deaths",
        "age_standardized_death_rate_per_100_000_standard_population",
        "death_rate_per_100_000_population",
        "record_hash",
        "sensitive_cell_flag",
    ])


def standardize_population_frame(df: DataFrame) -> DataFrame:
    result = df.withColumn("age_group_code", F.when(F.col("age_group_code") == "", F.lit(None).cast("string")).otherwise(F.col("age_group_code")))
    result = result.withColumn("age_group", F.when(F.col("age_group") == "", F.lit(None).cast("string")).otherwise(F.col("age_group")))
    result = result.withColumn("sex", F.when(F.col("sex") == "", F.lit(None).cast("string")).otherwise(F.col("sex")))
    result = harmonize_age_fields(result)
    result = harmonize_sex(result)
    result = sanitize_year(result)
    result = sanitize_non_negative(result, "population")
    result = result.withColumn("who_indicator_code", F.lit(None).cast("string"))
    result = result.withColumn("icd10_code_standard", F.lit(None).cast("string"))
    result = result.withColumn("icd10_group", F.lit(None).cast("string"))
    result = privacy_flags(result)
    result = record_hash(result, ["year", "sex", "age_group_code", "age_group"])
    result = deduplicate(result, ["year", "sex", "age_group_code", "age_group"])
    return finalize(result, [
        "year",
        "sex",
        "age_group_code",
        "age_group",
        "population",
        "record_hash",
        "sensitive_cell_flag",
    ])


def transform_frame(df: DataFrame, metadata: dict[str, str], spec: SourceSpec, base_url: str) -> DataFrame:
    result = normalize_string_columns(normalize_column_names(df))
    result = standardize_indicator_frame(result) if spec.source_kind == "indicator" else standardize_population_frame(result)
    result = add_metadata(result, metadata, spec, base_url)
    return finalize(result, [
        "source_system",
        "country_code",
        "country_name",
        "region_code",
        "region_name",
        "source_export_date_raw",
        "source_export_ts",
        "source_location",
        "source_file",
        "source_url",
        "table_kind",
        "privacy_class",
        "sensitive_cell_flag",
        "indicator_code",
        "indicator_name",
        "who_indicator_code",
        "icd10_code_standard",
        "icd10_group",
        "year",
        "sex",
        "age_group_code",
        "age_group",
        "number",
        "percentage_of_cause_specific_deaths_out_of_total_deaths",
        "age_standardized_death_rate_per_100_000_standard_population",
        "death_rate_per_100_000_population",
        "population",
        "record_hash",
        "ingestion_ts",
    ])


def write_delta_table(df: DataFrame, table_name: str) -> None:
    df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(table_name)


def get_base_url() -> str:
    return DEFAULT_BASE_URL.rstrip("/")


def ensure_target_schema() -> None:
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {TARGET_SCHEMA}")


def process_source(spec: SourceSpec, base_url: str) -> DataFrame:
    raw_text = fetch_text(source_url(base_url, spec.remote_path))
    metadata, cleaned_csv = split_metadata_and_csv(raw_text, spec.header_prefix)
    staging_path = dbfs_path(spec.file_name)
    write_dbfs_text(staging_path, cleaned_csv)
    return transform_frame(read_csv(staging_path), metadata, spec, base_url)


def main() -> None:
    ensure_target_schema()
    base_url = get_base_url()
    for spec in SOURCE_SPECS:
        write_delta_table(process_source(spec, base_url), spec.target_table)

#El que lo lea es gay
if __name__ == "__main__":
    main()
