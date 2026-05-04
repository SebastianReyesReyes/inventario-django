## 2024-05-04 - [Missing Security Flags]
**Vulnerability:** Cookies sin Secure flag
**Learning:** En entornos de produccion, SESSION_COOKIE_SECURE y CSRF_COOKIE_SECURE deben estar en True para asegurar que las cookies se transmitan por HTTPs
**Prevention:** Configurar cookies con Secure y definir HSTS
