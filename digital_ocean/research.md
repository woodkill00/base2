# Research: Digital Ocean API Integration

## Decision
- Use Digital Ocean REST API to automate container deployment and management.
- Scripts will be written in Bash and/or Node.js for compatibility with existing project scripts.
- Store all Digital Ocean API scripts in `digital_ocean/` folder.

## Rationale
- REST API is well-documented and supports all required operations (droplet/container creation, management, etc.).
- Bash/Node.js aligns with current project tech stack and script conventions.
- Isolated folder ensures maintainability and separation of concerns.

## Alternatives Considered
- Terraform/Ansible: More complex, not required for direct API calls.
- Python scripts: Would add another language dependency.

## Key API Endpoints
- [Droplets](https://docs.digitalocean.com/reference/api/api-reference/#operation/create_droplet)
- [Container Registry](https://docs.digitalocean.com/reference/api/api-reference/#tag/Container-Registry)
- [Apps](https://docs.digitalocean.com/reference/api/api-reference/#tag/Apps)

## Environment Variables Needed
- `DO_API_TOKEN`: Digital Ocean API token (required)
- `DO_REGION`: Region for deployment (optional, defaults to `nyc3`)
- `DO_IMAGE`: Container image to deploy
- `DO_APP_NAME`: Name for the deployed app/container

## References
- [Digital Ocean API Docs](https://docs.digitalocean.com/reference/api/api-reference/)
- [Apps API](https://docs.digitalocean.com/reference/api/api-reference/#tag/Apps)
- [Droplets API](https://docs.digitalocean.com/reference/api/api-reference/#tag/Droplets)
- [Container Registry API](https://docs.digitalocean.com/reference/api/api-reference/#tag/Container-Registry)
- [Spaces API](https://docs.digitalocean.com/reference/api/spaces/)
- [Metadata API](https://docs.digitalocean.com/reference/api/metadata/)
- [PyDo Python Client](https://github.com/digitalocean/pydo)

## Using PyDo in Base2
- PyDo is the official Python client for Digital Ocean's API, supporting all major endpoints.
- **Authentication:**
  ```python
  import os
  from pydo import Client
  client = Client(token=os.getenv("DIGITALOCEAN_TOKEN"))
  ```
- **App/Container Deployment:**
  - Use `client.apps.create()` with a deployment spec to launch containers/apps.
  - Use `client.apps.list()`, `client.apps.get(app_id)`, and `client.apps.delete(app_id)` for lifecycle management.
- **Droplets:**
  - Use `client.droplets.create()` to launch VMs, and `client.droplets.list()`/`client.droplets.delete()` for management.
- **Container Registry:**
  - Use `client.registry.create()`, `client.registry.get()`, and `client.registry.delete()` for registry operations.
- **Best Practices:**
  - Always set your API token in the environment (`DIGITALOCEAN_TOKEN`).
  - Use integration tests with real resources for production validation.
  - Reference [PyDo examples](https://github.com/digitalocean/pydo/tree/main/examples) for advanced usage (custom endpoints, logging, pagination).
  - See [PyDo documentation](https://docs.digitalocean.com/reference/pydo/) for full API coverage.

## Next Steps
- Design data model for API requests/responses
- Write scripts for authentication, container launch, status, and teardown
- Document usage and error handling
