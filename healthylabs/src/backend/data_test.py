from google.cloud import bigquery

# Initialize the client. It automatically picks up your gcloud login!
# Use your actual billing project ID here.
client = bigquery.Client(project='healthylabs')

# Write your SQL query (targeting the MIMIC-III dataset from your previous screenshot)
query = """
    SELECT subject_id, admission_type, diagnosis 
    FROM `physionet-data.mimiciii_clinical.admissions` 
    LIMIT 5
"""

try:
    print("Sending query to BigQuery...")
    query_job = client.query(query)  # Make the API request
    
    # Iterate over the results
    for row in query_job:
        print(f"Subject: {row.subject_id}, Type: {row.admission_type}, Diagnosis: {row.diagnosis}")
        
    print("\nSuccess! Your backend is connected.")
except Exception as e:
    print(f"An error occurred: {e}")