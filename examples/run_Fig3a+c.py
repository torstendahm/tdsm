#--------------------------
# Plot Fig. 3a, 3c und B1a (see manuscript on TDSM ,Dahm, 2022) 
#--------------------------
import sys
sys.path.insert(0, "../")
from pathlib import Path
from tdsm import Config, TDSM, LCM, Traditional, RSM
from tdsm.plotting import plot
from tdsm.loading import StepLoading, BackgroundLoading
import matplotlib.pyplot as plt
import matplotlib.ticker
import math
import numpy as np

current_dir = Path(__file__).parent.parent
config_file = current_dir / "config.toml"
pdf_file0 = current_dir / "../plots/Dahm_fig3a"
pdf_file1 = current_dir / "../plots/Dahm_fig3c"

print("set-up the tdsm, lcm and rsm class environments")
tdsm = TDSM(config=Config.open(config_file))
lcm  = LCM(config=Config.open(config_file))
trad = Traditional(config=Config.open(config_file))
rsm  = RSM(config=Config.open(config_file))


print("define model parameter for plotting, if different from config file")
hours = 3600.
tstart = 0*hours
tend   = 20000*hours
deltat = 18000.0
nt = np.floor( (tend-tstart) / deltat).astype(int)

strend  = 1.0E-8
 
#sstep  =  [0.30, 0.60, 0.90, 1.20, 1.50, 1.80, 3.0]  # stress step in MPa
sstep  =  [0.000000000001, 0.30, 0.60, 0.90, 1.20, 1.50, 1.80]  # stress step in MPa
tstep  = 5.0*hours         # time when stress step is acting

nstep = np.floor( (tstep-tstart) / deltat).astype(int)+1

chi0   = 1.E4            # susceptibility to trigger earthquakes by unit stress increase
depthS = -0.3            # skin depth in MPa (must be defined negativ)

deltaS    = -depthS/500.  # increment do discretize Coulomb stress axis
sigma_max = 10000.*deltaS # maximum depth on Coulomb axis (limit of integral)
precision = 18

print('deltat=',deltat,' sec = ',deltat/hours,' hours, from 0 to ',tend/hours,' hours, samples =',nt)
print('Ta   =',-depthS/strend,' sec = ',-depthS/(strend*hours),' hours')
print('suscept. chi0=',chi0,' #/MPa')
print('stress step=[',sstep,'] MPa')
print('skin depth =',-depthS,' MPa')
print('tectonic trends =',strend,' MPa/s =',strend*24.*hours,' MPa/days,  dot(sigma)*deltat/deltaS=',-strend*deltat/depthS)
print('deltaS=',deltaS,' MPa, from 0 to ',sigma_max,' MPa')

#-----------------------------------------------------
print("Calculate earthquake rates with tdsm, lcm and rsm")
#-----------------------------------------------------
ns   = len(sstep)
cfs    = np.zeros((ns,nt))
K1         = np.zeros(nt)
#romo       = np.zeros(nt)
#romo1      = np.zeros(nt)
r_tdsm = np.zeros((ns,nt))
r_lcm  = np.zeros((ns,nt))
r_rsm  = np.zeros((ns,nt))
n_tdsm = np.zeros((ns,nt-1))
n_lcm  = np.zeros((ns,nt-1))
n_rsm  = np.zeros((ns,nt-1))

r_tdsm_theo = np.zeros((ns,nt))
r_tdsm_theo1 = np.zeros((ns,nt))
r_tdsm_theo2 = np.zeros((ns,nt))
r_tdsm_theo3 = np.zeros((ns,nt))
prod        = np.zeros(ns)      # estimated from integration of theoretical r(t)
ctheo       = np.zeros(ns)      # argument of integration kernel 
r_rsm_theo  = np.zeros((ns,nt))

# ---- initial dfecay according to equation 8 for zero tectonic stress rate
strend_background = 0.00001
strend_background = 0.0000005
strend_background = 0.00005
#strend_background = 0.0
strend_background = [0.0, 0.00001, 0.00005]
nsb   = len(strend_background)
r_tdsm_eq8 = np.zeros((nsb,nt))
romo       = np.zeros((nsb,nt))
romo1      = np.zeros((nsb,nt))
scal1      = np.zeros(nsb)

