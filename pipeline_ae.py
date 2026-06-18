# pipeline_ae.py
# Pipeline completo de detección y guardado de emisiones acústicas

import numpy as np
import h5py
import time
# import rp  # ← descomentar cuando corra en la STEMlab

# ── Parámetros del sistema ─────────────────────────────────────────
FS          = 125_000_000   # Hz — frecuencia de muestreo STEMlab
DECIMACION  = 64            # Fs efectiva = 125MHz / 64 = ~1.95 MHz
FS_EFECTIVA = FS / DECIMACION
N           = 16384         # muestras por evento
FREQ_SENSOR = 150_000       # Hz — frecuencia nominal VS150-RI
FREQ_MIN    = 100_000       # Hz — rango mínimo del sensor
FREQ_MAX    = 450_000       # Hz — rango máximo del sensor
UMBRAL_SNR  = 5             # ajustar con datos reales
ARCHIVO     = "eventos_ae.h5"

# ── Adquisición ────────────────────────────────────────────────────
def adquirir_señal():

    # ── SIMULADO ──────────────────────────────────────────────────
    # Comentar este bloque cuando corra en la STEMlab
    t        = np.linspace(0, N/FS_EFECTIVA, N)
    amp      = np.random.uniform(1, 8)
    ruido    = np.random.uniform(0.3, 2.0)
    envelope = np.exp(-t * 20_000)
    signal   = amp * np.sin(2 * np.pi * FREQ_SENSOR * t) * envelope
    signal  += np.random.normal(0, ruido, N)
    return signal
    # ── FIN SIMULADO ──────────────────────────────────────────────

    # ── HARDWARE REAL ─────────────────────────────────────────────
    # Descomentar cuando corra en la STEMlab
    # buff = rp.Buffer(N)
    # rp.rp_AcqGetOldestDataV(rp.RP_CH_1, N, buff)
    # return np.array(buff)
    # ── FIN HARDWARE REAL ─────────────────────────────────────────

# ── Detección ──────────────────────────────────────────────────────
def analizar(signal):
    spectrum = np.abs(np.fft.rfft(signal)) / N
    freqs    = np.fft.rfftfreq(N, d=1/FS_EFECTIVA)

    mask      = (freqs >= FREQ_MIN) & (freqs <= FREQ_MAX)
    idx_pico  = np.argmax(spectrum[mask])
    freq_pico = freqs[mask][idx_pico]
    mag_pico  = spectrum[mask][idx_pico]
    mag_ruido = np.mean(spectrum[~mask])
    snr       = mag_pico / mag_ruido

    return {
        "freq_pico": freq_pico,
        "mag_pico":  mag_pico,
        "mag_ruido": mag_ruido,
        "snr":       snr,
        "evento":    snr > UMBRAL_SNR
    }

# ── Guardado ───────────────────────────────────────────────────────
def guardar(f, signal, resultado, contador):
    nombre = f"evento_{contador:04d}"
    ds     = f.create_dataset(nombre, data=signal)
    ds.attrs["timestamp"]  = time.time()
    ds.attrs["freq_pico"]  = resultado["freq_pico"]
    ds.attrs["mag_pico"]   = resultado["mag_pico"]
    ds.attrs["mag_ruido"]  = resultado["mag_ruido"]
    ds.attrs["snr"]        = resultado["snr"]
    return nombre

# ── Inicialización STEMlab ─────────────────────────────────────────
def configurar_stemlab():
    # Descomentar cuando corra en la STEMlab
    # rp.rp_Init()
    # rp.rp_AcqSetGain(rp.RP_CH_1, rp.RP_LOW)  # RP_HIGH si la señal supera ±1V
    # rp.rp_AcqSetDecimation(DECIMACION)
    # rp.rp_AcqSetTriggerSrc(rp.RP_TRIG_SRC_CHA_PE)
    # rp.rp_AcqSetTriggerLevel(rp.RP_T_CH_1, 0.05)  # 50 mV — ajustar con datos reales
    # rp.rp_AcqStart()
    pass

def liberar_stemlab():
    # Descomentar cuando corra en la STEMlab
    # rp.rp_Release()
    pass

# ── Loop principal ─────────────────────────────────────────────────
def main(n_adquisiciones=20):
    configurar_stemlab()

    with h5py.File(ARCHIVO, "w") as f:

        f.attrs["sensor"]      = "VS150-RI"
        f.attrs["dcpl"]        = "DCPL2"
        f.attrs["fs_hz"]       = FS
        f.attrs["fs_ef_hz"]    = FS_EFECTIVA
        f.attrs["decimacion"]  = DECIMACION
        f.attrs["n_muestras"]  = N
        f.attrs["umbral_snr"]  = UMBRAL_SNR
        f.attrs["fecha"]       = time.strftime("%Y-%m-%d %H:%M:%S")

        contador    = 0
        descartados = 0

        print(f"Iniciando adquisición — {n_adquisiciones} ciclos")
        print(f"Fs efectiva: {FS_EFECTIVA/1e3:.0f} kHz — umbral SNR: {UMBRAL_SNR}x")
        print("─" * 55)

        for i in range(n_adquisiciones):
            signal    = adquirir_señal()
            resultado = analizar(signal)

            if resultado["evento"]:
                nombre = guardar(f, signal, resultado, contador)
                print(f"[{i+1:02d}] {nombre} — "
                      f"SNR: {resultado['snr']:.1f}x — "
                      f"freq: {resultado['freq_pico']/1000:.1f} kHz")
                contador += 1
            else:
                descartados += 1
                print(f"[{i+1:02d}] descartado — SNR: {resultado['snr']:.1f}x")

        print("─" * 55)
        print(f"Guardados: {contador} — Descartados: {descartados}")
        print(f"Archivo: {ARCHIVO}")

    liberar_stemlab()

if __name__ == "__main__":
    main(n_adquisiciones=100)