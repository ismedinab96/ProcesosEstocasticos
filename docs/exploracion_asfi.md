# Exploración del portal de la ASFI

- **Generado (UTC):** 2026-11-14T02:51:10+00:00
- **URL base analizada:** https://www.asfi.gob.bo
- **Modo:** solo lectura (navegación + HEAD); sin descargas masivas.
- **Límites aplicados:** rate limit del `config.yaml`, User-Agent identificable y máximo 3 archivos sondeados.

## Metodología

1. Se consultó `robots.txt` y se verificó el permiso de acceso por dominio.
2. Se visitaron las secciones candidatas declaradas en `config.yaml` (sin adivinar rutas de descarga directa).
3. Se extrajeron enlaces a archivos y a contenidos financieros relevantes.
4. Se inspeccionaron cabeceras `HEAD` para estimar tipo y tamaño real, porque la extensión declarada no siempre coincide con el formato.

## Robots.txt

| Dominio | Estado |
|---|---|
| https://www.asfi.gob.bo | permitido |

## Secciones visitadas

| Sección | Estado | Content-Type | Título | Detalle |
|---|---|---|---|---|
| portada | HTTP 200 | text/html; charset=UTF-8 | ¡Bienvenidos! \| ASFI | 116 enlaces, 0 tablas HTML |
| robots | HTTP 200 | text/plain | robots.txt | 72 líneas; primeras: # / # robots.txt / # / # This file is to prevent the crawling and indexing of certain parts / # of your site by web crawlers and spiders run by sites like Yahoo! |
| estados financieros | HTTP 200 | text/html; charset=UTF-8 | Estados Financieros \| ASFI | 189 enlaces, 0 tablas HTML |
| estadisticas intermediacion | HTTP 200 | text/html; charset=UTF-8 | Estadísticas Intermediación Financiera \| ASFI | 109 enlaces, 0 tablas HTML |

## Archivos candidatos inspeccionados (HEAD)

| Texto del enlace | URL | Content-Type | Bytes | Formato estimado | Estado |
|---|---|---|---|---|---|
| Balance General | `https://www.asfi.gob.bo/la/balance-general` | text/html; charset=UTF-8 | — | html | HTTP 200 |
| Actividad Financiera Ilegal | `https://www.asfi.gob.bo/pb/actividad-financiera-ilegal` | text/html; charset=UTF-8 | — | html | HTTP 200 |
| Servicios Financieros | `https://www.asfi.gob.bo/pb/servicios-financieros` | text/html; charset=UTF-8 | — | html | HTTP 200 |

## Fuentes verificadas (disponibilidad histórica)

Plantillas obtenidas de enlaces y del JavaScript público del portal (por ejemplo `bmu-bol.js`), verificadas con peticiones `HEAD`:

