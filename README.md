# Oriens-Skills

Skills de Claude para armar las propuestas comerciales de Oriens Energía Solar.
Cada carpeta es una skill (contiene un `SKILL.md`, y según el caso `scripts/`, `reference/` y `assets/`).

> Repositorio privado: las carpetas `reference/` incluyen PDFs y configs de clientes reales.

## Propuestas por tipo de central

| Skill | Para qué sirve |
|---|---|
| `central-ongrid` | On Grid sin batería: una alternativa, o 2-3 comparadas. También On Grid vs. híbrida sin batería (caso Gentile). |
| `central-hibrida-dos-alternativas` | Híbrida con inyección, 2-3 alternativas que difieren en batería y/o paneles. Motor mes a mes con arrastre de crédito. |
| `central-hibrida-propuesta-unica-sin-bateria` | Híbrida sin batería en un solo escenario (batería prevista para una segunda etapa). |
| `central-hibrida-peak-shaving` | Suministros con tarifa de demanda (Edenor T2 y similares): recorte de picos con baterías. |
| `central-off-grid` | Off grid en paralelo a la red sin inyectar, o aislada. 1 a 3 alternativas. Respaldo ante cortes. |
| `central-mixta-mono` | Monofásico: compara off grid contra híbrida(s) en 2-3 alternativas. |

## General

| Skill | Para qué sirve |
|---|---|
| `habilidad-armado-de-presupuesto-y-analisis` | Propuesta industrial/comercial On Grid, residencial híbrida con batería y off grid con alternativas de batería. Incluye la lista de errores ya cometidos. |

## Versiones descartadas al armar este repo

- `oriens-propuesta-industrial`: versión anterior de `habilidad-armado-de-presupuesto-y-analisis`, sin las correcciones del caso Castresana.
- `guardar-en-google`: skill personal para guardar propuestas en Drive; se descartó para la migración a Teams.
- `central-ongrid-una-alternativa`: absorbida por `central-ongrid` (modo una alternativa), que además tiene la leyenda actualizada del gráfico.

## Cómo cargarlas en Claude Teams

- Owner: Organization settings > Plugins & skills > Upload a skill.
- Usuario: Customize > Skills > Upload a skill (y compartirla después).
