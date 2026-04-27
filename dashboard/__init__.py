"""SPEACE Dashboard — GUI di monitoraggio su localhost.

Serve una pagina HTML + JSON API che legge lo stato reale di SPEACE dal
filesystem (state.json, benchmarks/results.json, epigenome.yaml, test counts,
mesh status). Single-file stdlib-only — non richiede Flask/Django.

Uso:
    python -m dashboard.speace_dashboard
    # poi apri http://localhost:8769
"""
__version__ = "1.0.0"