for i in range(nsb):
    loading = BackgroundLoading(_config=tdsm.config, strend=strend_background[i], deltat=deltat, tstart=tstart, tend=tend)
    config, t, chiz_background, cf, r, xn = tdsm(loading=loading, chi0=chi0, depthS=depthS, deltaS=deltaS, sigma_max=sigma_max, precision=precision, deltat=deltat, tstart=tstart, tend=tend)
    r_tdsm_eq8[i,:] = r

# ---- calculate equilibrium distribution of tectonic loading, to be used later to avoid initial oscillations
loading = BackgroundLoading(_config=tdsm.config, strend=strend, deltat=deltat, tstart=tstart, tend=tend)
config, t, chiz_background, cf, r, xn = tdsm(loading=loading, chi0=chi0, depthS=depthS, deltaS=deltaS, sigma_max=sigma_max, precision=precision, deltat=deltat, tstart=tstart, tend=tend)

print('background')
print('len(cf)',len(cf))
print('len(chiz_background)',len(chiz_background))
rinfty = strend*chi0
Ta   = -depthS/strend
good = t >= (tstep-tstart)
good1 = t >= (tstep-tstart)-deltat
for i in range(ns):

    loading = StepLoading(_config=tdsm.config, strend=strend, sstep=sstep[i], tstep=tstep, deltat=deltat, tstart=tstart, tend=tend)
    config, t, chiz, cf, r, xn = tdsm(loading=loading, equilibrium=True, chiz=chiz_background, chi0=chi0, depthS=depthS, deltaS=deltaS, sigma_max=sigma_max, precision=precision, deltat=deltat, tstart=tstart, tend=tend)
    cfs[i,:]    = cf[:]
    r_tdsm[i,:] = r[:]
    n_tdsm[i,:] = xn[:]

    loading = StepLoading(_config=trad.config, strend=strend, sstep=sstep[i], tstep=tstep, deltat=deltat, tstart=tstart, tend=tend)
    config, t, chiz, cf, r, xn = trad(loading=loading, chi0=chi0, deltat=deltat, tstart=0, tend=tend)
    r_lcm[i,:] = r
    n_lcm[i,:] = xn

    loading = StepLoading(_config=rsm.config, strend=strend, sstep=sstep[i], tstep=tstep, deltat=deltat, tstart=tstart, tend=tend)
    config, t, chiz, cf, r, xn = rsm(loading=loading, chi0=chi0, depthS=depthS, deltat=deltat, tstart=0, tend=tend)
    r_rsm[i,:] = r
    n_rsm[i,:] = xn

    r_rsm_theo[i,:] = rinfty
    r_rsm_theo[i,good] = rinfty/(1.+(np.exp(sstep[i]/depthS)-1.)*np.exp(-(t[good]-tstep)/Ta) )
    r_tdsm_theo3[i,:] = rinfty
    r_tdsm_theo3[i,good] = rinfty/(1.+(np.exp(sstep[i]/depthS)-1.)*np.exp(-(t[good]-tstep)/Ta) )

    #----------------------------------------------
    # ----- calculate own (new) theoretical Omori curves ----
    # t1 bestimmt die Hoehe des peaks
    # t0 bestimmt die Laenge der Abfallkurve, aehnlich wie Ta - mit trial and error auf 0.14*deltat 
    #----------------------------------------------
    dS = -depthS
    strend_tmp = strend
    t0 = 0.1*deltat  # t0 muss deutlich kleiner als deltat sein, damit die peak Amplituden richtig
    t1 = deltat
    t1 = t0    # die peak perturbation is ein Effekt , der durch t1=deltat  die Numerik wiedergibt
    t1 = 0.0
    #f1 = np.exp(-(t[good]-tstep)/Ta)
    #f1 = 1.-np.exp(-sstep[i]/dS)
    f1 = 1.0

    #r_tdsm_theo1[i,good] = chi0*dS*f1*np.exp(-(t[good]-tstep)/Ta)/(Ta*np.exp(-sstep[i]/dS)+(t[good]-tstep)+t1)
    r_tdsm_theo1[i,good] = chi0*dS*np.exp(-(t[good]-tstep)/Ta)/(Ta*np.exp(-sstep[i]/dS)/f1+(t[good]-tstep)+t1)
    r_tdsm_theo1[i,:] = rinfty + r_tdsm_theo1[i,:]
    print('r_tdsm_theo1 max()=',i,sstep[i],np.amax(r_tdsm_theo1[i,:]))

    t1 = Ta*np.exp(-sstep[i]/dS)
    p2 = np.exp(-0.50*sigma_max/dS)  # kleine Korrektur durch endliche Integration
    r_tdsm_theo2[i,good1] = chi0*dS/(t1+(t[good1]-tstep))
    r_tdsm_theo2[i,good1] = r_tdsm_theo2[i,good1]*(np.exp(-p2*(t[good1]-t[nstep]+t1)/t0)-np.exp(-np.exp(-strend_tmp*(t[good1]-tstep)/dS)*(t[good1]-tstep+t1)/t0) )
    r_tdsm_theo2[i,:] = r_tdsm_theo2[i,:]+rinfty

    factor = 380.+(10.-380.)*(sstep[i]-sstep[0])/(sstep[-1]-sstep[0])
    t1 = dS/(sstep[i]/(factor*deltat)-strend_tmp)

    #a = dS/(sstep[i]/deltat-strend_tmp)
    #b= np.exp(-sstep[i]/dS)*dS/strend/(1.-np.exp(-sstep[i]/dS))

    rback = rinfty

    print('# estimate factor prod  und   c  by integration') 
    nev_lcm = 1.0*chi0*(sstep[i])-rback*deltat
    v = dS*deltat/sstep[i]
    values = np.linspace(1.0*v, 800*v, 5000, endpoint=True)
    for k, t1 in enumerate(values):
        t0 = 0.14*deltat
        p2 = np.exp(-0.50*sigma_max/dS)  # kleine Korrektur durch endliche Integration
        r_tdsm_theo[i,good1] = chi0*dS/(t1+(t[good1]-tstep))
        r_tdsm_theo[i,good1] = r_tdsm_theo[i,good1]*(np.exp(-p2*(t[good1]-t[nstep]+t1)/t0)-np.exp(-np.exp(-strend_tmp*(t[good1]-tstep)/dS)*(t[good1]-tstep+t1)/t0) )
        nev = np.trapz(r_tdsm_theo[i,good1], dx=deltat)
        if nev <= nev_lcm:
            prod[i] = t1
            break
    r_tdsm_theo[i,:] = r_tdsm_theo[i,:]+rback


