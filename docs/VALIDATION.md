# AquaTwin AI v12 validation protocol and local test coverage

Run `python -m pytest -q` from the project root.

Automated coverage includes:

1. Water allocation cannot exceed demand or total supply.
2. Proportional allocation and sufficient-supply cases.
3. Crop demand responds to entered soil moisture; hydroponic top-up responds to reservoir level.
4. Pump runtime and energy values are calculated from nominal flow and rated power.
5. Zone configuration enforces unique IDs, supported systems/stages and numeric bounds.
6. Selected-day rain credit applies only to soil zones and is capped at estimated demand.
7. Farm 3D, Sankey and soil-profile Plotly objects can be generated and serialized.
8. SQLite configuration, plan and actual-delivery records persist in an isolated test database.

Manual acceptance checks still required on the target machine:

- Install the declared dependencies and start Streamlit locally.
- Navigate through all eight workspaces and verify responsive layout at the target display size.
- Rotate/zoom the 3D view, inspect every zone and check branch/zone allocations against planner table.
- Fetch Open-Meteo data with an internet connection, then test the manual fallback with network access disabled.
- Save a configuration and plan, restart the process and verify persistence.
- Record actual water delivery, check planned-versus-actual comparison, and export CSV/JSON files.
- Verify pump values against the installed pump's actual curve and electricity meter before using the estimates operationally.

Automated unit tests do not establish field accuracy, API availability at every location, hardware compatibility, or agronomic validity.
