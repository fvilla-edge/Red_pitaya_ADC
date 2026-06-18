# analisis_desde_hdf5.py
# Lee eventos guardados en HDF5 y genera análisis completo

import numpy as np
import h5py
import matplotlib.pyplot as plt
from datetime import datetime

ARCHIVO = "eventos_ae_v2.h5"

def cargar_eventos(archivo):
    eventos = []

    with h5py.File(archivo, "r") as f:

        print("=== Metadata del archivo ===")
        for k, v in f.attrs.items():
            print(f"  {k}: {v}")

        print(f"\n=== Cargando {len(f.keys())} eventos ===")

        for nombre in sorted(f.keys()):
            ds = f[nombre]
            eventos.append({
                "nombre":    nombre,
                "signal":    ds[:],
                "timestamp": ds.attrs["timestamp"],
                "freq_pico": ds.attrs["freq_pico"],
                "snr":       ds.attrs["snr"],
                "mag_pico":  ds.attrs["mag_pico"],
                "mag_ruido": ds.attrs["mag_ruido"],
            })

    return eventos

def graficar(eventos):
    if len(eventos) == 0:
        print("No hay eventos para graficar")
        return

    indices    = list(range(len(eventos)))
    snrs       = [e["snr"]           for e in eventos]
    freqs      = [e["freq_pico"]/1e3 for e in eventos]
    mag_picos  = [e["mag_pico"]      for e in eventos]
    timestamps = [datetime.fromtimestamp(e["timestamp"]).strftime("%H:%M:%S")
                  for e in eventos]

    print(f"\n=== Estadísticas ===")
    print(f"SNR   — min: {min(snrs):.1f}x  max: {max(snrs):.1f}x  promedio: {np.mean(snrs):.1f}x")
    print(f"Freq  — min: {min(freqs):.1f} kHz  max: {max(freqs):.1f} kHz  promedio: {np.mean(freqs):.1f} kHz")

    fig, axes = plt.subplots(3, 1, figsize=(10, 8))

    # SNR por evento
    axes[0].bar(indices, snrs, color='steelblue', alpha=0.8)
    axes[0].set_ylabel("SNR")
    axes[0].set_title("SNR por evento")
    axes[0].set_xticks(indices)
    axes[0].set_xticklabels([e["nombre"] for e in eventos],
                             rotation=45, fontsize=8)

    # Frecuencia del pico
    axes[1].scatter(indices, freqs, color='purple', s=60, zorder=3)
    axes[1].axhline(150, color='gray', linewidth=1,
                    linestyle='--', label='150 kHz nominal')
    axes[1].set_ylabel("Frecuencia pico (kHz)")
    axes[1].set_title("Frecuencia del pico por evento")
    axes[1].set_xticks(indices)
    axes[1].set_xticklabels([e["nombre"] for e in eventos],
                             rotation=45, fontsize=8)
    axes[1].legend(fontsize=9)

    # Señal cruda del último evento
    ultimo  = eventos[-1]
    Fs_ef   = 1_953_125
    N       = len(ultimo["signal"])
    t_ms    = np.linspace(0, N/Fs_ef*1000, N)

    axes[2].plot(t_ms[:800], ultimo["signal"][:800],
                 linewidth=0.8, color='green')
    axes[2].set_xlabel("Tiempo (ms)")
    axes[2].set_ylabel("Voltaje (V)")
    axes[2].set_title(f"Señal cruda — {ultimo['nombre']} "
                      f"(SNR: {ultimo['snr']:.1f}x)")

    plt.tight_layout()
    plt.savefig("analisis_hdf5.png", dpi=150)
    print("Gráfico guardado como analisis_hdf5.png")

# ── Main ───────────────────────────────────────────────────────────
eventos = cargar_eventos(ARCHIVO)
graficar(eventos)