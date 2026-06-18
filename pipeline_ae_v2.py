# pipeline_ae_v2.py
# Pipeline definitivo de detección y guardado de emisiones acústicas
# Hardware: Red Pitaya STEMlab 125-14 + sensor VS150-RI + acondicionador DCPL2
# Ejecutar en la STEMlab via SSH: python3 pipeline_ae_v2.py
# Detener con Ctrl+C — el archivo HDF5 se cierra correctamente al salir

import numpy as np      # operaciones matemáticas y FFT
import h5py             # guardado de datos en formato HDF5
import time             # timestamps y pausas
import threading        # dos hilos corriendo en paralelo
import queue            # cola de comunicación entre hilos
# import rp            # librería Red Pitaya — descomentar cuando corra en la STEMlab

# ── Parámetros del sistema ─────────────────────────────────────────
# Modificar estos valores para calibrar el sistema con datos reales

FS          = 125_000_000   # frecuencia de muestreo de la STEMlab en Hz (fija en hardware)
DECIMACION  = 64            # divisor de Fs — debe ser potencia de 2 (1,2,4,8...65536)
                            # Fs efectiva = 125MHz / 64 = ~1.95 MHz
                            # decimación máxima para cubrir el VS150-RI (450 kHz)
                            # si se usa decimación > 64 el sensor deja de ser visible (Nyquist)
FS_EFECTIVA = FS / DECIMACION
N           = 16384         # muestras por captura — determina resolución de la FFT
                            # resolución frecuencial = Fs_efectiva / N = ~119 Hz por bin
FREQ_SENSOR = 150_000       # frecuencia de resonancia nominal del VS150-RI en Hz
FREQ_MIN    = 100_000       # límite inferior del rango del sensor en Hz
FREQ_MAX    = 450_000       # límite superior del rango del sensor en Hz
UMBRAL_SNR  = 5             # relación señal/ruido mínima para considerar un evento válido
                            # SNR = magnitud del pico / promedio del ruido de piso
                            # calibrar con los primeros datos reales del sensor
ARCHIVO     = "eventos_ae_v2.h5"   # nombre del archivo de salida

# ── Cola entre hilos ───────────────────────────────────────────────
# El hilo de captura pone señales acá, el hilo de análisis las lee
# maxsize=100 significa que si el análisis se atrasa más de 100 capturas
# las nuevas capturas se descartan (se registra en total_perdidos)
cola = queue.Queue(maxsize=100)

# Event para coordinar el apagado limpio — corriendo.clear() detiene ambos hilos
corriendo = threading.Event()
corriendo.set()

# Lock para modificar contadores desde dos hilos sin conflictos
lock           = threading.Lock()
total_capturas = 0   # cuántas veces capturó el hilo de captura
total_eventos  = 0   # cuántos eventos superaron el umbral SNR y se guardaron
total_perdidos = 0   # cuántas capturas se descartaron por cola llena

# ── Adquisición de señal ───────────────────────────────────────────
def adquirir_señal():
    """
    Retorna un array numpy con N muestras de voltaje.
    En simulación genera una señal AE sintética.
    En hardware real lee directamente del ADC de la STEMlab.
    """
    # ── SIMULADO ──────────────────────────────────────────────────
    # Genera una señal tipo burst similar a la del VS150-RI
    # amp y ruido aleatorios simulan variabilidad de eventos reales
    t        = np.linspace(0, N/FS_EFECTIVA, N)
    amp      = np.random.uniform(0.5, 8)       # amplitud aleatoria entre 0.5 y 8 V
    ruido    = np.random.uniform(0.3, 2.5)     # nivel de ruido aleatorio
    envelope = np.exp(-t * 20_000)             # decaimiento exponencial — forma del burst
    signal   = amp * np.sin(2 * np.pi * FREQ_SENSOR * t) * envelope
    signal  += np.random.normal(0, ruido, N)   # ruido gaussiano de piso
    time.sleep(0.01)                           # simula tiempo de captura real (~10ms)
    return signal
    # ── FIN SIMULADO ──────────────────────────────────────────────

    # ── HARDWARE REAL ─────────────────────────────────────────────
    # Descomentar estas líneas y comentar el bloque simulado
    # cuando el pipeline corra en la STEMlab con el sensor conectado
    # buff = rp.Buffer(N)
    # rp.rp_AcqGetOldestDataV(rp.RP_CH_1, N, buff)
    # return np.array(buff)
    # ── FIN HARDWARE REAL ─────────────────────────────────────────

