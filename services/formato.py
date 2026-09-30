"""Formato de cifras en español (Ecuador): 1.234,56.

Vivía dentro del módulo de casos de los libros; al retirar ese módulo se trae aquí, porque
lo usan los filtros de plantilla `num_ec` y `money_ec` de toda la aplicación.
"""


def formato_es_ec(valor, decimales=2):
    """Normaliza la visualización de cifras al formato `es-EC`: 1.234,56.

    No altera el valor: solo cambia la representación (punto de miles, coma decimal).
    """
    try:
        numero = float(valor or 0)
    except (TypeError, ValueError):
        return str(valor)
    texto = ("{:,.%df}" % int(decimales)).format(numero)
    return texto.replace(",", "\u00a0").replace(".", ",").replace("\u00a0", ".")
