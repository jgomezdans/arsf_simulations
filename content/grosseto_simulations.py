#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import panel as pn
import pandas as pd
import holoviews as hv
import clumping
from ipyleaflet import Map, Rectangle, LayersControl, LayerGroup, Marker, WMSLayer
pn.extension()
pn.extension('ipywidgets')
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import datetime as dt
import numpy as np
pd.options.plotting.backend = 'holoviews'


# In[ ]:





# In[ ]:


def do_sims(Lon, Lat, Time, lam, lai, tsoil, tleaf, emv, ems, hspot, lidfa, tleaf_sunlit, tsoil_sunlit,
           H, w, D, psi):
    sza, saa = clumping.calculate_solar_position(Lon, Lat, Time)
    sail_params = clumping.ThermalSail(
                lam=lam,
                lai=lai,
                tsoil=tsoil,
                tleaf=tleaf,
                emv=emv,
                ems=ems,
                hspot=hspot,
                lidfa=lidfa,
                lidfb=None,
                tleaf_sunlit=tleaf_sunlit,
                tsoil_sunlit=tsoil_sunlit,
    )
    vza = np.linspace(-90, 90, 90)
    raa = [0 if v <= 0 else 180 for v in vza]
    retval = [clumping.run_thermalsail(sza, abs(v), r, sail_params)
                for v, r in zip(vza, raa)
            ]
    retval = np.array([x[1] - 273.15 for x in retval])
    scatter = hv.Scatter((vza, retval), "VZA [deg]", "Brightness temperature [degC]").opts(width=800)
    curve = hv.Curve(scatter, label="Continuous canopy")
    retval = curve*scatter
    p = clumping.ThermalSail(**sail_params.__dict__.copy())
    row_sims = []
    for v, r in zip(vza, raa):
        Omega = clumping.calculate_clumping(H, w, D, lai, sail_params.lidfa, v, psi)
        p.lai = lai*np.abs(Omega)
        x = clumping.run_thermalsail(sza, abs(v), r, p)
        row_sims.append(x[1]-273.15)
    scatter = hv.Scatter((vza, row_sims), "VZA [deg]", "Brightness temperature [degC]").opts(width=800)
    curve = hv.Curve(scatter, label="Row-oriented canopy")
    
    return retval*scatter*curve
                
    
#retval = do_sims()


# In[ ]:


# Acquisition
lon = pn.widgets.FloatInput(name="Longitude", start=-180, end=180, value=11.124)
lat = pn.widgets.FloatInput(name="Latitude", start=-90, end=90, value=42.7635)
timer = pn.widgets.DatetimePicker(name="Overflight time", value=dt.datetime(2023,5,18,14,0))
lam = pn.widgets.FloatSlider(name="Wavelength [um]", start=7.6, end=12.5, step=(12.5-7.6)/103, value=9.5)
acquisition = pn.WidgetBox("### Acquisition", lon, lat, timer, lam)

# Architecture
hspot = pn.widgets.FloatSlider(name="HotSpot parameter [-]", start=0.01, end=0.1, value=0.05)
lidfa = pn.widgets.FloatSlider(name="Average leaf angle [deg]", start=0.0, end=90, value=45)
lai = pn.widgets.FloatSlider(name="Leaf Area Index [m2/m2]", start=0.0, end=4, value=2)
architecture = pn.WidgetBox("### Canopy", lai, lidfa, hspot)
# Thermodynamics
tsoil = pn.widgets.FloatSlider(name="Shaded soil temperature [degC]", start=-10, end=100, value=35)
tleaf = pn.widgets.FloatSlider(name="Shaded leaf temperature [degC]", start=-10, end=100, value=25)
tsoil_sunlit = pn.widgets.FloatSlider(name="Sunlit soil temperature [degC]", start=-10, end=100, value=45)
tleaf_sunlit = pn.widgets.FloatSlider(name="Sunlit leaf temperature [degC]", start=-10, end=100, value=33)
ems = pn.widgets.FloatSlider(name="Soil emissivity [-]", start=0.9, end=1.0, value=0.94)
emv = pn.widgets.FloatSlider(name="Leaf emissivity [-]", start=0.9, end=1.0, value=0.98)
thermodynamics = pn.WidgetBox("### Thermal", tsoil, tleaf, tsoil_sunlit, tleaf_sunlit, ems, emv)