#----------------------------
# theoretical spontaneous decay of fully filled house
# Fazit der Tests: 
# 1. Die Loesung erklaert den Peak und background und Ta. Der detailliete Verlauf fuer kleine Zeiten weicht etwas ab, evtl. durch Approx bei Herleitung
# 2. Variieren von Ta veraendert die Abklingzeit wie gewuenscht. 
# 3. Die Peakhoehe wird fuer ein volles Haus reproduziert, wenn t1 = deltat. Wir t1 > deltat gewaehlt, dann wird die Peak HOehe kleiner
#    Die Abklingform (Ta) bleiben aber gleich, ebenso der BAckground. Man kann durch Steurung von t1 die Response fuer unterschiedliche Depletion Stadien
#    simulieren. t1 = depthS / ( Delta Sigma / Delta t - strend )  
# 4. t0 muss etwa 0.1 Deltat sein, damit Peak Amplituden richtig bestimmt
# 5. Die Integration in the Theorie geht bis zeta = infty. Im Programm aber nur bis etwa 2 * depthS
#----------------------------
solution_old = True
solution_old = False
if solution_old:
    A = chi0*(-depthS)
    t1 = deltat   # t1 muss auf deltat gesetzt werden, damit uebereinstimmung mit numerischer Simulation
    #t1 = 5*deltat   # t1 muss auf deltat gesetzt werden, damit uebereinstimmung mit numerischer Simulation
    t0 = 0.1*deltat  # t0 muss deutlich kleiner als deltat sein, damit die peak Amplituden richtig
    dS = -depthS
    strend_tmp = strend_background
    #strend_tmp = 1E+0*strend_background
    p2 = np.exp(-sigma_max/dS)/t0
    #p2 = np.exp(-0.35*sigma_max/dS)/t0   # mit 0.35 erhalte ich perfekten fit wenn strend>0

    # 1. time dependent component of spontaneous depletion under steady rate (see appendix)
    romo[good] = A/(t1+(t[good]-t[nstep]))
    #romo1[good] = romo[good]*(1.-np.exp(-np.exp(-strend_background*(t[good]-t[nstep])/(-depthS))*(t[good]-t[nstep]+t1)/(t1)) )
    romo1[good] = romo[good]*(np.exp(-p2*(t[good]-t[nstep]+t1))-np.exp(-np.exp(-strend_tmp*(t[good]-t[nstep])/dS)*(t[good]-t[nstep]+t1)/t0) )
    # 2. time independent component of steady rate loading (see appendix)
    # rback = chi0*strend_background
    rback = chi0*(-depthS)*(1.-np.exp(-strend_background*t0/dS))/t0
    romo1[good] = romo1[good]+rback

