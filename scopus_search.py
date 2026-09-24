"""Busca un DOI en la API oficial de Scopus sin exponer la clave en la URL."""

import argparse
import json
import os
import re
from getpass import getpass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

ENDPOINT = "https://api.elsevier.com/content/search/scopus"
DOI_PATTERN = re.compile(r"10\.\d{4,9}/[A-Za-z0-9._;:/-]+\Z")


class ScopusError(Exception):
    """Error de consulta apto para mostrar sin exponer credenciales."""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def get_api_key():
    key = os.environ.get("SCOPUS_API_KEY", "").strip()
    if not key:
        key = getpass("Pega tu clave API de Elsevier (no se mostrará): ").strip()
    if not key:
        raise ScopusError("Falta la clave API de Elsevier.")
    return key


def search_doi(doi, api_key, open_url=None):
    if not DOI_PATTERN.fullmatch(doi):
        raise ValueError("El DOI debe tener formato 10.xxxx/sufijo, sin espacios ni comillas.")
    if not api_key or "\n" in api_key or "\r" in api_key:
        raise ScopusError("La clave API no es válida.")

    url = ENDPOINT + "?" + urlencode({"query": f'DOI("{doi}")', "count": 1})
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


def main():
    parser = argparse.ArgumentParser(description="Busca un DOI en Scopus.")
    parser.add_argument("doi", help="Por ejemplo: 10.1145/3695988")
    args = parser.parse_args()
    try:
        entries = search_doi(args.doi, get_api_key())
    except (ScopusError, ValueError) as error:
        parser.exit(1, f"Error: {error}\n")
    if not entries:
        print("No se encontró ese DOI en la respuesta de Scopus.")
        return
    for entry in entries:
        print("Título:", entry.get("dc:title", "—"))
        print("DOI:", entry.get("prism:doi", "—"))
        print("Fuente:", entry.get("prism:publicationName", "—"))
        print("Fecha:", entry.get("prism:coverDate", "—"))
        print("Tipo:", entry.get("subtypeDescription", "—"))


if __name__ == "__main__":
    main()
