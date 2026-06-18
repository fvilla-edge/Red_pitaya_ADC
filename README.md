# Sistema de Detección de Emisiones Acústicas
## STEMlab 125-14 + VS150-RI + DCPL2

---

## Hardware

| Componente | Detalle |
|-----------|---------|
| Placa | Red Pitaya STEMlab 125-14 |
| Sensor | Vallen VS150-RI |
| Acondicionador | Vallen DCPL2 |
| Conexión | DCPL2 salida BNC → adaptador BNC-SMA → STEMlab IN1 |

---

## Parámetros del sistema

| Parámetro | Valor | Motivo |
|-----------|-------|--------|
| Fs STEMlab | 125 MHz | fijo en hardware |
| Decimación | 64 | Fs efectiva ~1.95 MHz, mínimo para cubrir 450 kHz |
| Fs efectiva | 1.953 MHz | 125 MHz / 64 |
| N muestras | 16384 | resolución frecuencial ~119 Hz por bin |
| Rango sensor | 100–450 kHz | rango nominal VS150-RI |
| Frecuencia pico | ~150 kHz | resonancia del VS150-RI |
| Ganancia inicial | RP_LOW (±1V) | cambiar a RP_HIGH si hay clipping |
| Trigger level | 50 mV | calibrar con datos reales |
| Umbral SNR | 5x | calibrar con datos reales |
| Pre-trigger | 1000 muestras | captura 512 µs antes del evento |

---

## Estructura del archivo HDF5

```
eventos_ae_v2.h5
│
├── [metadata global]
│     sensor, dcpl, fs_hz, fs_ef_hz, decimacion
│     n_muestras, umbral_snr, fecha
│
├── evento_0000
│     timestamp   → cuándo ocurrió el evento (tiempo Unix)
│     freq_pico   → frecuencia del pico detectado en Hz
│     snr         → relación señal/ruido
│     mag_pico    → magnitud del pico (normalizada)
│     mag_ruido   → magnitud promedio del ruido de piso
│     + array de 16384 muestras de señal cruda en voltios
│
└── evento_NNNN
      ...
```

---

## Conceptos clave

**SNR (Signal to Noise Ratio)** — relación señal a ruido.
`SNR = magnitud del pico / promedio del ruido de piso`
SNR > 5x → evento detectado. Calibrar con datos reales.

**Decimación** — divisor de la frecuencia de muestreo. Debe ser potencia de 2.
Decimación 64 es el máximo para cubrir el VS150-RI (450 kHz).
Si se usa decimación > 64 el sensor deja de ser visible (violación de Nyquist).

**HDF5** — formato de archivo para datos científicos.
Estructura jerárquica: metadata global + datasets individuales por evento.
Cada evento tiene su señal cruda + metadata asociada.
Ventajas sobre CSV: 10x más rápido, 10x menos espacio, acceso directo por índice.

---

## Instalación de dependencias en la STEMlab

Conectarse por SSH y ejecutar:

```bash
# numpy ya viene instalado pero puede necesitar downgrade
pip install "numpy<2" --break-system-packages   # tarda ~20 min en ARM

# h5py — usar apt para evitar compilación larga
apt-get install python3-h5py

# si apt-get da conflicto de versiones con numpy, usar pip
pip install h5py --break-system-packages        # tarda ~15 min en ARM
```

Verificar que todo funciona:

```bash
python3 -c "import numpy, h5py; print('OK')"
```

---

## Copiar archivos entre PC y STEMlab

```bash
# Copiar script de tu PC a la STEMlab
scp archivo.py root@192.168.x.xx:/root/

# Copiar HDF5 de la STEMlab a tu PC (ejecutar desde tu PC)
scp root@192.168.x.xx:/root/eventos_ae_v2.h5 .

# Si aparece warning de host key cambiada (después de actualizar SO)
ssh-keygen -f '/home/x/.ssh/known_hosts' -R '192.168.x.xx'
```

---

## Cuando lleguen los adaptadores BNC-SMA — pasos exactos

### Paso 1 — Verificar conexión física
```
DCPL2 salida BNC → adaptador BNC-SMA → STEMlab IN1
Verificar que el DCPL2 esté alimentado y el sensor conectado.
```

### Paso 2 — Diagnóstico inicial
Conectar el sensor sin generar eventos.
Ejecutar en la STEMlab via SSH:

```bash
python3 diagnostico.py
```

Resultados esperados sin evento:
- Offset < 50 mV
- RMS muy bajo (< 0.05 V)
- Clipping = 0 muestras

### Paso 3 — Primera captura con evento
Golpear suavemente la estructura donde está montado el sensor.
Verificar que el Max sube respecto al ruido de piso.

### Paso 4 — Activar pipeline real
En `pipeline_ae_v2.py` hacer 3 cambios:

**Cambio 1** — descomentar el import arriba del todo:
```python
import rp
```

**Cambio 2** — en `adquirir_señal()`, comentar bloque simulado
y descomentar bloque hardware real:
```python
def adquirir_señal():
    buff = rp.Buffer(N)
    rp.rp_AcqGetOldestDataV(rp.RP_CH_1, N, buff)
    return np.array(buff)
```

**Cambio 3** — descomentar el interior de `configurar_stemlab()`
y `liberar_stemlab()`.

### Paso 5 — Calibrar umbrales
Observar los primeros eventos reales y ajustar en `pipeline_ae_v2.py`:
```python
UMBRAL_SNR  = 5      # subir si hay falsos positivos
                     # bajar si se pierden eventos débiles
```
Y en `configurar_stemlab()`:
```python
rp.rp_AcqSetTriggerLevel(rp.RP_T_CH_1, 0.05)  # ajustar en voltios
```

### Paso 6 — Si hay interferencias (opcional)
Si el SNR es bajo o el espectro muestra ruido fuera del rango del sensor,
integrar el filtro Butterworth de `filtro_ae.py` al pipeline.

---

## Problemas comunes y soluciones

| Problema | Síntoma | Solución |
|---------|---------|---------|
| No se detectan eventos | SNR siempre < 5x | Bajar UMBRAL_SNR o verificar conexión |
| Demasiados falsos positivos | Eventos sin causa real | Subir UMBRAL_SNR o TRIGGER_mV |
| Clipping | Max = 1.0V exacto, señal plana | Cambiar a RP_HIGH |
| Offset alto | Mean > 50 mV | Verificar DCPL2, corregir por software |
| Pico fuera de rango | Pico no está en 100–450 kHz | Verificar decimación y conexión |
| Sin señal | RMS ≈ 0 | Verificar alimentación DCPL2 |
| h5py no importa | Error numpy.core.multiarray | `pip install "numpy<2" --break-system-packages` |
| Warning host key SSH | REMOTE HOST IDENTIFICATION HAS CHANGED | `ssh-keygen -f ~/.ssh/known_hosts -R 192.168.0.55` |

---

## Comandos útiles

```bash
# Conectar a la STEMlab
ssh root@192.168.x.xx

# Correr el pipeline (en la STEMlab)
python3 pipeline_ae_v2.py

# Copiar HDF5 a tu PC (desde tu PC)
scp root@192.168.x.xx:/root/eventos_ae_v2.h5 .

# Analizar datos (en tu PC o en la STEMlab)
python3 analisis_desde_hdf5.py

# Ver contenido del HDF5
python3 leer_ae.py
```