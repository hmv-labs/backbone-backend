# Backbone (Backend)

Backbone is a reusable Django foundation designed to accelerate development of modern web applications by providing a shared, modular backend architecture.

It standardizes common concerns such as authentication, API structure, caching, storage, websockets, messaging, etc across all projects built on top of it.

---

## Key Principles

- Composable: features are opt-in per project
- Modular design: each domain is isolated (auth, celery, storage, etc.)
- Environment-driven configuration

---

## Installation

```
pip install "backbone @ git+ssh://git@github.com/hmv-labs/backbone.git@main#subdirectory=backend"
```

With development extras

```
pip install "backbone[dev] @ git+ssh://git@github.com/hmv-labs/backbone.git@main#subdirectory=backend"
```

Local
```
pip install -e .
pip install -e ".[dev]"
```

## Project Integration
