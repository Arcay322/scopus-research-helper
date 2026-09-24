# Scopus Research Helper

Proyecto académico para ayudar a buscar, organizar y verificar referencias mediante la API oficial de Scopus de Elsevier.

## Configuración segura para Hermes

Ejecuta **una sola vez** en tu terminal:

```bash
python3 scopus_search.py --save-key
```

El programa pedirá la clave sin mostrar los caracteres y la guardará en `~/.hermes/scopus_api_key` con permisos `600`. No la pondrá en este repositorio ni en la línea de comandos. No compartas ese archivo; cualquier programa ejecutado con tu usuario de Linux, incluido Hermes, puede leerlo. Si el archivo ya existe, el programa se negará a sobrescribirlo.

## Consultar un DOI

Desde la carpeta del proyecto, ejecuta:

```bash
python3 scopus_search.py 10.1145/3695988
```

Si la clave aún no está guardada, el programa la pedirá en la terminal sin mostrar lo que escribes. No la incluyas en el comando: podría quedar en el historial del shell. El programa hace una consulta HTTPS con la clave en el encabezado `X-ELS-APIKey` y muestra los metadatos disponibles del DOI.

## Buscar varios artículos por tema

```bash
python3 scopus_search.py --query 'TITLE-ABS-KEY("large language models" AND "software engineering")' --limit 25 --csv outputs/llm-software-engineering.csv
```

`--limit` admite de 1 a 100 resultados y usa paginación cuando hace falta. Cada página consume una solicitud de la cuota asignada a tu clave. El CSV contiene título, autor, DOI, fuente, fecha, tipo y citas cuando Scopus devuelve esos campos. La carpeta `outputs/` se excluye de Git. El programa no sobrescribe un CSV existente: cambia el nombre para hacer otra búsqueda.

Para un proceso automatizado, el programa también admite `SCOPUS_API_KEY` como variable de entorno. No configures el valor en archivos versionados. La habilidad local `consultar-scopus` de Hermes usa este programa y no necesita ver ni imprimir la clave.

Si recibes `401`, revisa que la clave sea correcta. Un `403` suele indicar que faltan permisos o acceso institucional; el inicio de sesión en la web de Scopus no concede automáticamente esos permisos a la API. Un `429` indica un límite o cuota alcanzados. La cobertura depende de los permisos y cuotas asignados por Elsevier.

Ejecuta las pruebas locales con `python3 -m unittest discover -v` (no requieren clave ni hacen peticiones reales).

## Seguridad

- No subir claves API, credenciales universitarias ni cookies al repositorio.
- No pegar claves en el chat, en comandos con historial ni en URLs.
- Respetar las condiciones de uso de Elsevier y los límites de la API.

## Referencias

- [Scopus APIs](https://dev.elsevier.com/sc_apis.html)
- [Autenticación de la API](https://dev.elsevier.com/tecdoc_api_authentication.html)
- [Especificación de Scopus Search](https://dev.elsevier.com/documentation/SCOPUSSearchAPI.wadl)
- [Sintaxis de búsqueda de Scopus](https://dev.elsevier.com/sc_search_tips.html)
