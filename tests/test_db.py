"""Test de db.py — pytest tests/test_db.py -v"""
from qreaper import db


def test_guardar_y_listar(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    resultado = {
        "archivo": "correo_sospechoso.eml",
        "url": "https://correos-es.top/pago",
        "scoring": {"nota": 87, "veredicto": "PELIGRO", "motivos": ["dominio nuevo"]},
    }
    id_registro = db.guardar(resultado)
    assert id_registro == 1

    registros = db.listar()
    assert len(registros) == 1
    r = registros[0]
    assert r["archivo"] == "correo_sospechoso.eml"
    assert r["url"] == resultado["url"]
    assert r["veredicto"] == "PELIGRO"
    assert r["nota"] == 87
    assert r["motivos"] == ["dominio nuevo"]
