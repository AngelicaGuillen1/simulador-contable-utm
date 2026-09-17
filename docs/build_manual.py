"""
Genera la versión HTML del Manual de Usuario a partir de la fuente única en Markdown.

Uso:
    python docs/build_manual.py

Produce:
    docs/MANUAL_DE_USUARIO.html  -> página autónoma, servida por el sistema en /manual
                                    y también abrible directamente para Guardar como PDF

La fuente de contenido es siempre docs/MANUAL_DE_USUARIO.md: el HTML no se edita a mano.
Se sirve como archivo estático (no como plantilla Jinja) para que el texto del manual
nunca se interprete como código de plantilla.
"""

import pathlib
import re

import markdown

RAIZ = pathlib.Path(__file__).resolve().parent.parent
FUENTE_MD = RAIZ / "docs" / "MANUAL_DE_USUARIO.md"
SALIDA_HTML = RAIZ / "docs" / "MANUAL_DE_USUARIO.html"

PLANTILLA_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Manual de Usuario - Simulador Integral de Sistema Contable</title>
<style>
  :root {{ --tinta:#1f2933; --suave:#52606d; --linea:#d9e2ec; --acento:#1d4ed8; --fondo:#f5f7fa; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--fondo); color:var(--tinta);
         font-family:"Segoe UI",Roboto,Helvetica,Arial,sans-serif; font-size:15px; line-height:1.65; }}
  .barra {{ position:sticky; top:0; z-index:20; background:#111827; color:#fff; padding:12px 20px;
            display:flex; flex-wrap:wrap; gap:12px; align-items:center; justify-content:space-between; }}
  .barra strong {{ font-size:15px; letter-spacing:.3px; }}
  .barra .acciones {{ display:flex; gap:10px; flex-wrap:wrap; }}
  .barra a, .barra button {{ background:#1d4ed8; color:#fff; border:0; border-radius:6px;
        padding:8px 14px; font-size:13.5px; font-weight:600; text-decoration:none; cursor:pointer; }}
  .barra a.sec {{ background:#374151; }}
  .barra a:hover, .barra button:hover {{ filter:brightness(1.15); }}
  main {{ max-width:1000px; margin:0 auto; padding:34px 28px 80px; background:#fff;
          box-shadow:0 1px 3px rgba(0,0,0,.08); }}
  h1 {{ font-size:30px; margin:0 0 4px; border-bottom:3px solid var(--acento); padding-bottom:10px; }}
  h2 {{ font-size:22px; margin:38px 0 10px; padding-bottom:6px; border-bottom:1px solid var(--linea); }}
  h3 {{ font-size:18px; margin:26px 0 8px; color:#111827; }}
  h4 {{ font-size:16px; margin:20px 0 6px; }}
  p, li {{ color:var(--tinta); }}
  a {{ color:var(--acento); }}
  code {{ background:#eef2f7; border:1px solid var(--linea); border-radius:4px; padding:1px 5px;
          font-family:Consolas,"Courier New",monospace; font-size:13px; }}
  pre {{ background:#0f172a; color:#e5edff; padding:14px 16px; border-radius:8px; overflow:auto;
         font-family:Consolas,"Courier New",monospace; font-size:12.8px; line-height:1.5; }}
  pre code {{ background:none; border:0; color:inherit; padding:0; }}
  table {{ border-collapse:collapse; width:100%; margin:14px 0 18px; font-size:14px; }}
  th, td {{ border:1px solid var(--linea); padding:8px 10px; text-align:left; vertical-align:top; }}
  th {{ background:#eef2f7; }}
  tbody tr:nth-child(even) {{ background:#fafcff; }}
  blockquote {{ margin:14px 0; padding:10px 16px; border-left:4px solid var(--acento);
                background:#f0f6ff; color:#243b53; }}
  hr {{ border:0; border-top:1px solid var(--linea); margin:30px 0; }}
  img {{ max-width:100%; }}
  @media print {{
    :root {{ --fondo:#fff; }}
    .barra {{ display:none; }}
    body {{ background:#fff; font-size:11pt; }}
    main {{ max-width:none; box-shadow:none; padding:0; }}
    h2, h3 {{ page-break-after:avoid; }}
    table, pre, blockquote {{ page-break-inside:avoid; }}
    a {{ color:#000; text-decoration:none; }}
    @page {{ margin:14mm; }}
  }}
</style>
</head>
<body>
<div class="barra">
  <strong>Manual de Usuario &middot; Simulador Integral de Sistema Contable</strong>
  <div class="acciones">
    <a href="/">Ir al sistema</a>
    <a class="sec" href="javascript:window.print()">Imprimir / Guardar PDF</a>
    <a class="sec" href="/manual/fuente">Descargar fuente Markdown</a>
  </div>
</div>
<main>
{cuerpo}
</main>
</body>
</html>
"""


def slug(texto: str) -> str:
    """Slug compatible con GitHub, para que el índice del manual enlace correctamente."""
    texto = texto.strip().lower()
    texto = re.sub(r"[^\w\s-]", "", texto, flags=re.UNICODE)
    texto = re.sub(r"[\s]+", "-", texto)
    return texto.strip("-")


def md_a_html(texto_md: str) -> str:
    md = markdown.Markdown(
        extensions=["tables", "fenced_code", "attr_list", "sane_lists", "toc"],
        extension_configs={"toc": {"slugify": lambda valor, separador: slug(valor)}},
        output_format="html5",
    )
    return md.convert(texto_md)


def main() -> None:
    if not FUENTE_MD.exists():
        raise SystemExit(f"No se encontro la fuente: {FUENTE_MD}")

    cuerpo = md_a_html(FUENTE_MD.read_text(encoding="utf-8"))
    pagina = PLANTILLA_HTML.format(cuerpo=cuerpo)
    SALIDA_HTML.write_text(pagina, encoding="utf-8")

    enlaces_internos = cuerpo.count('href="#')
    print("Manual generado correctamente:")
    print(f"  {SALIDA_HTML}  ({len(pagina):,} caracteres)")
    print(f"  Secciones de primer nivel: {cuerpo.count('<h2')} | Tablas: {cuerpo.count('<table>')} | Enlaces internos: {enlaces_internos}")


if __name__ == "__main__":
    main()