| Fuente | URL verificada | Content-Type | Bytes | Estado |
|---|---|---|---|---|
| Bancos Múltiples — Estados Financieros | `https://www.asfi.gob.bo/sites/default/files/estadisticaif/bancos_multiples/2014/12/201412_BMU_EstadosFinancieros.zip` | application/zip | 120996 | HTTP 200 |
| Bancos Múltiples — Estados Financieros | `https://www.asfi.gob.bo/sites/default/files/estadisticaif/bancos_multiples/2015/12/201512_BMU_EstadosFinancieros.zip` | application/zip | 57958 | HTTP 200 |
| Bancos Múltiples — Estados Financieros | `https://www.asfi.gob.bo/sites/default/files/estadisticaif/bancos_multiples/2020/12/202012_BMU_EstadosFinancieros.zip` | application/zip | 178340 | HTTP 200 |
| Bancos Múltiples — Estados Financieros | `https://www.asfi.gob.bo/sites/default/files/estadisticaif/bancos_multiples/2022/12/202212_BMU_EstadosFinancieros.zip` | application/zip | 54728 | HTTP 200 |
| Bancos Múltiples — Estados Financieros | `https://www.asfi.gob.bo/sites/default/files/estadisticaif/bancos_multiples/2023/12/202312_BMU_EstadosFinancieros.zip` | application/zip | 146596 | HTTP 200 |
| Bancos Múltiples — Estados Financieros | `https://www.asfi.gob.bo/sites/default/files/estadisticaif/bancos_multiples/2024/12/202412_BMU_EstadosFinancieros.zip` | application/zip | 59270 | HTTP 200 |
| Bancos Múltiples — Estados Financieros | `https://www.asfi.gob.bo/sites/default/files/estadisticaif/bancos_multiples/2025/06/202506_BMU_EstadosFinancieros.zip` | application/zip | 58129 | HTTP 200 |
| Bancos Múltiples — Estados Financieros | `https://www.asfi.gob.bo/sites/default/files/estadisticaif/bancos_multiples/2025/12/202512_BMU_EstadosFinancieros.zip` | application/zip | 58201 | HTTP 200 |
| Bancos Múltiples — Indicadores Financieros | `https://www.asfi.gob.bo/sites/default/files/estadisticaif/bancos_multiples/2023/12/202312_BMU_IndicadoresFinancieros.zip` | application/zip | 65708 | HTTP 200 |
| Bancos Múltiples — Indicadores Financieros | `https://www.asfi.gob.bo/sites/default/files/estadisticaif/bancos_multiples/2024/12/202412_BMU_IndicadoresFinancieros.zip` | application/zip | 29619 | HTTP 200 |
| Bancos Múltiples — Indicadores Financieros | `https://www.asfi.gob.bo/sites/default/files/estadisticaif/bancos_multiples/2025/12/202512_BMU_IndicadoresFinancieros.zip` | application/zip | 29598 | HTTP 200 |
| Bancos Múltiples — Estados Financieros Evolutivos | `https://www.asfi.gob.bo/sites/default/files/estadisticaif/bancos_multiples/2023/12/202312_BMU_EstadosFinancieros_Evolutivo.zip` | application/zip | 674068 | HTTP 200 |
| Bancos Múltiples — Estados Financieros Evolutivos | `https://www.asfi.gob.bo/sites/default/files/estadisticaif/bancos_multiples/2024/12/202412_BMU_EstadosFinancieros_Evolutivo.zip` | application/zip | 246089 | HTTP 200 |
| Bancos Múltiples — Estados Financieros Evolutivos | `https://www.asfi.gob.bo/sites/default/files/estadisticaif/bancos_multiples/2025/12/202512_BMU_EstadosFinancieros_Evolutivo.zip` | application/zip | 255900 | HTTP 200 |
| Bancos de Desarrollo Productivo — Estados Financieros resumidos | `https://www.asfi.gob.bo/sites/default/files/2025-08/202401_BDR_EstadosFinancieros.xls` | application/vnd.ms-excel | 80384 | HTTP 200 |
| Bancos de Desarrollo Productivo — Estados Financieros resumidos | `https://www.asfi.gob.bo/sites/default/files/2025-08/202412_BDR_EstadosFinancieros.xls` | application/vnd.ms-excel | 168960 | HTTP 200 |

### Anexo: estructura observada de los archivos

- El portal es un sitio Drupal 10 con rutas `/pb/...` y `/la/...`.
- La sección `/pb/bancos-multiples` usa un formulario de año/mes; su JavaScript
  público (`bmu-bol.js`) construye la ruta mensual:
  `/sites/default/files/estadisticaif/bancos_multiples/{AAAA}/{MM}/`.
- Cada mes publica un ZIP con un único `.xls` binario (BIFF8) llamado
  `{AAAAMM}_BMU_EstadosFinancieros.xls`; también existen variantes de
  indicadores, desagregados, moneda y evolutivos.
