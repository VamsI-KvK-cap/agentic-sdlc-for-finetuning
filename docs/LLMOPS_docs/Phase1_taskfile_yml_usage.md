Taskfile: we need one for local one for docker
Good question — yes, you need both. Think of it this way:

- **Local tasks** — for day-to-day development when you're iterating fast, no Docker overhead
- **Docker tasks** — for running the full stack, testing production-like behaviour, Phase 2+ work

I'll keep all existing local tasks and add a `docker:` namespace below them.All local tasks are preserved unchanged. Here's a summary of what was added:

**Docker tasks added (`docker:` namespace):**

| Category | Tasks |
|---|---|
| Lifecycle | `docker:up`, `docker:up:d`, `docker:start`, `docker:stop`, `docker:down`, `docker:restart` |
| Building | `docker:build`, `docker:build:api`, `docker:build:ui` |
| Database | `docker:db:migrate`, `docker:db:rollback`, `docker:db:clean`, `docker:db:reset`, `docker:db:shell` |
| Logs | `docker:logs`, `docker:logs:api`, `docker:logs:ui`, `docker:logs:db`, `docker:logs:worker` |
| Shell | `docker:shell:api`, `docker:shell:ui`, `docker:shell:db` |
| Status | `docker:ps`, `docker:stats` |
| Cleanup | `docker:clean:output`, `docker:clean:all`, `docker:prune` |

**The most used commands day-to-day will be:**
```bash
task docker:up:d          # start everything in background
task docker:db:migrate    # run migrations after first start
task docker:logs:api      # watch api logs
task docker:shell:api     # debug inside the container
task docker:stop          # shut it all down
```