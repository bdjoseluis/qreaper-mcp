"""Smoke test: comprueba que todo importa sin errores."""

def test_imports():
    from qreaper import decode, analisis_url, sandbox, scoring, informe, pipeline, cli
    assert decode and analisis_url and sandbox and scoring and informe and pipeline and cli
