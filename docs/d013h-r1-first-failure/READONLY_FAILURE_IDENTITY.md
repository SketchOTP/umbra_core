# Read-only validation failure identity

If read-only validation encounters a database error, its failure artifact
retains the complete campaign identity, records `validation_status: FAIL`,
sets `mutating_api_used: false`, and includes the error. Publication can then
validate identity even when the read-only check itself failed.
