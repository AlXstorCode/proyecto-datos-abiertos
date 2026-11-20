import os
import requests
from dotenv import load_dotenv

load_dotenv()


def _parsear_limite(valor):
    if valor is None:
        return None
    texto = str(valor).strip().lower()
    if texto in ("", "none", "null", "sin_limite", "sin limite", "0", "-1"):
        return None
    return int(texto)


class APIClient:
    """Cliente encargado de consultar el dataset en datos.gov.co."""

    def __init__(self, resource_id=None, limite=None, tamano_pagina=5000, timeout=30):
        self.resource_id = (resource_id or os.getenv("API_RESOURCE_ID", "s5df-6cb7")).strip()
        limite_fuente = limite if limite is not None else os.getenv("API_LIMIT", "none")
        self.limite = _parsear_limite(limite_fuente)
        self.tamano_pagina = int(tamano_pagina)
        self.url = f"https://www.datos.gov.co/resource/{self.resource_id}.json"
        self.timeout = timeout

    def obtener_registros(self, limite=None):
        """Descarga registros paginando con $limit y $offset hasta completar."""
        max_total = _parsear_limite(limite) if limite is not None else self.limite
        todos = []
        offset = 0

        while True:
            paso = self.tamano_pagina
            if max_total is not None:
                restante = max_total - len(todos)
                if restante <= 0:
                    break
                paso = min(self.tamano_pagina, restante)

            respuesta = requests.get(
                self.url,
                params={"$limit": paso, "$offset": offset, "$order": "anno,trimestre,proveedor,proveedor_destino"},
                timeout=self.timeout,
            )
            respuesta.raise_for_status()

            datos = respuesta.json()
            if not isinstance(datos, list) or len(datos) == 0:
                break

            todos.extend(datos)
            if len(datos) < paso:
                break

            offset += len(datos)

        return todos