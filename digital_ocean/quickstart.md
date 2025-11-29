# Quickstart: Digital Ocean API Scripts

## Prerequisites
- Digital Ocean account
- API token (`DO_API_TOKEN`)
- Node.js 18+ and/or Bash (matching project requirements)
- Docker image to deploy

## Setup
1. Add your Digital Ocean API token to `.env`:
   ```
   DO_API_TOKEN=your_token_here
   DO_REGION=nyc3
   DO_IMAGE=your_image_name
   DO_APP_NAME=your_app_name
   ```
2. Document all variables in `.env.example`.
3. Install dependencies if using Node.js scripts:
   ```bash
   cd digital_ocean
   npm install
   ```

## Usage
- To launch a container/app:
  ```bash
  ./digital_ocean/launch_container.sh
  # or
  node digital_ocean/launch_container.js
  ```
- To check status:
  ```bash
  ./digital_ocean/status.sh
  # or
  node digital_ocean/status.js
  ```
- To teardown:
  ```bash
  ./digital_ocean/teardown.sh
  # or
  node digital_ocean/teardown.js
  ```

## Documentation
- See `README.md` and script comments for details.
- Reference [Digital Ocean API Docs](https://docs.digitalocean.com/reference/api/api-reference/).
