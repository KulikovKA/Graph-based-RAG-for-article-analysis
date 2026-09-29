# License inventory

This inventory covers dependencies introduced by SKEL-001. Recheck and update it when
adding or upgrading a dependency; preserve upstream notices when distributing binaries.

| Component | Pinned version | License |
|---|---:|---|
| Python | >=3.11,<3.13 | PSF License |
| FastAPI | 0.115.12 | MIT |
| Pydantic | 2.11.3 | MIT |
| Uvicorn | 0.34.0 | BSD-3-Clause |
| Alembic | 1.20.0 | MIT |
| Psycopg | 3.3.6 | LGPL-3.0-only |
| SQLAlchemy | 2.0.54 | MIT |
| setuptools (build) | 75.8.0 | MIT |
| httpx (dev) | 0.28.1 | BSD-3-Clause |
| mypy (dev) | 1.15.0 | MIT |
| pytest (dev) | 8.3.5 | MIT |
| Ruff (dev) | 0.11.5 | MIT |
| React / React DOM | 19.0.0 | MIT |
| TypeScript | 5.8.3 | Apache-2.0 |
| Vite | 6.4.3 | MIT |
| `@vitejs/plugin-react` | 4.4.1 | MIT |
| `@types/react` | 19.0.10 | MIT |
| `@types/react-dom` | 19.0.4 | MIT |
| ESLint | 9.39.5 | MIT |
| `eslint-plugin-react` | 7.37.5 | MIT |
| `typescript-eslint` | 8.29.1 | MIT |

Transitive frontend packages are resolved by npm from the direct exact pins; `package-lock.json`
must be committed when npm is available so their resolved versions and integrity hashes are fixed.

This document inventories dependencies only; the repository does not declare a project source
license here. Third-party donor notices and pinned source inventory are recorded in
`docs/donors.lock.json` and the corresponding validation reports; do not copy donor code without
its notice.
