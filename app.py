from flask import Flask, flash, redirect, render_template, request, url_for
from api.api_client import APIClient
from models.datos_model import consultar_registros, sincronizar_si_es_necesario, obtener_resumen, guardar_registros

app = Flask(__name__)
app.secret_key = "cambiar-por-una-clave-local"


@app.route("/", methods=["GET"])
def inicio():
    try:
        cliente = APIClient()
        sincronizar_si_es_necesario(cliente, minimo_registros=100, limite_descarga=None)
    except Exception as e:
        flash(f"No se pudo completar la sincronización automática: {e}", "error")

    filtros = {
        "anno": request.args.get("anno", "").strip(),
        "trimestre": request.args.get("trimestre", "").strip(),
        "proveedor": request.args.get("proveedor", "").strip(),
        "proveedor_destino": request.args.get("proveedor_destino", "").strip(),
        "trafico_prepago": request.args.get("trafico_prepago", "").strip(),
        "trafico_pospago": request.args.get("trafico_pospago", "").strip(),
    }

    registros = consultar_registros(filtros)
    resumen = obtener_resumen()

    return render_template(
        "index.html",
        registros=registros,
        filtros=filtros,
        resumen=resumen,
    )


@app.route("/sincronizar", methods=["POST"])
def sincronizar():
    try:
        cliente = APIClient()
        datos = cliente.obtener_registros()
        nuevos = guardar_registros(datos)
        flash(f"Nuevos registros guardados: {nuevos}", "exito")
    except Exception as e:
        flash(f"No se pudo sincronizar: {e}", "error")
    return redirect(url_for('inicio'))


if __name__ == "__main__":
    app.run(debug=True)