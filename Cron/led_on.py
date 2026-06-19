import sys
sys.path.append('/opt/redpitaya/lib/python') # Agrega el directorio de la biblioteca de Red Pitaya al path 
# sino el cron no lo dectecta
import rp

rp.rp_Init()
rp.rp_LEDSetState(0b00000001)
rp.rp_Release()

