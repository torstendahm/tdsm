"""
TDSM (Time Dependent Seismicity Model)
====================================
TDSM is python tool to simulate time dependent earthquake rates for different stress loading scenarios. 
Earthquake rate is definded as number of events per time unit with magnitudes above a completeness magntiude. 
Stress loading is understood as Coulomb stress as a function of time. The stress loading is assumed homogeneous within the rock volume for which the simulation is performed. The details of the TDSM model are given in the paper by Dahm (2022) submitted. 

Additional  to the TDSM model simulations, the tdsm tool can simulate earthquakes rates for a rate and state seismicity model and a linear Coulomb failure model, which can be loaded from tdsm. Different loading scenarios are supported, including step in Coulomb stress, a constant background stress rate, a change in stres rate, a cyclic stress rate superposed to a constant background trend, a stress curve defined by 4 points, a ramp like loading scenario, or a loading tome function readed from an exernal file. The loading classes are imported from tdsm.loading.  

An elementary plotting class is supported, which is imported from tdsm.plotting.

Input parameter can be defined in config.toml (default settings)  or when calling the seismicity models or loading scenarios. 

Examples how to use the tdsm tools  are provided in python scripts in directory examples. Example scripts reproduce figures published in Dahm (2022) submitted.

Please cite Dahm (2022) and Dahm et al. (2022) when using the software. No warranty is given. 
"""

from copy import deepcopy
from typing import Optional, Tuple

import numpy as np
import numpy.typing as npt
#import nptyping as npt

from tdsm.config import Config
from tdsm.loading import Loading
from tdsm.utils import gridrange, shifted

Result = Tuple[
    Config,
    npt.NDArray[np.float64],
    npt.NDArray[np.float64],
    npt.NDArray[np.float64],
    npt.NDArray[np.float64],
]


class LCM(object):
    """Linear Coulomb Failure Model (LCM ) ,according to Dahm (2022), class documentation.
       This LCM class  is used as base for calculating time dependent seismicity with class tdsm. For calculation of
       responses with a linear Coulomb Failure model the class "Traditional" is recommended. 
    """

    def __init__(self, config: Optional[Config] = None) -> None:
        """
        Add description here

        Parameters
        ---------
        config
            Optional config to use
        """
        self.config = config or Config()

    def __call__(
        self,
        chi0: Optional[float] = None,
        chiz: Optional[float] = None,
        depthS: Optional[float] = None,
        Sshadow: Optional[float] = None,
        equilibrium: Optional[bool] = None,
        deltat: Optional[float] = None,
        tstart: Optional[float] = None,
        tend: Optional[float] = None,
        deltaS: Optional[float] = None,
        sigma_max: Optional[int] = None,
        precision: Optional[int] = None,
        loading: Optional[Loading] = None,
    ) -> Result:
        config = deepcopy(self.config)
        config.merge(
            dict(
                chi0=chi0,
                depthS=depthS,
                Sshadow=Sshadow,
                equilibrium=equilibrium,
                deltat=deltat,
                tstart=tstart,
                tend=tend,
                deltaS=deltaS,
                sigma_max=sigma_max,
                precision=precision,
            )
        )
        if loading is not None:
            config.loading = loading
        #if config.equilibrium:
        if chiz is not None:
            self._prepare(config)
            chiz_background = chiz
            #print('chiz_background=',chiz_background)
            self.chiz = chiz_background
        else:
            #print('chiz is none')
            self._prepare(config)
        return self._compute(config)

    def _prepare(self, config: Config) -> None:
        (self.smin, self.smax, self.nsigma, self.sigma) = gridrange(
            -config.sigma_max, +config.sigma_max, config.deltaS
        )
        (self.tmin, self.tmax, self.nt, self.t) = gridrange(
            config.tstart, config.tend, config.deltat
        )
        self.chiz = np.zeros(self.nsigma)
        self.pz = np.heaviside(self.sigma, 1)
        loading = config.loading
        if loading is None:
            raise ValueError("missing loading function")
        self.cf = loading.values(length=self.nt)

    def _compute(self, config: Config) -> Result:
        if config.equilibrium:
            #chiz = np.heaviside(-self.sigma, 0)
            #raise ValueError("the option to calculate or read the equilibrium function chiz is not yet implemented")
            print("chiz bereits uebergeben, daher nicht ueberschrieben mit Heaviside")
        else: 
            self.chiz = np.heaviside(-self.sigma, 0)

        nshift = np.around(config.Sshadow / config.deltaS, 0).astype(int)
        self.chiz = shifted(self.chiz, nshift)

        ratez = np.zeros(self.nt)
        ratez[0] = 0.0
        resid = 0.0
        for i in range(1, self.nt):
            deltacf = self.cf[i] - (self.cf[i - 1] - resid)
            nshift = np.around(deltacf / config.deltaS, 0).astype(int)
            resid = deltacf - nshift * config.deltaS
            # shift chiz (memory effect)
            self.chiz = shifted(self.chiz, nshift)
            ratez[i] = np.trapz(self.chiz * self.pz) * config.deltaS  # type: ignore
            # cut off chiz
            self.chiz = self.chiz * (1.0 - self.pz)

        ratez = ratez * config.chi0 / config.deltat
        neqz = np.zeros(self.nt - 1)
        # neqz[0] = 0.0
        for i in range(1, self.nt - 2):
            neqz[i] = np.trapz(ratez[0 : i + 1])  # type: ignore
        return config, self.t, self.chiz, self.cf, ratez, neqz