else:
    for i in range(nsb):
        A = chi0*(-depthS)
        #t1 = -depthS/strend_background
        t1 = deltat
        t0 = 0.1*deltat  # t0 muss deutlich kleiner als deltat sein, damit die peak Amplituden richtig 
        dS = -depthS
        strend_tmp = strend_background[i]
        p2 = np.exp(-sigma_max/dS)/t0

        # 1. time dependent component of spontaneous depletion under steady rate (see appendix)
        romo[i,good] = A/(t1+(t[good]-t[nstep]))
        romo1[i,good] = romo[i,good]*(1.-np.exp(-(t[good]-t[nstep]+t1)/t0))
        # 2. time independent component of steady rate loading (see appendix)
        rback = chi0*strend_background[i]
        if strend_tmp <=0:
            term1 = 1.0
        else:
            tA1 = -depthS/strend_background[i]
            term1 = np.exp(-(t[good]-t[nstep])/tA1)
        romo[i,good] = romo[i,good]*term1
        romo1[i,good] = romo1[i,good]*term1
        romo[i,good] = romo[i,good]+rback
        romo1[i,good] = romo1[i,good]+rback

#-----------------------------------------------------
print("Plotting Fig. 4a")
#-----------------------------------------------------
coltheo = 'black'    
colnum  = 'orange'
thicktheo = 1.5
thicknum = 5.0

for i in range(nsb):
    if strend_background[i]<=0:
        scal1[i] = -chi0*depthS/deltat
    else:
        Ta   = -depthS/strend_background[i]
        scal1[i] = -chi0*depthS*(1./deltat +1/Ta)
tmin = -10.0
tmax = 120.0
xrange_set = False
xrange_set = True
lstyle = '-'
if xrange_set:
    nstart = nstep-1
else:
    nstep = 0
    nstart = 1

fig = plt.figure(2, figsize=(6, 8))
ax = fig.add_subplot(111)
ax.set_xlabel(r'$t/\Delta t$', fontsize=20)
ax.set_ylabel(r'$r T_a \Delta t / \chi_0 V \delta \sigma (T_a + \Delta t)$', fontsize=20)
ax.tick_params(axis = 'both', which = 'major', labelsize = 20)
ax.tick_params(axis = 'both', which = 'minor', labelsize = 18)

ax.plot([(t[0])/deltat,(t[-1])/deltat], [0, 0], linewidth=1.0, ls='-', color='black')
for i in range(nsb-1):
    ax.plot((t[nstart+1:]-t[nstep])/deltat, r_tdsm_eq8[i,1:-nstart]/scal1[i], linewidth=thicknum, ls='-', color=colnum)
    #ax.plot((t[nstart:]-t[nstep])/deltat, romo1[i,nstart:]/scal1[i], linewidth=3.5, color='black', ls='--')
    ax.plot((t[nstart:]-t[nstep])/deltat, romo[i,nstart:]/scal1[i], linewidth=thicktheo, color=coltheo, ls='--')
