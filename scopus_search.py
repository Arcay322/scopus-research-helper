"""Busca un DOI en la API oficial de Scopus sin exponer la clave en la URL."""

import argparse
import csv
import json
import os
import re
from getpass import getpass
from pathlib import Path
import stat
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

ENDPOINT = "https://api.elsevier.com/content/search/scopus"
DOI_PATTERN = re.compile(r"10\.\d{4,9}/[A-Za-z0-9._;:/-]+\Z")
KEY_FILE = Path.home() / ".hermes" / "scopus_api_key"


class ScopusError(Exception):
    """Error de consulta apto para mostrar sin exponer credenciales."""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def store_api_key(key, path=KEY_FILE):
    if not key or "\n" in key or "\r" in key:
        raise ScopusError("La clave API no es válida.")
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    except FileExistsError:
        raise ScopusError("Ya existe una clave guardada; no se sobrescribió.") from None
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(key + "\n")


def get_api_key():
    key = os.environ.get("SCOPUS_API_KEY", "").strip()
    if not key and KEY_FILE.exists():
        metadata = KEY_FILE.lstat()
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_mode & 0o077:
            raise ScopusError("El archivo de la clave debe ser regular y tener permisos 600.")
        key = KEY_FILE.read_text(encoding="utf-8").strip()
    if not key:
        key = getpass("Pega tu clave API de Elsevier (no se mostrará): ").strip()
    if not key:
        raise ScopusError("Falta la clave API de Elsevier.")
    return key


def search_doi(doi, api_key, open_url=None):
    if not DOI_PATTERN.fullmatch(doi):
        raise ValueError("El DOI debe tener formato 10.xxxx/sufijo, sin espacios ni comillas.")
    return search_query(f'DOI("{doi}")', api_key, count=1, open_url=open_url)


def search_query(query, api_key, count=10, start=0, open_url=None):
    if not query.strip() or len(query) > 1000:
        raise ValueError("La consulta debe tener entre 1 y 1000 caracteres.")
    if not 1 <= count <= 25 or start < 0:
        raise ValueError("count debe estar entre 1 y 25 y start no puede ser negativo.")
    if not api_key or "\n" in api_key or "\r" in api_key:
        raise ScopusError("La clave API no es válida.")

    url = ENDPOINT + "?" + urlencode({"query": query, "count": count, "start": start})
    request = Request(url, headers={"Accept": "application/json", "X-ELS-APIKey": api_key})
    if open_url is None:
        open_url = build_opener(NoRedirect()).open
    try:
        with open_url(request, timeout=15) as response:
            payload = json.load(response)
    except HTTPError as error:
        messages = {
            401: "Clave API ausente o inválida.",
            403: "La clave no tiene los permisos necesarios; revisa el acceso institucional.",
            429: "Cuota o límite de velocidad alcanzado.",
        }
        raise ScopusError(f"Scopus respondió {error.code}: {messages.get(error.code, 'consulta rechazada')}") from None
    except (URLError, TimeoutError):
        raise ScopusError("No se pudo conectar a la API de Scopus.") from None
    except (json.JSONDecodeError, UnicodeDecodeError, KeyError, TypeError):
        raise ScopusError("La API devolvió una respuesta inesperada.") from None

    results = payload.get("search-results")
    if not isinstance(results, dict) or not isinstance(results.get("entry", []), list):
        raise ScopusError("La API devolvió una respuesta inesperada.")
    return [item for item in results.get("entry", []) if isinstance(item, dict) and item.get("dc:title")]


def export_csv(entries, output):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    columns = {
        "dc:title": "titulo",
        "dc:creator": "autor",
        "prism:doi": "doi",
        "prism:publicationName": "fuente",
        "prism:coverDate": "fecha",
        "subtypeDescription": "tipo",
        "citedby-count": "citas",
    }

    def safe_cell(value):
        text = str(value or "")
        return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else text

    with output.open("x", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns.values()))
        writer.writeheader()
        for entry in entries:
            writer.writerow({label: safe_cell(entry.get(field)) for field, label in columns.items()})


def main():
    parser = argparse.ArgumentParser(description="Busca un DOI en Scopus.")
    parser.add_argument("doi", nargs="?", help="Por ejemplo: 10.1145/3695988")
    parser.add_argument("--save-key", action="store_true", help="Guarda la clave en un archivo privado para Hermes")
    parser.add_argument("--query", help="Consulta avanzada de Scopus, por ejemplo TITLE-ABS-KEY(software)")
    parser.add_argument("--limit", type=int, default=25, help="Máximo de resultados para --query (1-100)")
    parser.add_argument("--csv", type=Path, help="Guarda metadatos en un CSV nuevo; no sobrescribe archivos")
    args = parser.parse_args()
    if args.save_key:
        if args.doi or args.query or args.csv:
            parser.error("--save-key no se combina con búsquedas o exportación")
        try:
            store_api_key(getpass("Pega tu clave API (no se mostrará): ").strip())
        except ScopusError as error:
            parser.exit(1, f"Error: {error}\n")
        print("Clave guardada en un archivo privado (permisos 600).")
        return
    if bool(args.doi) == bool(args.query):
        parser.error("indica un DOI o --query, pero no ambos")
    if not 1 <= args.limit <= 100:
        parser.error("--limit debe estar entre 1 y 100")
    try:
        key = get_api_key()
        if args.query:
            entries = []
            while len(entries) < args.limit:
                count = min(25, args.limit - len(entries))
                page = search_query(args.query, key, count=count, start=len(entries))
                entries.extend(page)
                if len(page) < count:
                    break
        else:
            entries = search_doi(args.doi, key)
        if args.csv:
            export_csv(entries, args.csv)
    except (ScopusError, ValueError) as error:
        parser.exit(1, f"Error: {error}\n")
    except FileExistsError:
        parser.exit(1, "Error: el CSV ya existe; elige otro nombre para no sobrescribirlo.\n")
    if args.csv:
        print(f"Guardados {len(entries)} resultados en {args.csv}")
        return
    if not entries:
        print("No se encontraron resultados en la respuesta de Scopus.")
        return
    for entry in entries:
        print("Título:", entry.get("dc:title", "—"))
        print("DOI:", entry.get("prism:doi", "—"))
        print("Fuente:", entry.get("prism:publicationName", "—"))
        print("Fecha:", entry.get("prism:coverDate", "—"))
        print("Tipo:", entry.get("subtypeDescription", "—"))
        print()


if __name__ == "__main__":
    main()