class TDSM(LCM):
    """TDSM class documentation.
       TDSM estimates the time dependent seimicity response for a given stress loading scenario.  
       Theory is described in Dahm (2022), submitted. 
    """

    def _compute(self, config: Config) -> Result:
        # use exponential decay for pz
        ndepth = np.around(config.depthS / config.deltaS, 0).astype(int)
        nzero = int(self.nsigma / 2)
        window = int(config.precision * ndepth)
        self.pz[nzero + window : nzero] = np.exp(-np.arange(window, 0) / ndepth)
        return super()._compute(config)

class TDSR(LCM):
    """TDSR class documentation.
       Seismicity response of TDSR for a continuous stress evolution S(t) for times t
       given the stress distribution Z at t=t[0]
       TDSR estimates the time dependent seimicity response for a given stress loading scenario.  
       Theory is described in Dahm and Hainzl (2022), in revision 
    """

    def _compute(self, config: Config) -> Result:
        ratez = np.zeros(self.nt)
        cf_shad = np.zeros(self.nt)
        S0 = -config.Sshadow
        cf_shad[0] = self.cf[0] - config.Sshadow
        dt = np.ediff1d(self.t, to_end=config.loading.strend)
        dS = np.ediff1d(self.cf, to_end=config.loading.strend)

        for i in range(1, self.nt):

        #def TDSR(t, S, ZZ, XX, t0, dsig):
        #    Z = np.copy(ZZ)
        #    X = np.copy(XX)
        #    dS = np.ediff1d(S, to_end=S[-1]-S[-2])
        #    dt = np.ediff1d(t, to_end=t[-1]-t[-2])
        #    dZ = np.ediff1d(Z, to_end=Z[-1]-Z[-2])
        #    R = np.zeros(len(dS))
        #    aus CF Model:   gamma = (dum - config.deltat/dS[i-1]) * np.exp((-dS[i-1]+Asig*np.log(config.loading.strend))/Asig) +config.loading.strend* config.deltat/dS[i-1]
            dX = X / tf(Z, t0, dsig) * dt[i]
            dX[(dX>X)] = X[(dX>X)]
            ratez[i] = np.sum(dX * dZ) / dt[i]
            Z -= dS[i]
            X -= dX

        neqz = np.zeros(self.nt - 1)
        for i in range(1, self.nt - 2):
            neqz[i] = np.trapz(ratez[0 : i + 1])  # type: ignore
        return config, self.t, cf_shad, self.cf, ratez, neqz


class Traditional(LCM):
    """Linear Coulomb Failure Model (LCM ) - traditional way of calculation, class documentation.
       LCM estimtes the linear, instantaneous seimicity response for a given stress loading scenario.  
       Simulations with the LCM cannot account for delayed failure,. 
    """

    def _compute(self, config: Config) -> Result:
        ratez = np.zeros(self.nt)
        cf_shad = np.zeros(self.nt)
        S0 = -config.Sshadow
        cf_shad[0] = self.cf[0] - config.Sshadow
        for i in range(1, self.nt - 1):
            if self.cf[i] >= self.cf[i - 1] and self.cf[i] >= S0:
                S0 = self.cf[i]
                ratez[i] = (self.cf[i] - self.cf[i - 1])
            else:
                ratez[i] = 0.0
            cf_shad[i] = S0
        ratez = ratez * config.chi0 / config.deltat
        neqz = np.zeros(self.nt - 1)
        for i in range(1, self.nt - 2):
            neqz[i] = np.trapz(ratez[0 : i + 1])  # type: ignore
        return config, self.t, cf_shad, self.cf, ratez, neqz