i= nsb-1
ax.plot((t[nstart+1:]-t[nstep])/deltat, r_tdsm_eq8[i,1:-nstart]/scal1[i], linewidth=thicknum, ls='-', color=colnum, label=r'TDSM')
ax.plot((t[nstart:]-t[nstep])/deltat, romo[i,nstart:]/scal1[i], linewidth=thicktheo, color=coltheo, ls='--', label=r'$equation (8)$')

plt.figtext(0.0, 0.87, 'a)', fontsize=20)
#plt.figtext(0.57, 0.68, r'$\delta\sigma=$'+'{:.1f}'.format(float(-depthS))+' MPa', fontsize=20)
plt.figtext(0.60, 0.68, r'$\Delta t/T_a=$'+'{:.1f}'.format(float(-(strend_background[2]*deltat)/depthS)), fontsize=20)
plt.figtext(0.60, 0.42, r'$\Delta t/T_a=$'+'{:.1f}'.format(float(-(strend_background[1]*deltat)/depthS)), fontsize=20)
plt.figtext(0.60, 0.19, r'$\Delta t/T_a=$'+'{:.1f}'.format(float(-(strend_background[0]*deltat)/depthS)), fontsize=20)
plt.legend(loc='upper right',fontsize=20)
if xrange_set:
    plt.xlim([-5, 50])

plt.show()
fig.savefig(str(pdf_file0)+'.pdf', format='pdf',bbox_inches='tight')
fig.savefig(str(pdf_file0)+'.png', format='png',bbox_inches='tight')

#-----------------------------------------------------
print("Plotting Fig. 4c")
#-----------------------------------------------------
Ta   = -depthS/strend
fa   = np.zeros(ns)
fa   = -np.asarray(sstep)/(depthS)
Ta0 = 0.0
rinfty = strend*chi0
tmin = -10.0
tmax = 120.0
xrange_set = False
xrange_set = True
lstyle = '-'

if xrange_set:
    nstart = nstep-0
    nstart = nstep-1
else:
    nstep = 0
    nstart = 0

# ---- Coulomb stress loading (input and interpolated input)
fig = plt.figure(1, figsize=(6, 8))
ax1a = fig.add_subplot(111)
ax1a.set_ylabel('$\sigma_c/\dot{\sigma}_cT_a$', fontsize=20)
ax1a.set_xlabel(r'$(t-t_0)/T_a$', fontsize=20)
ax1a.tick_params(axis = 'both', which = 'major', labelsize = 20)
ax1a.tick_params(axis = 'both', which = 'minor', labelsize = 18)

for i in range(ns):
    ax1a.plot((t[nstart:]-t[nstep])/Ta, cfs[i,nstart:]/(Ta*strend), linewidth=2.0, ls=lstyle, color='black', label=r'$\Delta\sigma/\delta\sigma=$'+'{:.1f}'.format(float(fa[i])))

plt.legend(loc='lower right',fontsize=20)
if xrange_set:
    #plt.xlim([tmin, tmax])
    print(' to be defined')
plt.show()

# ---- earthquake rate ------------------------------------
fig = plt.figure(2, figsize=(6, 8))
ax1b = fig.add_subplot(111)
ax1b.set_xlabel(r'$(t-t_s)/T_a$', fontsize=20)
ax1b.set_ylabel(r'$r / \chi_0 V \dot{\sigma}_c$', fontsize=20)
ax1b.tick_params(axis = 'both', which = 'major', labelsize = 20)
ax1b.tick_params(axis = 'both', which = 'minor', labelsize = 18)