row_H = pn.widgets.FloatSlider(name="Row height [m]", start=0.0, end=5.0, value=1.5)
row_width = pn.widgets.FloatSlider(name="Row width [m]", start=0.0, end=5.0, value=0.5)
row_sep = pn.widgets.FloatSlider(name="Row separation [m]", start=0.0, end=10.0, value=1.2)
row_angle = pn.widgets.FloatSlider(name="Row angle with VAA [deg]", start=0, end=90.0, value=45)
rows = pn.WidgetBox("### Row geometry", row_H, row_width, row_sep, row_angle)

sza, saa = clumping.calculate_solar_position(lon.value, lat.value, timer.value)


json_widget = pn.pane.JSON({"SZA": f"{sza:6.2f}", "SAA": f"{saa:6.2f}", 
                          "Lon": f"{lon.value:+8.5f}", "Lat": f"{lat.value:+8.5f}",
                         "UTC":timer.value.strftime("%Y-%m-%d %H:%M:%S"),
                         }, height=300, width=400, name="Sun position")


    
m = Map(center=(42.7465,11.1124), zoom_snap=0.25, zoom=10)
wms = WMSLayer(
    url='https://tiles.maps.eox.at/wms',
    layers='s2cloudless-2020_3857',
    format='image/jpeg',
    transparent=True,
    attribution='Sentinel2 Cloudless 2020'
)

marker = Marker(location=(42.7465,11.1124), draggable=True) 
m.add_layer(marker)
m.add_layer(wms)

def on_location_changed(event):
    new = event["new"]
    lon.value = new[1]
    lat.value = new[0]
    sza, saa = clumping.calculate_solar_position(lon.value, lat.value, timer.value)
    json_widget.object = {"SZA": f"{sza:6.2f}", "SAA": f"{saa:6.2f}", 
                          "Lon": f"{lon.value:+6.2f}", "Lat": f"{lat.value:+6.2f}",
                         "UTC":timer.value.strftime("%Y-%m-%d %H:%M:%s"),
                         }
    

def on_time_changed(value):
    sza, saa = clumping.calculate_solar_position(lon.value, lat.value, timer.value)
    json_widget.object = {"SZA": f"{sza:6.2f}", "SAA": f"{saa:6.2f}",
                          "Lon": f"{lon.value:+6.2f}", "Lat": f"{lat.value:+6.2f}",
                         "UTC":timer.value.strftime("%Y-%m-%d %H:%M:%s"),
                         }
timer.param.watch(on_time_changed, 'value')
marker.observe(on_location_changed, 'location')
m.add_control(LayersControl(position='topright'))


interactive_simulations = pn.bind(do_sims, lon, lat, timer, 
                                  lam, lai, tsoil, tleaf, emv, 
                                  ems, hspot, lidfa, tleaf_sunlit,
                                  tsoil_sunlit, row_H, row_width, row_sep, row_angle)


template = pn.template.FastListTemplate(site="NCEO Airborne Facility",
                                        title="Brightness temperature simulations",
     sidebar=pn.Row(acquisition, architecture, thermodynamics, rows),
    main=pn.Column(m, pn.Row(pn.layout.HSpacer(),
                        interactive_simulations,
                             json_widget,
                        pn.layout.HSpacer(),
                        width=800,
                        height=600)),
    accent_base_color="#0a2d50",
    header_background="#e2231a"

).servable()
template.show()


# In[ ]:




