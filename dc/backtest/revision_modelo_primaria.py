"""Post-mortem del modelo de la primaria (repo dc2026-rcv-forecast, «FINALES.xlsx») contra el resultado del 16-jun-2026.

El modelo de la primaria acertó al ganador (Lewis George, 85.3 %) pero su primera ronda se equivocó en 12 pp con la
ganadora: repartía los indecisos 55 % / 30 % agotados / 15 % abstención y daba a los candidatos menores el doble de lo
que sacaron. Su README compara la cuota FINAL simulada (51.85 %) con la PRIMERA ronda real (52.79 %); no son la misma
cantidad (aquí no hubo segunda ronda: la final es la primera). Lecciones aplicadas a la general:
  - indecisos de encuestas futuras: reparto proporcional (no 55/30/15);
  - candidatos menores: su cuota sale de resultados reales (lognormales calibradas), no de encuestas.
Resultado real: tabla de la primaria en Wikipedia (votos válidos, sin sobre/subvotos).
"""
from pathlib import Path

import pandas as pd

AQUI = Path(__file__).resolve().parent
modelo = {'Janeese Lewis George': 42.224, 'Kenyan McDuffie': 31.586, 'Gary Goodweather': 5.527, 'Vincent Orange': 4.970,
          'Rini Sampath': 3.870, 'Ernest Johnson': 2.225, 'Hope Solomon': 1.677, 'Otros / por escrito': 7.919}
real = {'Janeese Lewis George': 54.13, 'Kenyan McDuffie': 35.07, 'Gary Goodweather': 3.12, 'Vincent Orange': 2.54,
        'Rini Sampath': 3.22, 'Ernest Johnson': 0.51, 'Hope Solomon': 1.07, 'Otros / por escrito': 0.33}
t = pd.DataFrame({'modelo_primera_ronda': modelo, 'real_primera_ronda': real})
t['error_pp'] = t.modelo_primera_ronda - t.real_primera_ronda
t['razon_modelo_real'] = t.modelo_primera_ronda / t.real_primera_ronda
print(t.round(2).to_string())
menores = t.drop(['Janeese Lewis George', 'Kenyan McDuffie'])
print(f"\nMAE {t.error_pp.abs().mean():.2f} pp · dos principales: {t.error_pp.iloc[:2].round(1).tolist()} · "
      f"menores juntos: modelo {menores.modelo_primera_ronda.sum():.1f} % vs real {menores.real_primera_ronda.sum():.1f} %")
# indecisos de la encuesta WaPo/GMU (27 may–1 jun, 836 LV): JLG 36, McDuffie 25, indecisos 25
enc = {'Janeese Lewis George': 36, 'Kenyan McDuffie': 25}
prop = {k: 100 * v / 75 for k, v in enc.items()}
print(f"WaPo/GMU con indecisos proporcionales: JLG {prop['Janeese Lewis George']:.1f} (real 54.1), McDuffie "
      f"{prop['Kenyan McDuffie']:.1f} (real 35.1)")
(AQUI / 'resultados').mkdir(exist_ok=True)
t.round(3).to_csv(AQUI / 'resultados/revision_modelo_primaria.csv')
