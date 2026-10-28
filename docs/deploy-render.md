# Deploying Evidra on Render

Evidra runs as one Docker container: the FastAPI backend, the built React site, and SQLite on a persistent disk.
The repository's `render.yaml` describes that service, so Render can set it up from the repo.

## What you get

- One web service built from `infra/Dockerfile`, in the Singapore region.
- A 1 GB disk mounted at `/app/data` for the SQLite database. Reviews survive restarts and redeploys.
- A private site: visitors must type the shared **site password** (`AUTH_MODE=password`).
- The synthetic metformin demo review, loaded on the first start (`SEED_DEMO=true`). It is never
  loaded twice, so reviewers' work is not overwritten.
- An automatic redeploy on every push to `main`.

Persistent disks need a paid instance (`0.5c-512mb` in `render.yaml`). See Render's pricing page
for the current cost. The free plan has no disk. To use it, change `plan` to `free` and
delete the `disk` block. The site still works, but anything people add is wiped on every restart,
and the demo review is loaded again each time.

## First deploy

1. Sign in at https://dashboard.render.com with the GitHub account that can see this repository.
2. Choose **New** > **Blueprint**, then pick `balledasivavaraprasad-create/Evidra` and the `main` branch.
3. Render reads `render.yaml` and asks for **SITE_PASSWORD**. Enter at least 8 characters, and share it
   only with people who should see the demo. Render generates `SECRET_KEY` for you.
4. Click **Apply**. The first build takes a few minutes. The service is live once `/health/ready` passes.
5. Open the `.onrender.com` address Render shows. You should see the password screen.

## Changing things later

| To do this | Do this in the Render dashboard |
| --- | --- |
| Change the password | Service > Environment > `SITE_PASSWORD` > Save. Everyone is signed out. |
| Stop loading demo data | Set `SEED_DEMO` to `false`. Existing data is kept. |
| Turn off auto-deploy | Service > Settings > Auto-Deploy. |
| Use your own domain | Service > Settings > Custom Domains. |

## Running the same container elsewhere

```bash
export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
export SITE_PASSWORD='choose-a-password'
docker compose -f infra/docker-compose.yml up --build
# open http://localhost:8000
```
