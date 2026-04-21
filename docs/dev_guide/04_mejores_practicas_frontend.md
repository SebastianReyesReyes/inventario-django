# Mejores Prácticas del Frontend (HTMX y UI)

Al carecer de un framework pesado del lado del cliente como ReactJS, todas nuestras resoluciones interactivas se resuelven orquestando inteligentemente atributos `hx-*` (HTMX), Alpine.js como puente para variables de estado locales e interactividad del micro-DOM, y Tailwind.

## Reglas UI de "Consola de Precisión"

El diseño visual de la "Consola de Precisión" es la cara principal del proyecto. Implementa su UI siguiendo estas directivas:
1. **Glassmorphism:** Las cajas de métricas (Cards) y Modales implementan la clase `backdrop-blur-md bg-opacity-70`. En `dark mode`, esto genera una interfaz elegante apoyada sobre una paleta muy delimitada.
2. **Micro-animaciones:** Toda alteración u hover del cursor debe generar reacciones en la página (`transform transition-transform hover:scale-105 duration-200`).
3. **Skeleton Loading:** Es recomendable utilizar `htmx:configRequest` y targeters como clases globales `htmx-indicator` o `skeleton` que enmarcan la barra de carga mientras HTMX viaja por el servidor, dando fluidez y omitiendo que parezca un salto de página brutal.

## Implementaciones y Arquitectura HTMX

### 1. Refresco Orientado a Objetos Ocultos (Hidden Targets)
En modales de catálogos y mantenimiento hemos prescindido de respuestas complejas o reemplazo agresivo sobre `<main>`. 
La regla es: Cuando se requiere manipular una entidad vía modal (como *Añadir Colaborador*):
* Se añade `hx-target="#modal-dialog"` para que el HTML se inyecte al div de Alpine `x-show="isModalOpen"`.
* Tras la inserción del guardado y de un POST resuelto por Django (`200 OK`), la vista HTMX actualiza silenciosamente un div general `id="table-container"` vía OOB (`hx-swap-oob`) o a través de eventos HTTP Custom Response Headers:
  `HX-Trigger: recordChanged`
Al llegar el header `recordChanged`, el grid sabe que debe volver a fetchear los datos de su propia tabla.

## Uso de Alpine.js (`x-data`)
Evita extenderte en Javascript Vanilla en archivos separados (`scripts.js`), alójalo de preferencia con Alpine:
1. Validaciones reactivas simples (`x-bind:disabled="..."`).
2. Toggles de clases (Modales abiertos / cerrados / barras superpuestas de navegación).
3. Componentes personalizados sin API, como es el caso del **Autocompletado Personalizado** para asignaciones de catálogos (Búsqueda de Empleados) donde HTMX requiere filtrar la petición POST sobre selecciones.
