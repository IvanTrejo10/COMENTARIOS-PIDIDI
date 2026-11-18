# DATA · Alertas de recuperación

Panel local de Streamlit con la identidad visual de Estructuras RH: barra lateral azul marino, acentos turquesa y tarjetas independientes para México y LATAM.

## Uso

1. Abre `abrir_pagina.bat`.
2. Carga el PDF **Avance Cobranza y Entregado** en México, LATAM o ambos.
3. Pulsa **Generar mensajes**.
4. Revisa el corte y selecciona los países que quieres incluir.
5. Usa **Copiar mensaje**, **Copiar imagen** o **Descargar imagen** en cada tarjeta. También puedes descargar todos los seleccionados como ZIP o TXT.

Puedes generar una sola región. Si uno de los PDF falla, el otro se procesa de forma independiente. Se valida que cada archivo corresponda a su tarjeta. Si cambias o quitas un PDF, los resultados anteriores se ocultan hasta que vuelvas a generar.

Los países sin movimiento y los excluidos en `config_alertas.json` siguen las reglas del motor original. Los PDF se procesan en una carpeta temporal; los resultados permanecen en memoria durante la sesión y la caché dura como máximo una hora. La aplicación prepara el contenido; el envío a WhatsApp se realiza manualmente.

Si el navegador impide copiar una imagen, descárgala o haz clic derecho sobre ella y selecciona **Copiar imagen**.

## Instalación manual

Requiere Python 3.10 o posterior.

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Mantén juntos `app.py`, `ui.py`, `assets/`, `alertas_cobranza.py`, `config_alertas.json`, `requirements.txt` y `.streamlit/`. El motor y sus reglas de redacción siguen en `alertas_cobranza.py`.

La alternativa de línea de comandos con `generar_alertas.bat` se conserva.