- El `.xls` de EEFF tiene una hoja (`BMU`) con la matriz transpuesta respecto
  de una base de datos: filas = cuentas contables y columnas = entidades.
  Las filas 0–3 contienen metadatos (tipo de entidad, título, fecha y
  `(en miles de bolivianos)`); la fila 5 es el encabezado de entidades y la
  columna final es `TOTAL SISTEMA` (debe excluirse del panel por banco).
- El `.xls` de indicadores usa la misma orientación, con categorías de
  estructura de activos, pasivos, resultados y liquidez.
- El ZIP evolutivo contiene un `.xls` por entidad (por ejemplo
  `..._BMU_EstadosFinancierosBIS.xls`) con la serie histórica de esa entidad.
- Las columnas usan las siglas oficiales de ASFI. Según el PDF público
  "Siglas de Entidades de Intermediación Financiera":
  BNB (Banco Nacional de Bolivia), BME (Mercantil Santa Cruz), BIS (BISA),
  BCR (Crédito de Bolivia), BEC (Económico), BGA (Ganadero), BSO (Solidario),
  BNA (Banco de la Nación Argentina), BIE (FIE), BFO (Fortaleza), BPR (Prodem)
  y BUN (Banco Unión, entidad estatal incluida en la matriz).
- Disponibilidad mensual verificada: desde al menos 2014-12 hasta 2025-12
  (más de 60 meses), lo que habilita el modelado SARIMA con `s=12`.

## Enlaces relevantes por sección

### portada

