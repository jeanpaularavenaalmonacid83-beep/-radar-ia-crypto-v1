# Radar IA Crypto — V1 (simulador educativo)

Este prototipo está diseñado para abrirse desde el teléfono Android usando un navegador y desplegarse en Streamlit Community Cloud. No ejecuta compras ni ventas reales.

## Qué incluye
- Saldo inicial ficticio de 100 SOL.
- Vista demo con tokens totalmente ficticios.
- Modo experimental para consultar candidatos de Pump.fun mediante endpoints públicos de DexScreener.
- Filtros de liquidez y volumen 24h.
- Puntuación heurística (no es un modelo predictivo).
- Compras y ventas simuladas, supuestos de costos, posiciones abiertas y registro CSV.
- Límite de 2 SOL por operación.
- No solicita claves privadas ni conecta billeteras.

## Importante sobre el modo en vivo
El prototipo consulta tokens recientemente promocionados en DexScreener y luego busca pares Solana cuyo identificador DEX contenga `pump`. Es una exploración parcial y sesgada, NO un feed completo de todos los tokens de Pump.fun. Los endpoints públicos pueden cambiar, limitar solicitudes o no devolver resultados. La API de precios no garantiza que una orden real pueda ejecutarse a ese precio.

## Costos de simulación
- Comisión asumida: 1% por lado.
- Deslizamiento asumido: 1% por lado.
Estos valores son supuestos editables para evitar que la simulación ignore costos; no representan una tarifa real universal.

## Archivos
- `app.py`: aplicación principal.
- `requirements.txt`: dependencias.
- `README.md`: instrucciones y limitaciones.

## Cómo desplegarlo desde Android
1. Inicia sesión o crea una cuenta de GitHub.
2. Crea un repositorio nuevo, por ejemplo `radar-ia-crypto-v1`.
3. Sube `app.py`, `requirements.txt` y `README.md` desde el navegador del teléfono.
4. Entra en Streamlit Community Cloud y conecta GitHub.
5. Crea una app seleccionando tu repositorio y `app.py`.
6. Espera a que termine la instalación. Abre la URL de la app en tu teléfono.
7. Empieza con **Demo (segura)**. Después prueba **Intentar datos en vivo**.

No añadas claves privadas, frases semilla ni contraseñas al repositorio. Este prototipo no necesita ninguna.

## Siguiente etapa recomendada
Añadir persistencia real (SQLite o una base de datos administrada), captura continua de datos y pruebas históricas con precios observados. Antes de confiar en el resultado, probar deslizamiento variable, liquidez insuficiente, fallos de API y tokens que colapsan.
