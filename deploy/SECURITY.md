# Hosted execution

All hosted Lab, forward, and S&P scoring requires a local Docker daemon and a clean runtime image:

```sh
docker build -f deploy/Dockerfile.sandbox -t convexpi-sandbox:local .
export GRADER_DOCKER_IMAGE=convexpi-sandbox:local
python deploy/check_runtime.py
python deploy/grader_worker.py --once
```

The worker must be able to contact the daemon. Bind mounts are created by the daemon, so the worker's temporary directory must exist at the same path on the daemon host. Run the worker directly on that host, or configure a shared temporary directory at identical paths when containerizing the worker. Never mount the daemon socket into a strategy container. A Railway deployment without a reachable, correctly configured daemon will now fail closed; migrate the worker to a Docker-capable host before enabling public grading. CI builds and tests the runtime automatically; production scoring runs on the dedicated host.

For a containerized coordinator on a dedicated Docker host, `deploy/compose.yaml` supplies the shared-path configuration. Set `NEXT_PUBLIC_SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, and a private `MARKET_SEED` in the host environment; then run from the repository root:

```sh
export SANDBOX_TMPDIR=/var/lib/convexpi-sandbox
mkdir -p "$SANDBOX_TMPDIR"
docker compose -f deploy/compose.yaml --profile build build sandbox grader
docker compose -f deploy/compose.yaml run --rm grader python deploy/check_runtime.py
docker compose -f deploy/compose.yaml run --rm grader
```

Schedule the last command every five minutes on that host, preventing overlapping runs. The preflight uses only built-in sample strategies and never reads the submission queue. The worker also runs it before processing queued work, so a missing daemon, image, shared directory, or language runtime stops the job without failing students' submissions. The coordinator controls Docker and must remain trusted; use a dedicated host rather than sharing its daemon with unrelated sensitive workloads.

For Linux, install the repository at `/opt/convexpi-lab` and the environment file
at `/etc/convexpi/grader.env` (root-owned, mode `0600`; template in
`deploy/systemd/grader.env.example`). Install the `.service` and `.timer` files
from `deploy/systemd/` into `/etc/systemd/system/`. Build both images and pass
the preflight with that environment before enabling the timer:

```sh
sudo systemctl daemon-reload
sudo systemctl start convexpi-grader.service
sudo journalctl -u convexpi-grader.service --no-pager -n 40
sudo systemctl enable --now convexpi-grader.timer
```

The timer waits five minutes after the preceding batch finishes, so runs do not
overlap. Disable it with `sudo systemctl disable --now convexpi-grader.timer`.
Stop the service too if a batch is running. Keep the previous application commit
and built images for rollback; never roll back to execution without isolation.
Use a host dedicated to grading, patched Linux and Docker, SSH key authentication,
and no public application ports. Do not expose the Docker API over TCP.

The Railway schedule has been removed because the current Railway service has no
Docker daemon. Do not replace it with a production GitHub Actions queue: GitHub's
[additional product terms](https://docs.github.com/en/site-policy/github-terms/github-terms-for-additional-products-and-features#actions)
restrict application hosting. The existing scheduled scoring workflows should
remain disabled until moved to the dedicated host; CI remains appropriate for
testing the runtime.

The clean runtime contains language libraries and the SDK, with no deployment credentials baked into layers or image environment variables. Containers run without networking, capabilities, writable root filesystem, or host process access, as an unprivileged user, with bounded memory, CPU, processes, output, scratch space, and a wall-clock deadline. Cleanup forcibly removes the container and its descendants. There is no subprocess fallback.

Only strategy source and its protocol harness are mounted read-only. The worker sends one day's observable features/prices and current weights at a time (forecast models receive only history through that date). The child returns bounded, finite decisions; the worker validates shape and normalizes weights before computing all grades and returns. Submitted stdout can never supply an authoritative grade. Library users may still run their own trusted notebook strategies in-process; those APIs are not hosted security boundaries.

Run all tests with the image configured:

```sh
GRADER_DOCKER_IMAGE=convexpi-sandbox:local PYTHONPATH=src pytest -q
```

After rollout, existing grades and replication outputs are historical artifacts and may need regeneration. Apply the platform's `20261118000000_submission_authorization.sql` migration before deploying the corresponding submission route. The migration blocks new unauthorized membership inserts; it does not infer which existing privileged memberships are legitimate. Review existing memberships separately.
