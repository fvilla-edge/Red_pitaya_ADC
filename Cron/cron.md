# Cron

Cron es un servicio que ejecuta comandos o scripts automáticamente en horarios programados.

## Instalar
```bash 
apt-get install cron -y # instalar
systemctl enable cron # habilitar
systemctl start cron # arrcar
```

## Editar las tareas

```bash
crontab -e    # editar tareas del usuario actual
crontab -l    # listar tareas actuales
crontab -r    # borrar todas las tareas
```

## Estructura de una línea cron

```
┌─────────── minuto        (0 - 59)
│ ┌───────── hora          (0 - 23)
│ │ ┌─────── día del mes   (1 - 31)
│ │ │ ┌───── mes           (1 - 12)
│ │ │ │ ┌─── día semana    (0 - 7, donde 0 y 7 = domingo)
│ │ │ │ │
* * * * *  comando
```

## Ejemplos prácticos

### Hora específica todos los días

```bash
# Todos los días a las 13:00
0 13 * * * /usr/bin/python3 /root/relay_on.py

# Todos los días a las 18:30
30 18 * * * /usr/bin/python3 /root/relay_off.py
```

### Cada tantas horas

```bash
# Cada 2 horas
0 */2 * * * /usr/bin/python3 /root/script.py

# Cada 6 horas
0 */6 * * * /usr/bin/python3 /root/script.py

# Cada 12 horas
0 */12 * * * /usr/bin/python3 /root/script.py
```

### Cada tantos minutos

```bash
# Cada 15 minutos
*/15 * * * * /usr/bin/python3 /root/script.py

# Cada 30 minutos
*/30 * * * * /usr/bin/python3 /root/script.py
```

### Días específicos de la semana

```bash
# Solo los lunes a las 08:00
0 8 * * 1 /usr/bin/python3 /root/script.py

# Lunes, miércoles y viernes a las 10:00
0 10 * * 1,3,5 /usr/bin/python3 /root/script.py
```

### Al arrancar el sistema

```bash
# Se ejecuta cada vez que la Pitaya arranca
@reboot /usr/bin/python3 /root/script.py
```

## Caso de uso: Starlink con relay

Encender el Starlink a las 08:00 y apagarlo a las 14:00 todos los días:

```bash
0 8  * * * /usr/bin/python3 /root/relay_on.py
0 14 * * * /usr/bin/python3 /root/relay_off.py
```

Encender cada 6 horas durante 30 minutos:

```bash
0 */6 * * * /usr/bin/python3 /root/relay_on.py
30 */6 * * * /usr/bin/python3 /root/relay_off.py
```

## Importante para Red Pitaya

- Usar siempre la ruta completa de python3: `/usr/bin/python3`
- Usar siempre la ruta completa del script: `/root/script.py`
- La hora es UTC — Argentina (ART) es UTC-3, entonces las 13:00 ART son las 16:00 UTC
- Ver el log de ejecución: `grep CRON /var/log/syslog | tail -20`
- Cron no funciona si la placa está apagada (no tiene RTC)
