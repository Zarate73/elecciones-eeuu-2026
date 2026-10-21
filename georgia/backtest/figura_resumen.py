"""Figura resumen del backtest y pronóstico 2026."""
import pandas as pd, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from scipy.stats import norm
from pathlib import Path
O = Path(__file__).resolve().parent / 'salida_backtest'
R = pd.read_csv(O/'metricas_h15.csv'); C = pd.read_csv(O/'C_sesgo_estado_decaimiento.csv')
G = pd.read_csv(O/'GA_errores_historicos_h15.csv'); T = pd.read_csv(O/'2026_pronostico.csv')
mods = {'pond|sd_V9(2pp)':'V9: encuestas + σ piso 2pp','pond|sd_empirica':'Encuestas + σ empírica',
        'casa|sd_empirica':'+ efectos de casa','casa_part|fundamentales+sd_emp':'+ fundamentales'}
rows=[]
for amb, ca in [('Nacional_todas','Nacional'),('GA_generales','GA_generales')]:
    for m,lab in mods.items():
        r=R[(R.ambito==amb)&(R.modelo==m)].iloc[0]; rows.append((ca,lab,r.CRPS,r.Cob80,r.Cob95))
    c=C[(C.ambito==ca)&(C.vida_media_anios==4)].iloc[0]; rows.append((ca,'+ casa + sesgo GA (4 años) ★',c.CRPS,c.Cob80,c.Cob95))
D=pd.DataFrame(rows,columns=['amb','modelo','CRPS','Cob80','Cob95'])
ink='#1f2933'; acc='#2563eb'; mute='#9aa5b1'
fig,ax=plt.subplots(2,2,figsize=(13,8.5)); plt.rcParams['font.size']=9.5
for i,amb in enumerate(['Nacional','GA_generales']):
    a=ax[0,i]; s=D[D.amb==amb]
    cols=[acc if '★' in m else mute for m in s.modelo]
    a.barh(s.modelo[::-1],s.CRPS[::-1],color=cols[::-1]); a.set_title(f'CRPS a T−15 (LOYO) · {amb} · menor es mejor',loc='left',color=ink)
    lo=s.CRPS.min()*0.9; a.set_xlim(lo,s.CRPS.max()*1.12)
    for y,(v,c8,c9) in enumerate(zip(s.CRPS[::-1],s.Cob80[::-1],s.Cob95[::-1])):
        a.text(v,y,f'  {v:.2f} | cob80 {c8:.0%} cob95 {c9:.0%}',va='center',fontsize=8.5,color=ink)
    a.spines[['top','right']].set_visible(False)
a=ax[1,0]; g=G[~G.race.str.contains('GR')]
a.axhline(0,color=mute,lw=1); a.scatter(g.year,g.e,s=18+8*g.k,color=acc,alpha=.8)
a.set_title('GA: error del promedio a T−15 (encuestas − resultado, pp D−R)',loc='left',color=ink)
a.set_ylabel('+ = encuestas sobrestiman a D'); a.spines[['top','right']].set_visible(False)
a=ax[1,1]; x=np.linspace(-20,15,600)
m0=T.iloc[0]; a.plot(x,norm.pdf(x,m0.margen_B_J,m0.sd),color=acc,lw=2,label=f'Ganador: {m0.margen_B_J:+.1f} ± {m0.sd:.1f} · P(Bottoms)={m0.P_Bottoms_gana_pluralidad:.2f}')
a.plot(x,norm.pdf(x,0.34,3.03),color=mute,lw=2,ls='--',label='V9: +0.3 ± 3.0 · P(Bottoms)=0.55')
a.axvline(0,color=ink,lw=.8); a.set_title('Georgia Gobernador 2026 · margen Bottoms − Jackson',loc='left',color=ink)
a.legend(frameon=False,fontsize=8.5,loc='upper left',bbox_to_anchor=(0,1.0)); a.set_ylim(0,0.2); a.set_yticks([]); a.spines[['top','right','left']].set_visible(False)
fig.tight_layout(); fig.savefig(O/'resumen_backtest_georgia.png',dpi=150)
print('ok')
