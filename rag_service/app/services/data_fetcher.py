from google.cloud import bigquery

client = bigquery.Client(project="physionet-data")
query = """
SELECT subject_id, gender, anchor_age
FROM `physionet-data.mimiciv_3_1_hosp.patients`
LIMIT 5
"""

query_job = client.query(query)
results = query_job.result()

for row in results:
    print(row.subject_id, row.gender, row.anchor_age)