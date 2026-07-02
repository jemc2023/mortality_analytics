# WHO Mortality Nginx Server

Serve the WHO mortality CSVs locally through nginx on port `8000`.

## Start

```bash
docker compose -f scripts/nginx/docker-compose.yml up -d
```

## Verify

```bash
curl -I "http://localhost:8000/deaths_by_age_group_gtm.csv"
curl -I "http://localhost:8000/detailed_causes_gtm.csv"
```

## Databricks URL

Use the devtunnel URL for port `8000`:

`https://q7k0jp9j-8000.use2.devtunnels.ms/`

## Files served

- `deaths_by_age_group_gtm.csv`
- `population_distribution_gtm.csv`
- `overview_causes_gtm.csv`
- `detailed_causes_gtm.csv`
