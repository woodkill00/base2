# Digital Ocean API Reference for Base2 Project

This document summarizes the major Digital Ocean API endpoints, options, and usage patterns relevant to automating container/app deployment and management for the Base2 project. It is intended as a working reference for all scripts and integrations in the `digital_ocean` folder.

---

## 1. Authentication
- **Personal Access Token**: Required for all API calls. Generate via [DigitalOcean dashboard](https://docs.digitalocean.com/reference/api/create-personal-access-token/).
- **Scopes**: Ensure token has sufficient scopes for Droplets, Apps, Registry, etc.
- **Header**: `Authorization: Bearer <DO_API_TOKEN>`

---

## 2. Droplets API
- **Create Droplet**: `POST /v2/droplets`
  - Params: `name`, `region`, `size`, `image`, `ssh_keys`, `backups`, `ipv6`, `user_data`, etc.
  - Use for launching VM-based containers if needed.
- **List Droplets**: `GET /v2/droplets`
- **Destroy Droplet**: `DELETE /v2/droplets/{id}`

---

## 3. Apps API
- **Create App**: `POST /v2/apps`
  - Params: `spec` (JSON describing app, services, image, env vars, region, etc.)
  - Use for deploying containerized apps directly from Docker images.
- **Get App Status**: `GET /v2/apps/{app_id}`
- **Destroy App**: `DELETE /v2/apps/{app_id}`

---

## 4. Container Registry API
- **Create Registry**: `POST /v2/registry`
- **List Images**: `GET /v2/registry/{registry_name}/repositories/{repository_name}/tags`
- **Delete Image**: `DELETE /v2/registry/{registry_name}/repositories/{repository_name}/tags/{tag}`
- Use for storing and retrieving Docker images for deployment.

---

## 5. Spaces API
- **S3-Compatible Storage**: Use for storing assets, backups, etc. via RESTful XML API or AWS S3 SDKs.
- Not required for basic container deployment, but useful for persistent storage.

---

## 6. OAuth API
- **User Authentication**: For third-party integrations or delegated access.
- Not required for direct automation scripts.

---

## 7. Metadata API
- **Droplet Metadata**: `GET http://169.254.169.254/metadata/v1.json` (from inside droplet)
- Use for self-discovery, environment introspection, etc.

---

## Usage Patterns for Base2
- **App Deployment**: Prefer Apps API for containerized deployments (matches Docker workflow).
- **Image Management**: Use Container Registry API to push/pull images before deployment.
- **Environment Variables**: Pass via app spec in Apps API.
- **Teardown**: Use DELETE endpoints to destroy resources when no longer needed.
- **Error Handling**: Check response codes and error messages; scripts must exit with clear errors.

---

## Best Practices
- Always validate required environment variables before API calls.
- Document all API usage and parameters in scripts.
- Use `.env` for secrets/config, `.env.example` for documentation.
- Update this reference as new endpoints/features are used.

---

## References
- [Digital Ocean API Docs](https://docs.digitalocean.com/reference/api/api-reference/)
- [Apps API](https://docs.digitalocean.com/reference/api/api-reference/#tag/Apps)
- [Droplets API](https://docs.digitalocean.com/reference/api/api-reference/#tag/Droplets)
- [Container Registry API](https://docs.digitalocean.com/reference/api/api-reference/#tag/Container-Registry)
- [Spaces API](https://docs.digitalocean.com/reference/api/spaces/)
- [Metadata API](https://docs.digitalocean.com/reference/api/metadata/)
