# Pre-database termination

When a V2 campaign terminates before its SQLite database is created, the
runner writes an identity-bound read-only artifact with:

```yaml
validation_status: NOT_APPLICABLE_DATABASE_NOT_CREATED
database_exists: false
mutating_api_used: false
```

This explains the absence of database validation without fabricating a
database or replacing the earlier startup failure.
