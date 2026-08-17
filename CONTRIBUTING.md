# Contributing

Contributions are welcome through focused pull requests.

1. Create a branch from `main`.
2. Keep changes scoped and update documentation when behavior changes.
3. Run the relevant checks before opening a pull request:

   ```bash
   cd backend && pytest && ruff check .
   cd frontend && npm ci && npm run lint && npm run build
   ```

4. Do not commit `.env` files, API keys, real incident packets, or confidential
   operational data.

The hosted application is a public demo. Use only sample or sanitized data.
