# Data Model: Digital Ocean API Scripts

## Entities

### 1. API Credentials
- `DO_API_TOKEN`: string (required)
- Validation: Must be present in `.env` before any API call

### 2. Container/App Deployment
- `DO_APP_NAME`: string (required)
- `DO_IMAGE`: string (required)
- `DO_REGION`: string (optional, default: `nyc3`)
- Relationships: Deployment references image and region
- Validation: All required fields must be present and valid

### 3. Deployment State
- States: `pending`, `active`, `error`, `destroyed`
- Transitions: 
  - `pending` → `active` (on successful launch)
  - `pending` → `error` (on failure)
  - `active` → `destroyed` (on teardown)

## Validation Rules
- All required environment variables must be present before running scripts
- API responses must be checked for errors and status
- Scripts must exit with clear error messages if validation fails

## Relationships
- Each deployment is linked to a specific Digital Ocean account via API token
- Each deployment references a container image and region