ax1b.plot([(t[nstart]-t[nstep])/Ta, (t[nt-1]-t[nstep])/Ta], [1, 1], linewidth=1.0, ls='-', color='black')
for i in range(ns-1):
    ax1b.plot((t[nstart:]-t[nstep])/Ta , r_tdsm[i,nstart:]/rinfty, linewidth=thicknum, ls='-', color=colnum)

    #ax1b.plot((t[nstart:]-t[nstep]+deltat)/Ta , r_tdsm_theo[i,nstart:]/rinfty, linewidth=1.5, ls='--', color='blue')
    #ax1b.plot((t[nstart:]-t[nstep]+deltat)/Ta , r_tdsm_theo1[i,nstart:]/rinfty, linewidth=4.5, ls='dotted', color='red')
    #ax1b.plot((t[nstart:]-t[nstep]+deltat)/Ta , r_tdsm_theo2[i,nstart:]/rinfty, linewidth=thicktheo, ls='--', color=coltheo)
    ax1b.plot((t[nstart:]-t[nstep]+deltat)/Ta , r_tdsm_theo3[i,nstart:]/rinfty, linewidth=thicktheo, ls='--', color=coltheo)
    #ax1b.plot((t[nstart:]-t[nstep]+deltat)/Ta , r_rsm_theo[i,nstart:]/rinfty, linewidth=1.5, ls='-', color='yellow')

i=ns-1
ax1b.plot((t[nstart:]-t[nstep])/Ta , r_tdsm[i,nstart:]/rinfty, linewidth=thicknum, ls='-', color=colnum, label=r'TDSM')
#ax1b.plot((t[nstart:]-t[nstep])/Ta , r_rsm[2,nstart:]/rinfty, linewidth=1.5, ls='dotted', color='green', label=r'RSM')
plt.text((t[nstart+2]-t[nstep])/Ta , 1.3*r_tdsm[i,nstart+2]/rinfty ,r'$\Delta\sigma/\delta\sigma=$'+'{:.0f}'.format(float(fa[i])), fontsize=20)
#plt.text((t[nstart+2]-t[nstep])/Ta , 0.97*r_tdsm[i,nstart+2]/rinfty ,r'$t_1/T_a=$'+'{:.4f}'.format(float(prod[i]/Ta)), fontsize=20)

#ax1b.plot((t[nstart:]-t[nstep]+deltat)/Ta , r_tdsm_theo[i,nstart:]/rinfty, linewidth=1.5, ls='--', color='blue', label='eq. (13)')
#ax1b.plot((t[nstart:]-t[nstep]+deltat)/Ta , r_tdsm_theo1[i,nstart:]/rinfty, linewidth=4.5, ls='dotted', color='red')
ax1b.plot((t[nstart:]-t[nstep]+deltat)/Ta , r_tdsm_theo3[i,nstart:]/rinfty, linewidth=thicktheo, ls='--', color=coltheo, label='eq. (13)')
#ax1b.plot((t[nstart:]-t[nstep]+deltat)/Ta , r_rsm_theo[i,nstart:]/rinfty, linewidth=1.5, ls='-', color='yellow')

for i in range(ns-1):
    #plt.text((t[nstart+2]-t[nstep])/Ta , r_tdsm[i,nstart+2]/rinfty ,r'{:.1f};{:2.3f}'.format(float(fa[i]),float(prod[i]/Ta)), fontsize=20)
    plt.text((t[nstart+2]-t[nstep])/Ta , r_tdsm[i,nstart+2]/rinfty ,r'{:.1f}'.format(float(fa[i])), fontsize=20)

plt.legend(loc='upper right',fontsize=20)
plt.figtext(0.0, 0.87, 'c)', fontsize=20)
plt.figtext(0.55, 0.63, r'$T_a=$'+'{:.0f}'.format(float(Ta/(24*hours)))+' days', fontsize=20)
if xrange_set:
    #plt.xlim([tmin, tmax])
    #plt.ylim([0.9, 1500])
    plt.ylim([0.9, 700])
    ax1b.set_xscale('log')
    ax1b.set_yscale('log')
    ax1b.set_yticks([1,10,50,100])
    ax1b.get_yaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
else:
    print(' to be defined')

plt.show()
fig.savefig(str(pdf_file1)+'.pdf', format='pdf',bbox_inches='tight')
fig.savefig(str(pdf_file1)+'.png', format='png',bbox_inches='tight')
