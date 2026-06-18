import h5py
import numpy as np

with h5py.File("eventos_ae_v2.h5", "r") as f:

    print("=== METADATA DEL ARCHIVO ===")
    for k, v in f.attrs.items():
        print(f"  {k}: {v}")

    print(f"\n=== EVENTOS GUARDADOS: {len(f.keys())} ===")
    for nombre in f.keys():
        ds = f[nombre]
        signal = ds[:]   # cargar las muestras a un array numpy

        print(f"\n{nombre}")
        print(f"  timestamp:  {ds.attrs['timestamp']}")
        print(f"  freq pico:  {ds.attrs['freq_pico']/1000:.1f} kHz")
        print(f"  SNR:        {ds.attrs['snr']:.1f}x")
        print(f"  muestras:   {len(signal)}")
        print(f"  min/max:    {signal.min():.4f} / {signal.max():.4f} V")
        print(f"  RMS:        {np.sqrt(np.mean(signal**2)):.4f} V")