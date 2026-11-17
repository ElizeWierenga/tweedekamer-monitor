SELECT
	id AS zaak_id,
	soort,
	onderwerp
FROM silver.zaak
LIMIT 40000;