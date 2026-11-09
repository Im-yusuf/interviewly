# Question patterns by technology category

Interviewers ask about a technology on your CV in two ways: **fundamentals** (do you understand the tool?) and **your usage** (did you really use it, and use it well?). Both are listed for each category below. Use these as templates: fill in the specific technology and, wherever possible, the user's own code.

Every skill in `profile.json` has one of these categories. If nothing fits, use `generic`.

---

## web-framework
FastAPI, Flask, Django, Express, NestJS, Spring Boot, Rails, ASP.NET, Gin…
- Lifecycle of a request: from the socket to your handler and back. Where do middleware, routing, validation and serialisation happen?
- Sync vs async handlers: what runs where, and what blocks? (FastAPI: `def` runs in a threadpool, `async def` on the event loop.)
- Dependency injection or app context: how do you get a DB session or the current user into a handler? Its lifetime and cleanup?
- Validation and error handling: what happens on bad input? Status codes? A global error handler?
- Auth: how is a request authenticated, and where is it checked?
- **Comparisons:** X vs Y for this project (FastAPI vs Flask vs Django). When would you *not* use X?
- **Your usage:** "Show me the most complex endpoint. What makes it complex?" · "How did you structure the routers, and why?"
- **Gotchas:** blocking calls inside async code, N+1 queries, mutable default args, CORS, background work dying with the process.

## database
PostgreSQL, MySQL, SQLite, MongoDB, Redis, DynamoDB, Elasticsearch…
- Data model: show the tables or collections; why this schema? Normalisation vs denormalisation?
- Indexes: which exist, which queries they serve, and what an index costs.
- Transactions and isolation: where do you need them? What anomaly would you see without them?
- Concurrency: two writers updating the same row; optimistic vs pessimistic locking.
- Migrations: how is the schema changed safely in production?
- Scale: read replicas, connection pooling, partitioning, caching layers.
- **Comparisons:** SQL vs NoSQL for this data. Why Postgres and not SQLite (or the other way round)?
- **Your usage:** "What's the slowest query in your app, and how would you find out?"
- **Gotchas:** a CV that says Postgres when the code uses SQLite; missing indexes on foreign keys; storing money as floats.

## orm-data-access
SQLAlchemy, Django ORM, Prisma, TypeORM, Hibernate, Entity Framework…
- Session or unit-of-work lifecycle: who opens it, commits it, closes it?
- Lazy vs eager loading; the N+1 problem and how to spot it.
- When would you drop down to raw SQL?
- Sync vs async engines.
- **Your usage:** "Walk me through what SQL your ORM emits for this endpoint."

## async-concurrency
asyncio, threads, multiprocessing, goroutines, Celery, worker pools…
- Concurrency vs parallelism. I/O-bound vs CPU-bound work, and which tool fits each.
- The GIL (Python): what it blocks, what it doesn't.
- Race conditions you have seen or prevented; locks, queues, idempotency.
- Back-pressure: what happens when work arrives faster than you can process it?
- **Your usage:** "Why a ThreadPoolExecutor here and not processes or asyncio?"

## messaging-queues
Kafka, RabbitMQ, SQS, Redis queues, Celery, Pub/Sub…
- Delivery guarantees (at-most-once / at-least-once / exactly-once) and what you did about duplicates.
- Retries, dead-letter queues, poison messages.
- Ordering and partitioning.
- **Comparisons:** a queue vs in-process background tasks vs cron.
- **Your usage:** "What happens to a job if the worker crashes halfway through?"

## infra-devops
Docker, Kubernetes, CI/CD (GitHub Actions, GitLab CI), Terraform, Nginx, Linux…
- Docker: image vs container, layers and caching, multi-stage builds, why your Dockerfile is ordered the way it is.
- Config and secrets: how they get into the container; what *never* goes in the image.
- CI/CD: what runs on each push? What blocks a deploy? How do you roll back?
- Kubernetes (if claimed): pods, deployments, services, probes, resource limits.
- Observability: logs, metrics, traces; how you'd debug a production 500.
- **Your usage:** "Walk me through your Dockerfile line by line." · "What does your CI do if the tests fail?"
- **Gotchas:** running as root, `latest` tags, secrets committed to the repo, no health checks.

## cloud
AWS, GCP, Azure, Vercel, Heroku, Cloudflare…
- Which services, and why those over the alternatives?
- IAM and least privilege: what can your app's role do?
- Cost: what's the most expensive part, and how would you cut it?
- Regions, availability and failure.
- **Your usage:** "Draw how a request flows through your AWS setup."
- **Gotchas:** claiming "AWS" for a single S3 upload; public buckets; hard-coded keys.

