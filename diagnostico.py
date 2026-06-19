# diagnostico.py
# Verificar que el sensor y la conexión funcionan correctamente
# Ejecutar ANTES de correr el pipeline, con el sensor conectado pero sin generar eventos
# Si algo no está en rango, revisar la tabla de problemas comunes del README

import rp
import numpy as np

GANANCIA   = rp.RP_HIGH   # RP_LOW = ±1V, RP_HIGH = ±20V
                          # VS150-RI con DCPL2 puede llegar a 15V pico a pico — usar HIGH
DECIMACION = 64
N          = 16384
LIMITE_ADC = 19.5         # V — umbral de clipping para RP_HIGH (margen de 0.5V sobre ±20V)

print("Iniciando diagnóstico...")
print(f"Ganancia: {'±1V (RP_LOW)' if GANANCIA == rp.RP_LOW else '±20V (RP_HIGH)'}")
print("─" * 40)

rp.rp_Init()
rp.rp_AcqSetGain(rp.RP_CH_1, GANANCIA)
rp.rp_AcqSetDecimation(DECIMACION)
rp.rp_AcqSetTriggerSrc(rp.RP_TRIG_SRC_NOW)
rp.rp_AcqStart()

import time
time.sleep(0.1)

rp.rp_AcqSetTriggerSrc(rp.RP_TRIG_SRC_NOW)
buff   = rp.Buffer(N)
rp.rp_AcqGetOldestDataV(rp.RP_CH_1, N, buff)
signal = np.array(buff)

rp.rp_Release()

# ── Resultados ─────────────────────────────────────────────────────
offset   = np.mean(signal) * 1000
rms      = np.sqrt(np.mean(signal**2))
clipping = np.sum((signal >= LIMITE_ADC) | (signal <= -LIMITE_ADC))
pico     = signal.max() - signal.min()

print(f"Offset:   {offset:.1f} mV  {'⚠ corregir — verificar DCPL2' if abs(offset) > 50 else 'OK'}")
print(f"RMS:      {rms:.4f} V      {'⚠ señal alta sin evento' if rms > 0.1 else 'OK'}")
print(f"Max:      {signal.max():.4f} V")
print(f"Min:      {signal.min():.4f} V")
print(f"Pico a pico: {pico:.4f} V")
print(f"Clipping: {clipping} muestras  {'⚠ señal supera ±20V — problema de hardware' if clipping > 0 else 'OK'}")

print("─" * 40)
if abs(offset) < 50 and rms < 0.1 and clipping == 0:
    print("Todo OK — podés correr el pipeline")
else:
    print("Hay problemas — revisá la tabla del README antes de continuar")