# ── Análisis de la señal ───────────────────────────────────────────
def analizar(signal):
    """
    Calcula la FFT de la señal y detecta si hay un evento AE.

    Proceso:
    1. FFT — convierte la señal de dominio tiempo a dominio frecuencia
    2. Busca el pico máximo dentro del rango del sensor (100–450 kHz)
    3. Calcula el SNR comparando ese pico con el ruido fuera del rango
    4. Decide si es evento según el umbral SNR configurado

    Retorna diccionario con freq_pico, magnitudes, snr y bool evento.
    """
    # FFT — rfft es la versión optimizada para señales reales (no complejas)
    spectrum = np.abs(np.fft.rfft(signal)) / N   # dividir por N para normalizar
    freqs    = np.fft.rfftfreq(N, d=1/FS_EFECTIVA)   # eje de frecuencias en Hz

    # Máscara booleana: True en los bins dentro del rango del sensor
    mask      = (freqs >= FREQ_MIN) & (freqs <= FREQ_MAX)

    # Encontrar el bin con mayor magnitud dentro del rango
    idx_pico  = np.argmax(spectrum[mask])
    freq_pico = freqs[mask][idx_pico]     # frecuencia del pico en Hz
    mag_pico  = spectrum[mask][idx_pico]  # magnitud del pico

    # Ruido de piso: promedio de todo lo que está FUERA del rango del sensor
    mag_ruido = np.mean(spectrum[~mask])

    # SNR: cuántas veces más grande es el pico que el ruido de piso
    snr = mag_pico / mag_ruido

    return {
        "freq_pico": freq_pico,   # Hz — dónde está el pico
        "mag_pico":  mag_pico,    # magnitud del pico (adimensional, normalizado)
        "mag_ruido": mag_ruido,   # magnitud promedio del ruido de piso
        "snr":       snr,         # relación señal/ruido
        "evento":    snr > UMBRAL_SNR   # True si supera el umbral
    }

# ── Hilo 1: captura continua ───────────────────────────────────────
def hilo_captura():
    """
    Corre en paralelo con hilo_analisis.
    Captura señales sin parar y las pone en la cola.
    Si la cola está llena (análisis atrasado), descarta la captura
    en lugar de bloquear — así nunca frena la adquisición.
    """
    global total_capturas, total_perdidos

    while corriendo.is_set():
        signal    = adquirir_señal()
        timestamp = time.time()   # marca de tiempo de la captura

        try:
            # put_nowait: intenta agregar a la cola sin esperar
            # si está llena lanza queue.Full en lugar de bloquear
            cola.put_nowait((signal, timestamp))
            with lock:
                total_capturas += 1
        except queue.Full:
            with lock:
                total_perdidos += 1
            print("⚠ cola llena — captura descartada")

# ── Hilo 2: análisis y guardado ────────────────────────────────────
def hilo_analisis(archivo_h5):
    """
    Corre en paralelo con hilo_captura.
    Lee señales de la cola, las analiza con FFT y guarda
    en HDF5 solo las que superan el umbral SNR.
    Sigue corriendo hasta que corriendo se apague Y la cola esté vacía
    — así no se pierden eventos que quedaron en la cola al detener.
    """
    global total_eventos
    contador = 0   # índice del evento para nombrar datasets en HDF5

    while corriendo.is_set() or not cola.empty():
        try:
            # Espera hasta 1 segundo por un item en la cola
            # timeout evita que el hilo quede bloqueado para siempre
            signal, timestamp = cola.get(timeout=1)
        except queue.Empty:
            continue   # no había nada, volver a intentar

        resultado = analizar(signal)

        if resultado["evento"]:
            # Guardar en HDF5 — cada evento es un dataset separado
            nombre = f"evento_{contador:04d}"   # evento_0000, evento_0001...
            ds     = archivo_h5.create_dataset(nombre, data=signal)

            # Metadata del evento — queda pegada al dataset en el HDF5
            ds.attrs["timestamp"]  = timestamp              # tiempo Unix de la captura
            ds.attrs["freq_pico"]  = resultado["freq_pico"] # Hz
            ds.attrs["snr"]        = resultado["snr"]        # relación señal/ruido
            ds.attrs["mag_pico"]   = resultado["mag_pico"]   # magnitud del pico
            ds.attrs["mag_ruido"]  = resultado["mag_ruido"]  # ruido de piso

            with lock:
                total_eventos += 1

            # Mostrar hora legible en lugar de timestamp Unix
            hora = time.strftime("%H:%M:%S", time.localtime(timestamp))
            print(f"[{hora}] {nombre} — "
                  f"SNR: {resultado['snr']:.1f}x — "
                  f"freq: {resultado['freq_pico']/1000:.1f} kHz — "
                  f"cola: {cola.qsize()}")
            contador += 1

        # Marcar el item como procesado — necesario para cola.join()
        cola.task_done()

