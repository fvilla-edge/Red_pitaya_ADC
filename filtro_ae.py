# filtro_ae.py
# Demostración de filtro pasa banda para señal AE
# Filtra entre 100 kHz y 450 kHz — rango del VS150-RI

import numpy as np
import matplotlib.pyplot as plt
from scipy import signal as sp

# ── Parámetros ─────────────────────────────────────────────────────
FS_EFECTIVA = 1_953_125   # Hz — Fs con decimación 64
N           = 16384
t           = np.linspace(0, N/FS_EFECTIVA, N)

FREQ_MIN    = 100_000     # Hz — límite inferior del filtro
FREQ_MAX    = 450_000     # Hz — límite superior del filtro
ORDEN       = 4           # orden del filtro — más alto = corte más abrupto
                          # pero puede volverse inestable con órdenes altos

# ── Diseño del filtro Butterworth pasa banda ───────────────────────
def disenar_filtro(freq_min, freq_max, fs, orden=4):
    """
    Diseña un filtro Butterworth pasa banda.
    Retorna coeficientes b, a para usar con scipy.signal.filtfilt.

    freq_min, freq_max: frecuencias de corte en Hz
    fs: frecuencia de muestreo en Hz
    orden: orden del filtro (4 es buen balance entre corte y estabilidad)
    """
    nyquist = fs / 2
    # Normalizar frecuencias respecto a Nyquist (scipy requiere 0–1)
    low     = freq_min / nyquist
    high    = freq_max / nyquist
    b, a    = sp.butter(orden, [low, high], btype='band')
    return b, a

def aplicar_filtro(signal_in, b, a):
    """
    Aplica el filtro a la señal usando filtfilt.
    filtfilt aplica el filtro dos veces (ida y vuelta) para
    eliminar el desfase de fase — la señal filtrada queda alineada
    en tiempo con la original.
    """
    return sp.filtfilt(b, a, signal_in)

# ── Señal de prueba con interferencias ────────────────────────────
def generar_señal_con_interferencias():
    """
    Genera una señal AE con tres tipos de interferencia:
    - 50 Hz: red eléctrica
    - 1 kHz: vibración mecánica del entorno
    - 600 kHz: interferencia de alta frecuencia (fuera del rango del sensor)
    """
    # Señal AE real (150 kHz con burst)
    envelope = np.exp(-t * 20_000)
    ae       = 3 * np.sin(2 * np.pi * 150_000 * t) * envelope

    # Interferencias
    red_electrica    = 1.5 * np.sin(2 * np.pi * 50 * t)        # 50 Hz
    vibracion        = 0.8 * np.sin(2 * np.pi * 1_000 * t)     # 1 kHz
    interferencia_hf = 0.6 * np.sin(2 * np.pi * 600_000 * t)   # 600 kHz

    # Ruido gaussiano de piso
    ruido = np.random.normal(0, 0.2, N)

    return ae + red_electrica + vibracion + interferencia_hf + ruido

# ── Comparar respuesta del filtro ──────────────────────────────────
def graficar_respuesta_filtro(b, a, fs):
    """
    Muestra cómo el filtro atenúa cada frecuencia.
    La línea azul debe estar cerca de 0 dB entre 100–450 kHz
    y caer abruptamente fuera de ese rango.
    """
    w, h = sp.freqz(b, a, worN=8000, fs=fs)
    return w, 20 * np.log10(np.abs(h) + 1e-10)   # convertir a dB

# ── Main ───────────────────────────────────────────────────────────
señal_original = generar_señal_con_interferencias()
b, a           = disenar_filtro(FREQ_MIN, FREQ_MAX, FS_EFECTIVA, ORDEN)
señal_filtrada = aplicar_filtro(señal_original, b, a)

# FFT de ambas señales para comparar espectros
def calcular_fft(sig):
    spectrum = np.abs(np.fft.rfft(sig)) / N
    freqs    = np.fft.rfftfreq(N, d=1/FS_EFECTIVA)
    return freqs, spectrum

freqs_o, spec_o = calcular_fft(señal_original)
freqs_f, spec_f = calcular_fft(señal_filtrada)
w, respuesta_db = graficar_respuesta_filtro(b, a, FS_EFECTIVA)

# ── Gráficos ───────────────────────────────────────────────────────
fig, axes = plt.subplots(4, 1, figsize=(11, 12))

# 1 — Señal original en tiempo
axes[0].plot(t[:1000] * 1e6, señal_original[:1000], linewidth=0.8, color='steelblue')
axes[0].set_title("Señal original — con interferencias de 50 Hz, 1 kHz y 600 kHz")
axes[0].set_ylabel("Voltaje (V)")
axes[0].set_xlabel("Tiempo (µs)")

# 2 — Señal filtrada en tiempo
axes[1].plot(t[:1000] * 1e6, señal_filtrada[:1000], linewidth=0.8, color='green')
axes[1].set_title("Señal filtrada — solo 100–450 kHz")
axes[1].set_ylabel("Voltaje (V)")
axes[1].set_xlabel("Tiempo (µs)")

# 3 — Espectro comparado (zoom en rango de interés)
axes[2].plot(freqs_o/1e3, spec_o, linewidth=0.8,
             color='steelblue', alpha=0.7, label='original')
axes[2].plot(freqs_f/1e3, spec_f, linewidth=0.8,
             color='green', label='filtrada')
axes[2].axvspan(0, 100,  alpha=0.1, color='red',   label='zona eliminada')
axes[2].axvspan(450, 700, alpha=0.1, color='red')
axes[2].set_xlim(0, 700)
axes[2].set_title("Espectro de frecuencias — comparación antes/después del filtro")
axes[2].set_ylabel("Magnitud")
axes[2].set_xlabel("Frecuencia (kHz)")
axes[2].legend(fontsize=9)

# 4 — Respuesta en frecuencia del filtro
axes[3].plot(w/1e3, respuesta_db, color='purple', linewidth=1)
axes[3].axvline(100, color='red', linewidth=1,
                linestyle='--', label='100 kHz')
axes[3].axvline(450, color='red', linewidth=1,
                linestyle='--', label='450 kHz')
axes[3].axhline(-3, color='orange', linewidth=0.8,
                linestyle=':', label='-3 dB (punto de corte)')
axes[3].set_xlim(0, 700)
axes[3].set_ylim(-80, 5)
axes[3].set_title("Respuesta en frecuencia del filtro Butterworth orden 4")
axes[3].set_ylabel("Atenuación (dB)")
axes[3].set_xlabel("Frecuencia (kHz)")
axes[3].legend(fontsize=9)

plt.tight_layout()
plt.savefig("filtro_ae.png", dpi=150)
print("Gráfico guardado como filtro_ae.png")

# ── Comparar SNR antes y después del filtro ────────────────────────
def calcular_snr(spectrum, freqs):
    mask      = (freqs >= FREQ_MIN) & (freqs <= FREQ_MAX)
    idx_pico  = np.argmax(spectrum[mask])
    mag_pico  = spectrum[mask][idx_pico]
    mag_ruido = np.mean(spectrum[~mask])
    return mag_pico / mag_ruido

snr_original = calcular_snr(spec_o, freqs_o)
snr_filtrada = calcular_snr(spec_f, freqs_f)

print(f"\nSNR sin filtro:  {snr_original:.1f}x")
print(f"SNR con filtro:  {snr_filtrada:.1f}x")
print(f"Mejora:          {snr_filtrada/snr_original:.1f}x mejor")