class CFM(LCM):
    """Linear Coulomb Failure Model (CFM ) - traditional way of calculation, class documentation.
       DFM estimtes the linear, instantaneous seimicity response for a given stress loading scenario.  
       Simulations with the CFM cannot account for delayed failure,. 
    """

    def _compute(self, config: Config) -> Result:
        ratez = np.zeros(self.nt)
        cf_shad = np.zeros(self.nt)
        S0 = -config.Sshadow
        cf_shad[0] = self.cf[0] - config.Sshadow
        for i in range(1, self.nt - 1):
            if self.cf[i] >= self.cf[i - 1] and self.cf[i] >= S0:
                S0 = self.cf[i]
                ratez[i] = (self.cf[i] - self.cf[i - 1])
            else:
                ratez[i] = 0.0
            cf_shad[i] = S0
        ratez = ratez * config.chi0 / config.deltat
        neqz = np.zeros(self.nt - 1)
        for i in range(1, self.nt - 2):
            neqz[i] = np.trapz(ratez[0 : i + 1])  # type: ignore
        return config, self.t, cf_shad, self.cf, ratez, neqz

class RSM(LCM):
    """Rate and State Model (RCM) class documentation.
       RSM estimates the time dependent seimicity response for a given stress loading scenario.  
       Theory is described in Dietrich (1994), JGR. 
    """

    def _compute(self, config: Config) -> Result:
        cf_shad = np.zeros(self.nt)
        S0 = -config.Sshadow
        #self.chiz[0] = self.cf[0] - config.Sshadow
        cf_shad[0] = self.cf[0] - config.Sshadow
        ratez = np.zeros(self.nt)
        dS = np.ediff1d(self.cf, to_end=config.loading.strend)
        rinfty = config.chi0*config.loading.strend
        Asig = -config.depthS
        print('Asig',Asig)
        gamma = 1.0
        ratez[0] = 1.0
        for i in range(1, self.nt):
            dum = gamma / config.loading.strend
            # Cattania, PhD Eq.(6.2), Dieterich JGR 1994, Eq.(17):
            gamma = (dum - config.deltat/dS[i-1]) * np.exp(-dS[i-1]/Asig) + config.deltat/dS[i-1]
            gamma *= config.loading.strend
            ratez[i] = 1.0 / gamma
            cf_shad[i] = S0
            #self.chiz[i] = S0
        ratez = rinfty*ratez
        neqz = np.zeros(self.nt - 1)
        for i in range(1, self.nt - 2):
            neqz[i] = np.trapz(ratez[0 : i + 1])  # type: ignore
        #return config, self.t, self.chiz, self.cf, ratez, neqz
        return config, self.t, cf_shad, self.cf, ratez, neqz

class RSD(LCM):
    """Rate and State Model a la Dietrich (RSrate_Dietrich) class documentation.
       RSrate_Dietrich estimates the time dependent seimicity response for a given stress loading scenario.  
       Theory is described in Dietrich (1994), JGR. 
    """

    def _compute(self, config: Config) -> Result:
        cf_shad = np.zeros(self.nt)
        S0 = -config.Sshadow
        cf_shad[0] = self.cf[0] - config.Sshadow
        ratez = np.zeros(self.nt)  # nt = len(S)
        gamma = 1.0
        ratez[0] = 1.0

        #dt = np.ediff1d(t, to_end=t[-1]-t[-2])
        #dS = np.ediff1d(S, to_end=S[-1]-S[-2])
        dt = np.ediff1d(self.t, to_end=config.loading.strend)
        dS = np.ediff1d(self.cf, to_end=config.loading.strend)

        rinfty = config.chi0*config.loading.strend
        Asig = -config.depthS
        print('Asig',Asig)
        gamma = 1.0
        ratez[0] = 1.0
        for i in range(1, self.nt):
            dum = gamma / config.loading.strend
            # Cattania, PhD Eq.(6.2), Dieterich JGR 1994, Eq.(17):
            gamma = (dum - config.deltat/dS[i-1]) * np.exp((-dS[i-1]+Asig*np.log(config.loading.strend))/Asig) +config.loading.strend* config.deltat/dS[i-1]
            ratez[i] = 1.0 / gamma
            cf_shad[i] = S0
        ratez = rinfty*ratez
        neqz = np.zeros(self.nt - 1)
        for i in range(1, self.nt - 2):
            neqz[i] = np.trapz(ratez[0 : i + 1])  # type: ignore
        return config, self.t, cf_shad, self.cf, ratez, neqz