## cli-media-tools
FFmpeg, ImageMagick, OpenCV pipelines, GStreamer, yt-dlp, Pandoc…
- Explain the command you actually ran, flag by flag (`-ss`, `-i`, `-c:v`, `-crf`, `-preset`, `-map`, `-vf`, `-an`).
- Container vs codec (MP4 vs H.264); remuxing (`-c copy`) vs transcoding, and when each is possible.
- Seeking: input seeking (`-ss` before `-i`) vs output seeking, and the accuracy vs speed trade-off. Keyframes and GOPs.
- Quality vs size vs speed: CRF vs bitrate, presets, hardware encoders (NVENC, VideoToolbox, QSV).
- Filters and filter graphs; probing with `ffprobe`.
- Running it from code: subprocess vs bindings, parsing output, timeouts, error handling, temporary files.
- Scale: running many jobs at once, CPU limits, a queue of jobs, idempotency.
- **Your usage:** "Show me the exact ffmpeg command your code builds for a 30-second clip. Why each flag?" · "What happens with a corrupt input file?"
- **Gotchas:** `-c copy` cuts snapping to keyframes, variable frame rate, audio drifting out of sync, shell injection through file names.

## ml-ai
PyTorch, TensorFlow, scikit-learn, Hugging Face, LLM APIs, LangChain, RAG, pandas…
- The problem framing: what's the input, output and metric? Why that metric?
- Data: where it came from, how it was split, leakage you avoided.
- Model choice and baselines: what did you compare against?
- Training and evaluation details: overfitting, class imbalance, hyperparameters.
- LLM apps: prompting, retrieval, evaluation, cost and latency, hallucinations.
- Deployment and monitoring: drift, latency, cost.
- **Your usage:** "What was your baseline, and how much better was your model?"

## data-engineering
Airflow, dbt, Spark, ETL pipelines, data warehouses (BigQuery, Snowflake)…
- Batch vs streaming; idempotent, re-runnable jobs; backfills.
- Data quality checks, schema evolution.
- Partitioning and file formats (Parquet vs CSV).
- **Your usage:** "What happens if yesterday's job ran twice?"

## frontend
React, Vue, Angular, Next.js, Svelte, TypeScript, CSS, state management…
- Rendering: how does the framework decide what to re-render? Keys, memoisation.
- State: local vs global vs server state; why your choice of library.
- Data fetching: loading and error states, caching, race conditions.
- SSR vs CSR vs static generation, and why your project uses which.
- Performance and accessibility basics.
- **Your usage:** "Which component was the hardest to build, and why?"

## mobile
iOS (Swift, SwiftUI), Android (Kotlin, Compose), React Native, Flutter…
- App lifecycle, threading (main thread vs background).
- State and navigation architecture.
- Offline support, persistence, syncing.
- Releases: signing, store review, staged rollout.

## language
Python, JavaScript/TypeScript, Java, Go, Rust, C++, C#…
- Core semantics they'd expect at the level: mutability, references vs values, scoping, closures.
- Memory model: garbage collection, ownership (Rust), pointers.
- Error handling idioms.
- Concurrency model of the language.
- Typing: static vs dynamic; how you use types in your project.
- Python favourites: generators, decorators, context managers, the GIL, `is` vs `==`, mutable defaults.

## testing
pytest, Jest, JUnit, Cypress, Playwright…
- What's tested, what isn't, and why.
- Unit vs integration vs end-to-end; mocks, and when they hurt.
- How do you test code that calls an external service or a DB?
- **Your usage:** "What bug would your tests *not* catch?"
- **Gotchas:** a CV that says "tested" when the repo has one test.

## security-auth
OAuth, JWT, sessions, API keys, hashing, OWASP…
- Authentication vs authorisation, and where each is enforced in your code.
- Token storage and expiry; refresh tokens; revocation.
- Password hashing (bcrypt or argon2, never plain SHA).
- Injection, XSS, CSRF, SSRF: which apply to your app?
- Secrets management.

## ai-assisted
How the candidate worked with AI coding assistants. Ask it about projects whose dossier's **How it was built** shows a large AI share; it's fair to ask anyone. A good answer is specific and honest: what they decided, what they checked, where the AI was wrong.
- How did you use AI on this project? Which parts did you write yourself?
- Tell me about a time the AI's code was wrong. How did you notice, and what did you do?
- How do you check code an assistant wrote before you ship it?
- Pick one AI-written part. Walk me through what it does, line by line.
- Would you build it the same way without the assistant? What would you do differently?

## generic
Any technology without a better category.
- What is it, and what problem does it solve?
- Why did you choose it over the alternatives?
- What's one thing about it that surprised you or caused a bug?
- What are its limits, and when would you not use it?
- Walk me through exactly where and how you used it.

---

## Behavioral questions (for behavioral mode and `/interviewly:stories`)

| Category | Typical questions |
|---|---|
| challenge | "Tell me about the hardest technical problem you've solved." · "…a bug that took days to find." |
| failure | "Tell me about a time something you built failed or broke." · "…a mistake you made." |
| conflict | "Tell me about a disagreement with a teammate or a reviewer." |
| ownership | "Tell me about something you did that nobody asked you to." |
| impact | "What's the most impactful thing you've built? How do you know?" |
| learning | "Tell me about a time you had to learn something fast." |
| trade-off | "Tell me about a time you had to cut scope or ship under a deadline." |
| leadership | "Tell me about a time you mentored someone or led a piece of work." |
| feedback | "Tell me about critical feedback you got, and what you did with it." |
| motivation | "Why this company?" · "Why are you leaving your current role?" · "Where do you want to be in 3 years?" |
| ai-usage | "How do you use AI coding tools?" · "How much of this project did you write yourself?" · "Tell me about a time an AI suggestion was wrong." |
