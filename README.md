# Claude-code

Proyectos web interactivos de un solo archivo.

## 🪐 Sistema Solar Explorador

`sistema_solar_explorador.html` — Escena 3D interactiva del sistema solar construida con [Three.js](https://threejs.org/).

**Características:**
- **Sol realista** con textura de gránulos solares, corona *fresnel*, resplandor y **post‑procesado de bloom**.
- Los 8 planetas con **texturas procedurales realistas**: continentes, océanos y nubes en la Tierra; bandas y Gran Mancha Roja en Júpiter; casquetes polares en Marte; cráteres en mundos rocosos; gigantes de hielo, etc.
- **Atmósferas con brillo** (shader fresnel), **anillos de Saturno y Urano** con divisiones reales (Cassini), la Luna terrestre y un **cinturón de asteroides** instanciado entre Marte y Júpiter.
- Tamaños proporcionales, velocidades orbitales distintas, rotación axial con inclinación real y **estrellas fugaces** aleatorias sobre un fondo de nebulosa y estrellas.
- **Etiquetas flotantes en 3D** sobre cada planeta y barra de navegación rápida para saltar a cualquier mundo.
- Click/tap → **vuelo de cámara suave** al planeta + panel *glassmorphism* con **mini‑planeta 3D girando en vivo**, ficha ampliada (distancia, diámetro, gravedad, temperatura, lunas, masa…), dato curioso y efecto de inclinación 3D.
- Zoom y rotación con mouse o gestos táctiles; botones para **parar/reanudar** órbitas, mostrar/ocultar trayectorias y etiquetas, **centrar** la vista, control de velocidad y contador de FPS.
- Responsivo y optimizado (DPR limitado, bloom y conteos reducidos en móvil, geometría adaptativa) para desktop y mobile.

Para usarlo, abre el archivo en cualquier navegador moderno con conexión a internet (carga Three.js desde CDN).

## 🏀 Basketball Legends 3D

`basketball_legends.html` — Una experiencia editorial inmersiva de la NBA con efectos de scroll 3D en un solo archivo.