# ── Configuración STEMlab ──────────────────────────────────────────
def configurar_stemlab():
    """
    Inicializa la STEMlab y configura el ADC.
    Descomentar cuando el pipeline corra en la STEMlab.

    Ganancia: RP_LOW = ±1V, RP_HIGH = ±20V
    Empezar con RP_LOW — cambiar a RP_HIGH si hay clipping.

    Trigger level: 50 mV inicial — calibrar con datos reales.
    Si hay muchos falsos positivos: subir el valor.
    Si se pierden eventos débiles: bajarlo.
    """
    # rp.rp_Init()
    # rp.rp_AcqSetGain(rp.RP_CH_1, rp.RP_LOW)
    # rp.rp_AcqSetDecimation(DECIMACION)
    # rp.rp_AcqSetTriggerSrc(rp.RP_TRIG_SRC_CHA_PE)  # trigger por flanco positivo en CH1
    # rp.rp_AcqSetTriggerLevel(rp.RP_T_CH_1, 0.05)   # 50 mV
    # rp.rp_AcqSetTriggerDelay(-1000)  # negativo = muestras ANTES del trigger
    # rp.rp_AcqStart()

    pass

def liberar_stemlab():
    """Libera los recursos de la STEMlab al terminar."""
    # rp.rp_Release()
    pass

# ── Main ───────────────────────────────────────────────────────────
def main():
    """
    Punto de entrada del pipeline.
    Crea el archivo HDF5, arranca los dos hilos y espera Ctrl+C.
    Al detener: espera que el hilo de análisis vacíe la cola
    y cierra el HDF5 correctamente antes de salir.
    """
    configurar_stemlab()

    with h5py.File(ARCHIVO, "w") as f:

        # Metadata global del archivo — describe las condiciones de medición
        f.attrs["sensor"]     = "VS150-RI"
        f.attrs["dcpl"]       = "DCPL2"
        f.attrs["fs_hz"]      = FS
        f.attrs["fs_ef_hz"]   = FS_EFECTIVA
        f.attrs["decimacion"] = DECIMACION
        f.attrs["n_muestras"] = N
        f.attrs["umbral_snr"] = UMBRAL_SNR
        f.attrs["fecha"]      = time.strftime("%Y-%m-%d %H:%M:%S")

        # Crear hilos
        # daemon=True en captura: si el programa muere, ese hilo muere también
        t_captura  = threading.Thread(target=hilo_captura,
                                      name="captura", daemon=True)
        t_analisis = threading.Thread(target=hilo_analisis,
                                      args=(f,), name="analisis")

        print(f"Pipeline iniciado — Fs efectiva: {FS_EFECTIVA/1e3:.0f} kHz")
        print(f"Umbral SNR: {UMBRAL_SNR}x — guardando en: {ARCHIVO}")
        print("Presioná Ctrl+C para detener")
        print("─" * 55)

        t_captura.start()
        t_analisis.start()

        try:
            while True:
                time.sleep(1)   # espera indefinidamente hasta Ctrl+C
        except KeyboardInterrupt:
            print("\nDeteniendo — esperando que se vacíe la cola...")
            corriendo.clear()   # señal a ambos hilos para que terminen

        # Esperar que el hilo de análisis termine de procesar
        # lo que quedó en la cola antes de cerrar el HDF5
        t_analisis.join()

    liberar_stemlab()

    print("─" * 55)
    print(f"Capturas totales:  {total_capturas}")
    print(f"Eventos guardados: {total_eventos}")
    print(f"Capturas perdidas: {total_perdidos}")
    print(f"Archivo:           {ARCHIVO}")

if __name__ == "__main__":
    main()