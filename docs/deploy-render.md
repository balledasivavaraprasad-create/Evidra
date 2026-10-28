# Deploying Evidra on Render

Evidra runs as one Docker container: the FastAPI backend and the built React site. Review data lives in Neon Postgres.
The repository's `render.yaml` describes that service, so Render can set it up from the repo.

## What you get

- One web service on Render's **free plan**, built from `infra/Dockerfile`, in the Singapore region. No card is needed.
- User accounts (`AUTH_MODE=accounts`): people sign up with an email and password, or with Google when `GOOGLE_CLIENT_ID` is set. Each person sees only their own reviews.
- Review data in **Neon Postgres** (`DATABASE_URL`, the pooled connection string), so it survives restarts, redeploys and wake-ups.
- An automatic redeploy on every push to `main`.

Free-plan limits to know:

- **Temporary disk.** The free filesystem is temporary, but reviews and accounts are stored in Neon, not on it.
  Only transient LangGraph checkpoints stay on local disk.
- **Sleep.** After 15 minutes without visitors the service sleeps. The next visit waits about a minute.
- **Monthly hours.** 750 free instance hours per workspace each month. A sleeping service uses none.

### Keeping local files permanently (paid)

Only needed if you want the local checkpoint files to survive restarts. Change `plan: free` to a paid plan
(for example `0.5c-512mb`) in `render.yaml` and add a `disk` mounted at `/app/data`. Render will ask for a card.
See Render's pricing page for current cost.

## First deploy

1. Sign in at https://dashboard.render.com with the GitHub account that can see this repository.
2. Choose **New** > **Blueprint**, then pick `balledasivavaraprasad-create/Evidra` and the `main` branch.
3. Render reads `render.yaml` and asks for **DATABASE_URL** (the Neon *pooled* connection string) and, optionally,
   **GOOGLE_CLIENT_ID**. Render generates `SECRET_KEY` for you. Migrations run when the container starts.
4. Click **Apply**. The first build takes a few minutes. The service is live once `/health/ready` passes.
5. Open the `.onrender.com` address Render shows. You should see the sign-in and sign-up screen.

## Changing things later

| To do this | Do this in the Render dashboard |
| --- | --- |
| Point at another database | Service > Environment > `DATABASE_URL` (Neon pooled string) > Save. |
| Turn Google sign-in on or off | Set or clear `GOOGLE_CLIENT_ID`. Email sign-up keeps working either way. |
| Rotate sessions | Change `SECRET_KEY`. Everyone is signed out. |
| Background job worker | `RUN_WORKER_IN_PROCESS=true` runs the worker daemon inside FastAPI's lifespan (requires `WORKERS=1`). Defaults to `true` in production. |
| Turn off auto-deploy | Service > Settings > Auto-Deploy. |
| Use your own domain | Service > Settings > Custom Domains. |

## Running the same container elsewhere

```bash
export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
export DATABASE_URL='postgresql://USER:PASSWORD@HOST/DB?sslmode=require'   # Neon pooled connection string
# export GOOGLE_CLIENT_ID='...apps.googleusercontent.com'                  # optional
docker compose -f infra/docker-compose.yml up --build
# open http://localhost:8000
```