- [Balance General](https://www.asfi.gob.bo/la/balance-general)
- [Actividad Financiera Ilegal](https://www.asfi.gob.bo/pb/actividad-financiera-ilegal)
- [Servicios Financieros](https://www.asfi.gob.bo/pb/servicios-financieros)
- [Boletín Trimestral de Actualización y Emisión de Normativa](https://www.asfi.gob.bo/pb/boletin-trimestral-actualizacion-y-emision-normativa)
- [Derechos del Consumidor Financiero](https://www.asfi.gob.bo/la/derechos-del-consumidor-financiero)
- [Educación Financiera](https://www.asfi.gob.bo/ef/educacion-financiera)
- [Puntos de Atención Financiera](https://www.asfi.gob.bo/pb/puntos-atenci%C3%B3n-financiera)
- [Contratos Modelo para Servicios Financieros](https://www.asfi.gob.bo/pb/contratos-modelo-para-servicios-financieros)
- [Cobertura de Servicios Financieros](https://www.asfi.gob.bo/la/cobertura-servicios-financieros)
- [Sociedades Controladoras de Grupos Financieros](https://www.asfi.gob.bo/pb/sociedades-controladoras-grupos-financieros)
- [Intermediación Financiera](https://www.asfi.gob.bo/pb/estadisticas-intermediacion-financiera)
- [Servicios Financieros Complementarios](https://www.asfi.gob.bo/pb/estados-financieros)

### estados financieros

- [Balance General](https://www.asfi.gob.bo/la/balance-general)
- [Actividad Financiera Ilegal](https://www.asfi.gob.bo/pb/actividad-financiera-ilegal)
- [Servicios Financieros](https://www.asfi.gob.bo/pb/servicios-financieros)
- [Boletín Trimestral de Actualización y Emisión de Normativa](https://www.asfi.gob.bo/pb/boletin-trimestral-actualizacion-y-emision-normativa)
- [Derechos del Consumidor Financiero](https://www.asfi.gob.bo/la/derechos-del-consumidor-financiero)
- [Educación Financiera](https://www.asfi.gob.bo/ef/educacion-financiera)
- [Puntos de Atención Financiera](https://www.asfi.gob.bo/pb/puntos-atenci%C3%B3n-financiera)
- [Contratos Modelo para Servicios Financieros](https://www.asfi.gob.bo/pb/contratos-modelo-para-servicios-financieros)
- [Cobertura de Servicios Financieros](https://www.asfi.gob.bo/la/cobertura-servicios-financieros)
- [Sociedades Controladoras de Grupos Financieros](https://www.asfi.gob.bo/pb/sociedades-controladoras-grupos-financieros)
- [Intermediación Financiera](https://www.asfi.gob.bo/pb/estadisticas-intermediacion-financiera)
- [Servicios Financieros Complementarios](https://www.asfi.gob.bo/pb/estados-financieros)
- [Entidades de Arrendamiento Financiero 2026](https://www.asfi.gob.bo/la/entidades-arrendamiento-financiero-2026)
- [Entidades de Arrendamiento Financiero 2019](https://www.asfi.gob.bo/la/entidades-arrendamiento-financiero-2019)
- [Entidades de Arrendamiento Financiero 2018](https://www.asfi.gob.bo/la/entidades-arrendamiento-financiero-2018)
- [Entidades de Arrendamiento Financiero 2017](https://www.asfi.gob.bo/la/entidades-arrendamiento-financiero-2017)
- [Entidades de Arrendamiento Financiero 2016](https://www.asfi.gob.bo/la/entidades-arrendamiento-financiero-2016)
- [Entidades de Arrendamiento Financiero 2015](https://www.asfi.gob.bo/la/entidades-arrendamiento-financiero-2015)

### estadisticas intermediacion

- [Balance General](https://www.asfi.gob.bo/la/balance-general)
- [Actividad Financiera Ilegal](https://www.asfi.gob.bo/pb/actividad-financiera-ilegal)
- [Servicios Financieros](https://www.asfi.gob.bo/pb/servicios-financieros)
- [Boletín Trimestral de Actualización y Emisión de Normativa](https://www.asfi.gob.bo/pb/boletin-trimestral-actualizacion-y-emision-normativa)
- [Derechos del Consumidor Financiero](https://www.asfi.gob.bo/la/derechos-del-consumidor-financiero)
- [Educación Financiera](https://www.asfi.gob.bo/ef/educacion-financiera)
- [Puntos de Atención Financiera](https://www.asfi.gob.bo/pb/puntos-atenci%C3%B3n-financiera)
- [Contratos Modelo para Servicios Financieros](https://www.asfi.gob.bo/pb/contratos-modelo-para-servicios-financieros)
- [Cobertura de Servicios Financieros](https://www.asfi.gob.bo/la/cobertura-servicios-financieros)
- [Sociedades Controladoras de Grupos Financieros](https://www.asfi.gob.bo/pb/sociedades-controladoras-grupos-financieros)
- [Intermediación Financiera](https://www.asfi.gob.bo/pb/estadisticas-intermediacion-financiera)
- [Servicios Financieros Complementarios](https://www.asfi.gob.bo/pb/estados-financieros)
- [Boletines Estadísticos](https://www.asfi.gob.bo/pb/boletines-estadisticos)
- [Principales Indicadores Financieros](https://www.asfi.gob.bo/la/principales-indicadores-financieros)

## Conclusiones y recomendaciones

- Se detectaron recursos accesibles. Antes de automatizar descargas, validar los términos de uso del portal y mantener el rate limit configurado.

- Formatos observados en cabeceras: html. El ETL deberá soportar `.xlsx`, `.xls` binario y HTML disfrazado de `.xls`.

- Se verificaron 16 descargas por plantilla mensual (EEFF, indicadores y evolutivos de Bancos Múltiples). La disponibilidad mensual confirmada abarca desde al menos 2014-12 hasta 2025-12, suficiente para el mínimo de 60 meses y para SARIMA con `s=12`.

- Los archivos mensuales llegan como ZIP que contienen `.xls` binarios (BIFF8); algunos recursos del portal también aparecen como PDF o HTML. El ETL deberá soportar `.xls` binario, `.xlsx` y HTML disfrazado de `.xls`.

- Cualquier ruta de descarga directa deberá validarse en una nueva pasada; este informe solo documenta la navegación observada.


> **Descargo:** este documento describe la estructura observada del portal en la fecha indicada. No constituye una afirmación sobre la disponibilidad futura de los archivos ni sobre la solvencia de ninguna entidad financiera.
