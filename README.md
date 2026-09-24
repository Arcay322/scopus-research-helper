# Scopus Research Helper

Proyecto académico para ayudar a buscar, organizar y verificar referencias mediante la API oficial de Scopus de Elsevier.

## Primera prueba

Desde la carpeta del proyecto, ejecuta:

```bash
python3 scopus_search.py 10.1145/3695988
```

El programa pedirá la clave API en la terminal sin mostrar lo que escribes. Pégala allí y pulsa Enter. No la incluyas en el comando: podría quedar en el historial del shell. El programa hace una consulta HTTPS con la clave en el encabezado `X-ELS-APIKey` y muestra los metadatos disponibles del DOI.

Para un proceso automatizado, el programa también admite `SCOPUS_API_KEY` como variable de entorno. Configúrala en un almacén local de secretos o en el entorno del proceso, nunca en archivos versionados. La configuración de Hermes se hará después de comprobar que la API responde desde este equipo.

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
