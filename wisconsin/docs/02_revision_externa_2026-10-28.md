# Revisión externa del modelo de Wisconsin (28-oct-2026)

La revisión cubre `wi_pronostico` v1.0.0. No pide cambios al modelo; deja dos verificaciones de cierre, que se resolvieron así:

| Hallazgo | Veredicto | Acción |
|---|---|---|
| WI-01 · Dos firmas concentran el promedio (Wick 59 %, Marquette 41 %) | Correcto; ya cuantificado (sin Marquette: +4.1, P 74 % sin mercados; sin Wick: +5.3, P 83 %) | Ninguna; se conservan las sensibilidades |
| WI-02 · Sin sesgo estatal | Coincide con el backtest | Ninguna |
| WI-03 · Marquette se publicó el 28-oct (campo 14–22 oct) | **Verificado con una prueba nueva** | `test_reconstruccion_excluye_marquette_antes_de_su_publicacion` |
| WI-04 · Efecto de diseño | Sin defecto demostrado | Pendiente para después de la elección |
| WI-05 · Votos por escrito fijos en 0.10 % | **Verificado contra la boleta** | Ninguna |
| WI-06 · Incertidumbre con k = 2 | Limitación conocida; σ = 6.5 | Ninguna |

## WI-03 · Reconstrucciones anteriores al 28-oct
- **Prueba nueva (parametrizada)**, con las fuentes descargadas el 28-oct:
  - **corte 25-oct:** no entran Marquette de octubre (publicada el 28) ni Wick (sin fecha de publicación conocida: fin + 3 días = 26-oct). Como no hay encuestadoras en los últimos 21 días, la ventana se amplía: Marquette de septiembre, Z to A y YouGov/City Forward;
  - **corte 27-oct:** entra Wick y Marquette de octubre sigue fuera. Con una sola encuestadora en 21 días, la ventana se amplía desde el 2-oct: Wick y YouGov/City Forward;
  - en ningún corte aparece la Marquette del 14–22 oct, y la única Marquette posible en la ventana es la de septiembre.
- **Pronóstico reconstruido** (las mismas fuentes y mercados al cierre de cada día):

  | Corte | Ventana | Promedio de encuestas | Margen final | P(Crowley) |
  |---|---|---|---|---|
  | 25-oct | Marquette sep · Z to A · YouGov | +3.8 | +4.0 | 76.3 % |
  | 27-oct | Wick · YouGov | +4.1 | +4.4 | 75.8 % |
  | 28-oct (en vivo) | Marquette oct · Wick | +5.5 | +5.8 | 81.9 % |

  La publicación de Marquette subió P(Crowley) unos 6 puntos. Sin la regla de disponibilidad, una reconstrucción del 25 o el 27 habría mostrado esa subida antes de que existiera.

## WI-05 · Boleta
- **Boleta de muestra oficial** (condado de Portage, 3-nov-2026): para gobernador y vicegobernador solo aparecen Tiffany/Varnam (R) y Crowley/Godlewski (D), más una línea de voto por escrito.
- **Candidatos por escrito registrados:** siete, entre ellos Jamie Jo Carothers y David D. King (independientes), según The Green Papers. Ningún partido menor tiene candidato en la boleta.
- **El supuesto se sostiene.** Los terceros son solo votos por escrito, y en 2022 sumaron 0.07 % (1,983 votos) con una independiente retirada que aún figuraba en la boleta. La media de 0.10 % con sd de 0.05 cubre el rango 0.0–0.2 %, y su efecto en el margen es nulo.

## Fuentes
- [Boleta de muestra 2026, condado de Portage](https://www.co.portage.wi.gov/DocumentCenter/View/7365/2026-General-Election-Sample-Ballot---web)
- [The Green Papers: Wisconsin 2026](https://www.thegreenpapers.com/G26/WI)
- [Marquette Law School Poll, 28-oct-2026](https://law.marquette.edu/poll/)
