import numpy as np
import pandas as pd
from src.etl.synth import COLUMNAS, escribir_demo, generar_panel_demo, main
from src.scraping.configuracion import cargar_config


def test_panel_demo_estructura():
    panel = generar_panel_demo(meses=48, fecha_fin="2025-12")
    total_bancos = len(cargar_config()["bancos"])
    assert list(panel.columns) == COLUMNAS
    assert len(panel) == total_bancos * 48
    assert panel["fecha"].min() == "2022-01"
    assert panel["fecha"].max() == "2025-12"
    assert panel["es_demo"].all()


def test_identidad_contable_y_positividad():
    panel = generar_panel_demo(meses=36)
    diferencia = panel["activo_total"] - (panel["pasivo_total"] + panel["patrimonio_total"])
    assert np.allclose(diferencia, 0.0, atol=0.02)
    for columna in COLUMNAS[2:-1]:
        assert (panel[columna] > 0).all(), columna


def test_utilidad_acumulada_se_reinicia_en_enero():
    panel = generar_panel_demo(meses=48, bancos=["bisa"]).sort_values("fecha")
    panel["anio"] = panel["fecha"].str[:4].astype(int)
    panel["mes"] = panel["fecha"].str[5:7].astype(int)
    for anio in panel["anio"].unique()[1:]:
        actual = panel[(panel["anio"] == anio) & (panel["mes"] == 1)]["utilidad_neta"].iloc[0]
        anterior = panel[panel["anio"] == anio - 1]["utilidad_neta"].iloc[-1]
        assert actual < anterior


def test_choque_de_mora_es_visible():
    panel = generar_panel_demo(meses=72, bancos=["bga"])
    panel["mora"] = panel["cartera_mora"] / panel["cartera_bruta"]
    antes = panel.iloc[40:46]["mora"].mean()
    durante = panel.iloc[50:55]["mora"].mean()
    assert durante > antes


def test_generacion_determinista():
    primero = generar_panel_demo(meses=24, semilla=7)
    segundo = generar_panel_demo(meses=24, semilla=7)
    pd.testing.assert_frame_equal(primero, segundo)


def test_escribir_demo_y_metadatos(tmp_path):
    salida = tmp_path / "demo" / "panel.csv"
    ruta, meta = escribir_demo(salida=salida, meses=24)
    assert ruta.exists() and meta.exists()
    assert "MODO DEMOSTRACIÓN" in meta.read_text(encoding="utf-8")
    assert "es_demo" in pd.read_csv(ruta).columns


def test_cli_exige_flag_demo(tmp_path, capsys):
    salida = tmp_path / "panel.csv"
    codigo = main(["--salida", str(salida)])
    assert codigo == 2
    assert not salida.exists()
    assert "--demo" in capsys.readouterr().err


def test_cli_con_demo(tmp_path):
    salida = tmp_path / "demo" / "panel.csv"
    assert main(["--demo", "--salida", str(salida), "--meses", "12"]) == 0
    assert salida.exists()
