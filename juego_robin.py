# Traer funciones de librería
import os
import pygame
from math import sin

# Traer específicamente una función del módulo pygame
from random import randint, random

# Inicializar pygame
pygame.init()
font = pygame.font.Font(None, 72)
font_peq = pygame.font.Font(None, 28)   # texto pequeño: avisos, diálogos y contador

# Ajustes generales
win_width = 800
win_height = 600
left_bound = win_width / 40
right_bound = win_width - 8 * left_bound
shift = 0
gravedad = 0.25
salto = -8
h_width = 40          # ancho/alto de referencia de Robin: solo para colocar su punto de aparición
h_height = 55         # (el dibujo usa el PNG de 64x64 sin deformarlo; ver ROBIN_ESCALA)
hit_width = 28        # tamaño de la HITBOX (el cuerpo de Robin)
hit_height = 45
FPS = 60
zoom = 1.8

# ---------------------------------------------------------------------------
# MAPA
# Todas las coordenadas del mapa están medidas sobre la imagen COMPLETA de
# 1748 x 900 px de la referencia (márgenes rocosos incluidos). NO hay que sumar
# márgenes. Si tu archivo de fondo tuviera otro tamaño, todo se reescala solo.
# Las plataformas se midieron sobre los píxeles de los trazos rojos (centro del
# trazo), no a ojo: cada una empieza y acaba donde empieza y acaba su trazo.
# ---------------------------------------------------------------------------
REF_W, REF_H = 1748, 900

# Área jugable = borde verde de la imagen anotada (coordenadas de la imagen)
BORDE_IZQ, BORDE_DER = 180, 1611
BORDE_SUP, BORDE_INF = 100, 852

# Ajustes de colisión
PASO_MAX = 8                # desnivel máximo que Robin sube/baja caminando (px)
TOLERANCIA_ATERRIZAJE = 4   # margen para aterrizar justo en la superficie (px)
PIE_MITAD = 6               # medio ancho de la zona de "pies" que se apoya (px)
COYOTE_FRAMES = 6           # frames para saltar tras caminar fuera de un borde
SALTO_CORTE = -3            # velocidad máx. de subida al soltar ESPACIO (salto variable)
ZONA_MUERTE_MARGEN = 40     # px por debajo de BORDE_INF antes de perder una vida
MARGEN_EXTREMO = 3          # se recorta el redondeo del pincel rojo en cada extremo
GROSOR_DEBUG = 6
MURO_TOL_CABEZA = 28        # px: una pared cuya punta solo llega a la parte alta del cuerpo de Robin no le bloquea (rocas colgantes)
MURO_TOL_PIES = 8           # px: una pared que solo sobresale esa altura sobre sus pies es un escalón, no un muro
VEL_ROBIN = 5               # velocidad horizontal de Robin (para calcular el paso en rampas empinadas)
ESCUDO_VEL = 0.6            # fracción de la velocidad con la que Robin camina mientras se cubre con el escudo
debug = False               # F1 muestra/oculta plataformas, hitbox y paredes

# Bajar entre plataformas (SHIFT)
DROP_TOL = 14               # px: plataformas a esta distancia bajo los pies se atraviesan
DROP_MARGEN = 6             # px que los pies deben pasar bajo la superficie antes de volver a ser sólida
DROP_EMPUJE = 3             # px que se hunde Robin al empezar a bajar
DROP_VEL = 2                # velocidad vertical inicial al bajar

# ---------------------------------------------------------------------------
# CONTROLES (cada acción admite varias teclas). Cambia aquí lo que quieras.
# ---------------------------------------------------------------------------
CONTROLES = {
    "izquierda": [pygame.K_LEFT],
    "derecha": [pygame.K_RIGHT],
    "saltar": [pygame.K_SPACE],
    "atacar": [pygame.K_x],                  # zarpazo desde el inicio; con la espada pega más fuerte
    "defender": [pygame.K_c],                # MANTENER (puedes caminar cubierto); solo tras conseguir el escudo
    "interactuar": [pygame.K_e],             # hablar con aliados
    "curar": [pygame.K_q],                   # beber una poción de vida (cuando TÚ decides)
    "avanzar_dialogo": [pygame.K_e, pygame.K_RETURN],
    "bajar": [pygame.K_LSHIFT, pygame.K_RSHIFT],   # atravesar plataforma hacia abajo
    "depurar": [pygame.K_F1],
    "reiniciar": [pygame.K_r],
    "salir": [pygame.K_ESCAPE],              # cerrar el juego desde la pantalla de victoria/derrota
}


def pulsada(teclas, accion):
    # True si alguna tecla de la acción está mantenida (teclas = get_pressed())
    return any(teclas[k] for k in CONTROLES[accion])


def es_tecla(tecla, accion):
    # True si la tecla de un evento KEYDOWN/KEYUP pertenece a la acción
    return tecla in CONTROLES[accion]


def nombre_tecla(accion):
    # Nombre legible de la primera tecla de la acción (para los textos)
    n = pygame.key.name(CONTROLES[accion][0]).upper()
    return n.replace("LEFT ", "").replace("RIGHT ", "").replace("ESCAPE", "ESC")

# ---------------------------------------------------------------------------
# AJUSTES DE JUEGO FÁCILES DE MODIFICAR
# ---------------------------------------------------------------------------
# Zona del jamón (se desbloquea con recolectables)
REQ_TIPO = "cristal"             # clave de TIPOS_ITEM que hay que reunir
REQ_CANTIDAD = 10                # cuántos hacen falta para abrir la zona (en el mapa hay 11)
AVISO_FRAMES = 180               # duración de los avisos (3 s a 60 FPS)
ZONA_EMPUJE_MAX = 40             # px máximos que se empuja a Robin fuera de la zona cerrada

# Vidas
max_vidas = 7                    # vidas máximas = corazones en pantalla
INVULN_FRAMES = 75               # invulnerabilidad tras recibir daño
KNOCK_ROBIN = 5                  # empuje horizontal de Robin al ser golpeado

# Ataque de Robin: zarpazo desde el inicio del juego; con la espada pega más fuerte
ATAQUE_DURACION = 18             # frames que dura el golpe
ATAQUE_ACTIVO = (3, 14)          # frames (desde el inicio) en que el golpe hace daño (ventana amplia: pega con fiabilidad)
ATAQUE_RECUPERACION = 25         # frames extra de espera tras el golpe (cooldown configurable)
ATAQUE_ALCANCE = 42              # px de alcance de la ESPADA frente a Robin
ATAQUE_ALCANCE_ZARPAZO = 34      # px de alcance del zarpazo sin espada
DANO_ZARPAZO = 2                 # daño sin espada: ENEMIGO_VIDA / 2 = 3 golpes para matar
DANO_ESPADA = 3                  # daño con espada: ENEMIGO_VIDA / 3 = 2 golpes para matar

# Enemigos (solo cuerpo a cuerpo)
ENEMIGO_TAM = (40, 40)           # tamaño VISIBLE (cuadrado: el PNG de 64x64 no se deforma)
ENEMIGO_HIT = (28, 36)           # tamaño de su cuerpo (hitbox): torso y cabeza del orco, sin las armas ni las orejas
ENEMIGO_VIDA = 6                 # sin espada 3 zarpazos (2 de daño); con espada 2 golpes (3 de daño)
ENEMIGO_VEL = 1.5                # velocidad de patrulla
ENEMIGO_VEL_ATAQUE = 2.2         # velocidad al acercarse a Robin
ENEMIGO_DETECCION = 130          # distancia horizontal a la que ve a Robin (px)
ENEMIGO_ALTURA_DETECCION = 40    # diferencia vertical máxima para verlo (px)
ENEMIGO_ALCANCE = 34             # distancia a la que empieza a golpear (px entre centros)
ENEMIGO_ALCANCE_GOLPE = 20       # alcance de la zona de impacto desde su cuerpo (px)
ENEMIGO_PREPARAR = 20            # frames de preparación del golpe
ENEMIGO_GOLPE = 8                # frames en que la zona de impacto está activa
ENEMIGO_RECUPERACION = 180       # COOLDOWN del enemigo tras cada golpe (180 frames = 3 s): ahí no ataca
ENEMIGO_ATURDIDO = 22            # frames aturdido al ser golpeado o bloqueado
ENEMIGO_EMPUJE = 2.5             # retroceso al recibir un golpe (poco: así no se sale del alcance y el siguiente golpe conecta)
ENEMIGO_DANO = 1

# Pociones de vida: los enemigos las sueltan al morir, se recogen del suelo y se
# guardan; NO se beben solas: las bebes tú con la tecla "curar"
DROP_POCION_PROB = 0.5           # probabilidad de que un enemigo suelte una poción (0 a 1)
POCION_CURA = 2                  # corazones que cura cada poción
POCIONES_MAX = 9                 # máximo de pociones que se pueden llevar
POCIONES_REGALO = 5              # pociones que regala el aliado de la orilla (consejo_b)
POCION_TAM = (26, 26)            # caja donde cabe la poción (se recorta y se escala sin deformar)

# Jefe final: orco perro que lanza rocas. Solo se le puede dañar mientras
# está en RECUPERACIÓN (cooldown tras lanzar). Cada roca sin escudo = 3 corazones
JEFE_VIDA = 20                   # vida del jefe: 10 golpes con espada o 20 zarpazos sin ella
JEFE_DANO_ESPADA = 2             # daño de Robin al jefe con espada
JEFE_DANO_ZARPAZO = 1            # daño de Robin al jefe sin espada
JEFE_TAM = (110, 110)            # tamaño VISIBLE (cuadrado: el PNG de 64x64 no se deforma)
JEFE_HIT = (70, 95)              # tamaño de su cuerpo (zona donde le llega la espada)
JEFE_ESPERA_INICIAL = 70         # frames que tarda en atacar desde que Robin entra en la arena
JEFE_ESPERA = 45                 # frames de pausa entre tandas de ataque
JEFE_PREPARAR = 40               # frames de preparación antes de cada roca (animación "lanzar")
JEFE_ENTRE_ROCAS = 25            # frames entre roca y roca de una misma tanda
JEFE_ROCAS_POR_ATAQUE = 2        # rocas por tanda
JEFE_COOLDOWN = 150              # frames de RECUPERACIÓN tras la tanda: ahora se le puede dañar
JEFE_MUERTE_FRAMES = 90          # duración de la animación de derrota
JEFE_ROCA_DANO = 3               # corazones que quita una roca si no la bloqueas con el escudo
JEFE_ROCA_VUELO = 42             # frames que tarda la roca en llegar hasta Robin
JEFE_ROCA_GRAVEDAD = 0.2
JEFE_ROCA_DISPERSION = 14        # px de imprecisión al apuntar
JEFE_ROCA_TAM = (30, 30)
JEFE_ROCA_ORIGEN = (35, 20)      # de dónde sale la roca: (px delante del centro, px bajo la cabeza)
JEFE_BARRA_ANCHO = 260           # barra de vida del jefe (posición fija en pantalla)
JEFE_NOMBRE = "Orco perro"
# Arena del jefe (coordenadas de la imagen): el jefe solo ataca si Robin está dentro
JEFE_ARENA = (1160, 640, 1611, 852)
# Posición del jefe (centro, pies sobre el suelo de la cueva)
JEFE_POS = (1490, 822)

# Diálogos
DIALOGO_VELOCIDAD = 1.6          # letras por frame (máquina de escribir)

# Estilo de los cuadros de interfaz (gris claro translúcido, borde pixel art)
UI_FONDO = (205, 205, 212, 220)
UI_BORDE_OSCURO = (45, 40, 70)
UI_BORDE_CLARO = (245, 245, 252)
UI_ACENTO = (110, 190, 255)
UI_TEXTO = (30, 28, 45)

# ---------------------------------------------------------------------------
# RECURSOS (PNG): TODAS las rutas están aquí. Sustituye un archivo manteniendo
# el nombre o cambia la ruta en estos diccionarios. Si falta un archivo se usa
# un cuadro magenta y se avisa por consola (el juego no se cierra).
# ---------------------------------------------------------------------------
# Las rutas se calculan desde la carpeta donde está ESTE archivo, no desde la
# carpeta desde la que se lanza Python: así los PNG se encuentran siempre,
# lo ejecutes desde VS Code, IDLE o la terminal.
try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    BASE_DIR = os.getcwd()
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
MIRAN_A_LA_DERECHA = True        # los sprites originales miran a la derecha


def ruta(*partes):
    return os.path.join(ASSETS_DIR, *partes)


# Fondo del mapa
img_back = os.path.join(BASE_DIR, "mapinha.png")   # IMPORTANTE: la imagen LIMPIA (sin líneas rojas ni verdes), junto a este archivo

# Bomba (trampa) y jamón (objetivo final). OJO: el PNG del jamón conserva el nombre
# original "princesa.png" (es el sprite del jamón; puedes renombrarlo y cambiar la ruta aquí)
img_bomb = ruta("items", "bomba.png")
img_jamon = ruta("npcs", "princesa.png")
JAMON_CAJA = (56, 56)            # caja donde cabe el jamón (se recorta y se escala sin deformar)
JAMON_POS = (1440, 822)          # centro de los pies del jamón (coordenadas de la imagen del mapa)

# Animaciones de Robin: 5 estados. Cada una con "archivos" (lista de PNG) o con
# "hoja" (spritesheet: "frame_w", "frame_h", "cantidad"). "fps" y "loop" opcionales.
ANIM_ROBIN = {
    "idle": {"archivos": [ruta("player", "idle_0.png")], "fps": 4, "loop": True},
    "walk": {"archivos": [ruta("player", "walk_0.png"), ruta("player", "walk_1.png")],
             "fps": 8, "loop": True},
    "jump": {"archivos": [ruta("player", "jump_0.png")], "fps": 4, "loop": True},
    # Ataque CON espada (attack_*) y SIN espada, solo zarpazo (attack_No_*)
    "attack": {"archivos": [ruta("player", "attack_0.png"), ruta("player", "attack_1.png"),
                            ruta("player", "attack_2.png")],
               "loop": False, "duracion_frames": ATAQUE_DURACION},
    "attack_no": {"archivos": [ruta("player", "attack_No_0.png"), ruta("player", "attack_No_1.png"),
                               ruta("player", "attack_No_2.png")],
                  "loop": False, "duracion_frames": ATAQUE_DURACION},
    "shield": {"archivos": [ruta("player", "shield_0.png")], "fps": 4, "loop": True},
}
ESCALAR_ROBIN = True             # True: cada cuadro se escala por ROBIN_ESCALA (siempre cuadrado: no se deforma)
ROBIN_ESCALA = 1.0               # 1.0 = el PNG de 64x64 se dibuja tal cual (pixel perfect)
ROBIN_TAM = (round(64 * ROBIN_ESCALA), round(64 * ROBIN_ESCALA))

# Animaciones de enemigos: 2 estados (patrulla y ataque)
ANIM_ENEMIGO = {
    "patrulla": {"archivos": [ruta("enemies", "patrulla_0.png"), ruta("enemies", "patrulla_1.png")],
                 "fps": 6, "loop": True},
    "ataque": {"archivos": [ruta("enemies", "ataque_0.png"), ruta("enemies", "ataque_1.png")],
               "fps": 8, "loop": True},
}

# Animaciones del jefe (4 estados): es el MISMO orco de los enemigos, solo que más grande.
# Si algún día haces PNG propios, cambia aquí las rutas por assets/boss/...
ANIM_JEFE = {
    "idle": {"archivos": [ruta("enemies", "patrulla_0.png"), ruta("enemies", "patrulla_1.png")],
             "fps": 4, "loop": True},
    "lanzar": {"archivos": [ruta("enemies", "ataque_0.png"), ruta("enemies", "ataque_1.png")],
               "fps": 8, "loop": True},
    "cooldown": {"archivos": [ruta("enemies", "patrulla_1.png"), ruta("enemies", "patrulla_0.png")],
                 "fps": 3, "loop": True},
    "muerte": {"archivos": [ruta("enemies", "ataque_0.png"), ruta("enemies", "patrulla_1.png"),
                            ruta("enemies", "ataque_1.png")],
               "loop": False, "duracion_frames": JEFE_MUERTE_FRAMES},
}
JEFE_ROCA_ARCHIVO = ruta("boss", "roca.png")

# Tipos de objeto recolectable (se pueden añadir más tipos aquí). "tam" es la caja donde
# cabe el sprite (se recorta lo transparente y se escala sin deformar)
TIPOS_ITEM = {
    "cristal": {"nombre": "cristales mágicos", "archivo": ruta("items", "cristal.png"),
                "tam": (28, 28), "valor": 1},
}
# Los 4 diseños de cristal (colores distintos). Se reparten por el mapa en el orden de
# CRISTAL_ORDEN (índices de esta lista); el orden no es el 1-2-3-4 de siempre
CRISTAL_DISENOS = [
    ruta("items", "recompensa_01.png"),
    ruta("items", "recompensa_02.png"),
    ruta("items", "recompensa_03.png"),
    ruta("items", "recompensa_04.png"),
]
CRISTAL_ORDEN = [0, 2, 1, 3, 1, 0, 3, 2, 0, 1, 3]   # un diseño por cada cristal de ITEMS_MAPA

# Iconos de objetos que concede un NPC (se muestran en la interfaz al obtenerlos)
ASSETS_OBJETOS = {
    "espada": ruta("items", "espada.png"),
    "escudo": ruta("items", "escudo.png"),
    "pocion": ruta("items", "pocion.png"),     # poción de vida (suelo e interfaz)
}

# Interfaz
ASSETS_UI = {
    "corazon_lleno": ruta("ui", "corazon_lleno.png"),
    "corazon_vacio": ruta("ui", "corazon_vacio.png"),
}
CORAZON_TAM = (32, 32)           # caja del corazón (se recorta y se escala sin deformar)
NPC_TAM = (64, 64)               # lienzo del aliado dibujado tal cual (1:1)
ICONO_TAM = (28, 28)             # caja de los iconos de objetos de la interfaz

# Estado de la partida
vidas = max_vidas           # vidas iniciales = máximo (una sola constante)
ultimo_golpe = 0            # (se conserva por compatibilidad; la invulnerabilidad va en Hero)
contadores = {}             # recolectables reunidos por tipo, p. ej. {"cristal": 3}
objetos = {"espada": False, "escudo": False, "kit_pociones": False}   # objetos entregados por los aliados
pociones = 0                # pociones de vida guardadas (se beben con la tecla "curar")
jamon_visible = False       # el jamón no aparece hasta derrotar al jefe
zona_bloqueada = True       # la zona del jamón empieza cerrada
fin_tipo = None             # None mientras se juega; "victoria" o "derrota" en la pantalla final
fin_t = 0                   # frames desde que empezó la pantalla final (animaciones)

# Colores
C_BLACK = (0, 0, 0)
C_RED = (255, 0, 0)
C_GREEN = (32, 128, 32)

# Pone el nombre de la ventana
pygame.display.set_caption("Arcade")

# Crea nuestra ventana y la establece en un tamaño específico
window = pygame.display.set_mode([win_width, win_height])

# Cargamos la imagen del mapa (ya NO se escala al tamaño de la ventana)
back = pygame.image.load(img_back).convert()

# Dimensiones reales del mapa, leídas de la propia imagen
map_width, map_height = back.get_size()
sx = map_width / REF_W
sy = map_height / REF_H
escala_mapa = sx

# Cámara: zona del mundo que se ve en pantalla = ventana / zoom
view_w = int(win_width / zoom) + 1     # 445 px de mundo
view_h = int(win_height / zoom) + 1    # 334 px de mundo
world_surface = pygame.Surface((view_w, view_h))
cam_x = 0
cam_y = 0


# ---------------------------------------------------------------------------
# TEXTOS (diálogos, avisos y pistas). Edita aquí sin tocar la lógica.
# Variables disponibles: {atacar} {defender} {interactuar} {bajar} {saltar}
# {cantidad} {objeto} {actual} {curar} {pociones} {golpes_zarpazo} {golpes_espada}
# ---------------------------------------------------------------------------
TEXTOS = {
    "zona_bloqueada": "Necesitas reunir {cantidad} {objeto} para desbloquear esta zona ({actual}/{cantidad}).",
    "zona_desbloqueada": "¡La barrera mágica se ha desvanecido! Ya puedes entrar en la cueva del jamón.",
    "npc_espada": {
        "nombre": "Guardián de la espada",
        "primera": [
            "Te estaba esperando, pequeño Robin. La cueva está llena de criaturas hostiles.",
            "Toma esta espada. Ahora es tuya.",
            "¡Has recibido la ESPADA! Tus ataques ({atacar}) ahora pegan más fuerte: los enemigos caen con {golpes_espada} golpes en vez de {golpes_zarpazo}.",
        ],
        "despues": ["Ya tienes mi espada. Pulsa {atacar} para usarla y ten cuidado con los enemigos."],
    },
    "npc_escudo": {
        "nombre": "Guardián del escudo",
        "primera": [
            "Valiente gato, para sobrevivir no basta con atacar.",
            "Este escudo detendrá los golpes de frente.",
            "¡Has recibido el ESCUDO! Mantén {defender} para cubrirte (en el suelo). Puedes caminar con el escudo levantado, pero más despacio.",
        ],
        "despues": ["Mantén {defender} para cubrirte. Solo te protege de los golpes que vienen de frente."],
    },
    "npc_consejo_a": {
        "nombre": "Aliada del bolsillo",
        "primera": [
            "El jefe te espera en la gran cueva de abajo a la derecha. El jamón no aparecerá hasta que lo derrotes.",
            "La entrada está sellada con magia. Reúne {cantidad} {objeto} repartidos por la cueva para abrirla. Ya llevas {actual}.",
            "El orco perro lanza rocas: sin escudo, cada una te quita 3 corazones. Cúbrete con {defender} y golpéalo cuando se canse de lanzar.",
            "La espada y el escudo te los darán los guardianes de los extremos de la cueva.",
        ],
        "despues": ["Llevas {actual} de {cantidad} {objeto}. Cúbrete con {defender} ante las rocas y ataca al orco cuando se canse."],
    },
    "npc_consejo_b": {
        "nombre": "Aliada de la orilla",
        "primera": [
            "Los monstruos patrullan sus plataformas. Si te ven, te atacarán cuerpo a cuerpo.",
            "Algunos sueltan pociones de vida al caer. Recógelas del suelo, pero ojo: no se beben solas.",
            "Toma, te regalo {pociones_regalo} pociones de vida.",
            "¡Has recibido {pociones_regalo} POCIONES! Pulsa {curar} para beber una y recuperar corazones cuando tú decidas.",
        ],
        "despues": ["Llevas {pociones} pociones. Pulsa {curar} para beber una cuando lo necesites."],
    },
    # Mensajes de la interfaz y diálogo de inicio (se muestra al empezar y al reiniciar)
    "intro": {
        "nombre": "Robin",
        "primera": [
            "Un delicioso jamón descansa al fondo de esta cueva encantada, y un orco perro vigila su puerta. ¡Tienes que conseguirlo!",
            "Muévete con las flechas y salta con {saltar}. Para bajar de una plataforma sin saltar al vacío, pulsa {bajar} sobre ella.",
            "Ataca con {atacar}: sin espada necesitas {golpes_zarpazo} zarpazos por enemigo. Habla con los aliados con {interactuar}.",
            "Las pociones de vida las beberás con {curar} cuando tú decidas.",
            "Reúne {cantidad} {objeto} para abrir la entrada de la cueva del jefe. ¡Buena suerte!",
        ],
    },
    "jefe_guardia": "¡El orco se protege mientras lanza rocas! Golpéalo cuando se canse y baje la guardia.",
    "jamon_aparece": "¡El orco ha caído! El jamón aparece en el centro de la cueva: ve a por él.",
    "pocion_recogida": "Recogiste una poción de vida (llevas {pociones}). Pulsa {curar} para beberla cuando quieras.",
    "pocion_curar": "Bebes una poción y recuperas corazones. Te quedan {pociones}.",
    "sin_pociones": "No tienes pociones de vida.",
    "vida_completa": "Ya tienes la vida completa.",
    # Pantallas finales: título, líneas de texto y la indicación de teclas
    "fin_victoria": {
        "titulo": "¡VICTORIA!",
        "lineas": [
            "Robin ha vencido al orco perro y conquistado la cueva encantada.",
            "¡Por fin el jamón es tuyo! Fin de la aventura.",
        ],
    },
    "fin_derrota": {
        "titulo": "HAS CAÍDO",
        "lineas": [
            "La cueva se queda en silencio y la luz de los cristales se apaga...",
            "El jamón tendrá que esperar. ¡Vuelve a intentarlo!",
        ],
    },
    "fin_pie": "[{reiniciar}] Jugar de nuevo        [{salir}] Salir",
}

# ---------------------------------------------------------------------------
# UTILIDADES DE IMÁGENES Y ANIMACIÓN
# ---------------------------------------------------------------------------


def cargar_imagen(archivo, tam=None, respaldo=None):
    # Carga un PNG con transparencia. Si falta, prueba el respaldo y, si
    # tampoco existe, devuelve un cuadro magenta (nunca cierra el juego)
    try:
        img = pygame.image.load(archivo).convert_alpha()
    except (pygame.error, FileNotFoundError, OSError):
        img = None
        if respaldo:
            try:
                img = pygame.image.load(respaldo).convert_alpha()
            except (pygame.error, FileNotFoundError, OSError):
                img = None
        if img is None:
            print("AVISO: no se pudo cargar", archivo, "-> comprueba que la carpeta assets esté junto a este archivo")
            img = pygame.Surface(tam or (32, 32), pygame.SRCALPHA)
            img.fill((255, 0, 255, 255))
    if tam:
        img = pygame.transform.scale(img, tam)
    return img


def recortar_alpha(img):
    # Quita el margen transparente alrededor del dibujo (el PNG de 64x64 suele tener aire)
    r = img.get_bounding_rect()
    if r.width == 0 or r.height == 0:
        return img
    return img.subsurface(r).copy()


def recortar_pies(img):
    # Quita solo las filas transparentes BAJO los pies: así el borde inferior de la imagen
    # es el suelo y el personaje se apoya exactamente sobre la plataforma
    r = img.get_bounding_rect()
    if r.width == 0 or r.height == 0:
        return img
    return img.subsurface(pygame.Rect(0, 0, img.get_width(), r.bottom)).copy()


def cargar_ajustada(archivo, caja, respaldo=None):
    # Carga un PNG, recorta lo transparente y lo escala PARA QUE CABA en "caja"
    # conservando su proporción (sin estirarlo). Escalado sin suavizar (pixel art)
    img = recortar_alpha(cargar_imagen(archivo, None, respaldo))
    w, h = img.get_size()
    k = min(caja[0] / w, caja[1] / h)
    return pygame.transform.scale(img, (max(1, round(w * k)), max(1, round(h * k))))


def cargar_frames(cfg, tam=None, respaldo=None):
    # Devuelve la lista de cuadros de una animación (archivos sueltos o hoja)
    respaldo = cfg.get("respaldo", respaldo)
    if "hoja" in cfg:
        hoja = cargar_imagen(cfg["hoja"], None, respaldo)
        fw, fh = cfg["frame_w"], cfg["frame_h"]
        frames = []
        for i in range(cfg["cantidad"]):
            f = hoja.subsurface(pygame.Rect(i * fw, 0, fw, fh)).copy()
            frames.append(pygame.transform.scale(f, tam) if tam else f)
        return frames
    return [cargar_imagen(a, tam, respaldo) for a in cfg["archivos"]]


class Animacion:
    # Una secuencia de cuadros. Guarda también la versión espejo (izquierda)
    def __init__(self, frames, fps=8, loop=True, duracion_frames=None):
        self.der = frames
        self.izq = [pygame.transform.flip(f, True, False) for f in frames]
        if duracion_frames:
            self.ticks = max(1.0, duracion_frames / len(frames))
        else:
            self.ticks = max(1.0, FPS / fps)
        self.loop = loop
        self.t = 0

    def reiniciar(self):
        self.t = 0

    def avanzar(self):
        self.t += 1

    def imagen(self, direccion):
        i = int(self.t / self.ticks)
        n = len(self.der)
        i = i % n if self.loop else min(i, n - 1)
        mira_der = (direccion >= 0) == MIRAN_A_LA_DERECHA
        return (self.der if mira_der else self.izq)[i]


class Animador:
    # Conjunto de animaciones por estado: solo guarda cuál se reproduce
    def __init__(self, definiciones, tam=None, respaldo=None, estado="idle"):
        self.anims = {}
        for nombre, cfg in definiciones.items():
            # Cada cuadro se recorta bajo los pies: así siempre se apoya en el suelo
            frames = [recortar_pies(f) for f in cargar_frames(cfg, tam, respaldo)]
            self.anims[nombre] = Animacion(
                frames, cfg.get("fps", 8), cfg.get("loop", True),
                cfg.get("duracion_frames")
            )
        self.estado = estado

    def set(self, estado):
        if estado != self.estado:
            self.estado = estado
            self.anims[estado].reiniciar()

    def forzar(self, estado):
        self.estado = estado
        self.anims[estado].reiniciar()

    def tick(self):
        self.anims[self.estado].avanzar()

    def imagen(self, direccion):
        return self.anims[self.estado].imagen(direccion)


def colision_hitbox(a, b):
    # Compara la HITBOX de "a" (Robin) con el rect de "b"
    return a.hitbox.colliderect(b.rect)


def punto_en_poligono(px, py, poly):
    # Algoritmo del rayo: True si el punto (px, py) está dentro del polígono
    dentro = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > py) != (yj > py):
            if px < (xj - xi) * (py - yi) / (yj - yi) + xi:
                dentro = not dentro
        j = i
    return dentro


class Jamon(pygame.sprite.Sprite):
    # Objetivo final del juego. (x, y_pies) = centro de los pies sobre el suelo
    def __init__(self, archivo, x, y_pies, caja=JAMON_CAJA):
        super().__init__()
        self.image = cargar_ajustada(archivo, caja)
        # Consigue el rectángulo de nuestra imagen (apoyado sobre el suelo)
        self.rect = self.image.get_rect(midbottom=(x, y_pies))


class Hero(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height):
        super().__init__()
        # Animaciones por estado (IDLE, WALK, JUMP, ATTACK, SHIELD) desde ANIM_ROBIN
        tam = ROBIN_TAM if ESCALAR_ROBIN else None
        self.animador = Animador(ANIM_ROBIN, tam, None, "idle")
        self.estado = "idle"
        self.image = self.animador.imagen(1)
        # self.rect = SOLO dibujo. Las colisiones usan self.hitbox. El dibujo se
        # ancla siempre por el centro de los pies, así cambiar de imagen (aunque
        # tenga otro tamaño) no mueve a Robin
        self.rect = self.image.get_rect(topleft=(x, y))

        # Hitbox 28 x 45: centrada en el sprite y con los pies a ras del
        # borde inferior de la imagen, así se ve apoyado sobre la plataforma
        self.hitbox = pygame.Rect(0, 0, hit_width, hit_height)
        self.hitbox.midbottom = (x + width // 2, y + height)
        self.rect.midbottom = self.hitbox.midbottom
        self.pos_y = float(self.hitbox.y)   # posición vertical con decimales

        self.x_speed = 0
        self.y_speed = 0
        self.direction = 1

        # Variable para saber si se encuentra sobre alguna plataforma
        self.stands_on = False
        # Frames restantes para poder saltar tras salirse de un borde
        self.coyote = 0

        # Plataformas que se están atravesando hacia abajo (SHIFT)
        self.ignoradas = set()

        # Combate
        self.atq_frame = -1          # -1 = no está atacando
        self.atq_cooldown = 0
        self.golpeados = set()
        self.defendiendo = False
        self.invuln = 0
        self.empuje = 0.0
        self.moviendose = False

        # Aviso de zona cerrada
        self.toco_barrera = False

    # Una función dentro de una clase es un método
    def gravitate(self):
        self.y_speed += gravedad

    # Método para saltar
    def jump(self, y):
        if self.defendiendo:
            return
        # Comprobamos si nos encontramos sobre una plataforma para brincar
        # (o si acabamos de salir de su borde: coyote). Nunca en pleno aire.
        if self.stands_on or self.coyote > 0:
            self.y_speed = y
            self.stands_on = False
            self.coyote = 0

    # Salto variable: al soltar ESPACIO durante el ascenso se frena la subida.
    # Pulsación rápida = salto corto; mantener ESPACIO = salto completo (-8).
    # Solo actúa si Robin sigue subiendo más rápido que SALTO_CORTE, así que
    # no puede alargar un salto ni saltar en el aire.
    def cut_jump(self):
        if self.y_speed < SALTO_CORTE:
            self.y_speed = SALTO_CORTE

    # Zona de muerte: devuelve a Robin al punto inicial con el estado limpio
    def respawn(self, x, y):
        self.hitbox.midbottom = (x + h_width // 2, y + h_height)
        self.pos_y = float(self.hitbox.y)
        self.x_speed = 0
        self.y_speed = 0
        self.stands_on = False
        self.coyote = 0
        self.ignoradas = set()
        self.atq_frame = -1
        self.atq_cooldown = 0
        self.defendiendo = False
        self.empuje = 0.0
        self.invuln = INVULN_FRAMES        # un momento de gracia al reaparecer
        self.sincronizar()

    def sincronizar(self):
        # Mantiene el sprite alineado con la hitbox
        self.hitbox.y = round(self.pos_y)
        self.rect.midbottom = self.hitbox.midbottom

    def plataformas_bajo_pies(self):
        # Plataformas cuya superficie queda bajo los pies de Robin
        # (se excluyen las que está atravesando hacia abajo)
        centro = self.hitbox.centerx
        return [
            p for p in barriers
            if p.x0 - PIE_MITAD <= centro <= p.x1 + PIE_MITAD
            and p not in self.ignoradas
        ]

    # ------------------------------------------------------------------
    # ENTRADA Y COMBATE
    # ------------------------------------------------------------------
    def leer_entrada(self, teclas):
        # Movimiento horizontal leído de las teclas mantenidas (más fiable que
        # los eventos si se pulsan izquierda y derecha a la vez)
        self.defendiendo = bool(
            pulsada(teclas, "defender") and objetos["escudo"]
            and self.stands_on and self.atq_frame < 0
        )
        d = (1 if pulsada(teclas, "derecha") else 0) \
            - (1 if pulsada(teclas, "izquierda") else 0)
        # Con el escudo levantado Robin SÍ puede caminar (más despacio) y girarse
        self.x_speed = d * VEL_ROBIN * (ESCUDO_VEL if self.defendiendo else 1)
        if d:
            self.direction = d

    def bajar_plataforma(self):
        # SHIFT: atraviesa hacia abajo la plataforma sobre la que está. Solo
        # actúa con un pulso de la tecla (KEYDOWN, sin repetición), y solo
        # sobre plataformas atravesables (nunca paredes, techos ni límites)
        if not self.stands_on or self.defendiendo:
            return
        pies = self.pos_y + hit_height
        centro = self.hitbox.centerx
        nuevas = {
            p for p in self.plataformas_bajo_pies()
            if p.atravesable and abs(p.surface_y(centro) - pies) <= DROP_TOL
        }
        if not getattr(self.stands_on, "atravesable", False) or not nuevas:
            return
        self.ignoradas |= nuevas
        self.stands_on = False
        self.coyote = 0
        self.pos_y += DROP_EMPUJE
        self.y_speed = DROP_VEL
        self.sincronizar()

    def iniciar_ataque(self):
        # Desde el inicio del juego (zarpazo; con la espada, sablazo). Sin cooldown activo y sin
        # repetir al mantener la tecla (solo KEYDOWN); cada golpe daña una sola vez a cada enemigo
        if (self.atq_frame >= 0 or self.atq_cooldown > 0 or self.defendiendo):
            return False
        self.atq_frame = 0
        self.atq_cooldown = ATAQUE_DURACION + ATAQUE_RECUPERACION
        self.golpeados = set()
        self.animador.forzar("attack" if objetos["espada"] else "attack_no")
        return True

    def dano_ataque(self):
        # Daño a enemigos normales: la espada pega más fuerte que el zarpazo
        return DANO_ESPADA if objetos["espada"] else DANO_ZARPAZO

    def dano_jefe(self):
        return JEFE_DANO_ESPADA if objetos["espada"] else JEFE_DANO_ZARPAZO

    def ataque_activo(self):
        return (self.atq_frame >= 0
                and ATAQUE_ACTIVO[0] <= self.atq_frame <= ATAQUE_ACTIVO[1])

    def rect_ataque(self):
        # Zona de impacto delante de Robin, según hacia dónde mira
        h = self.hitbox
        alcance = ATAQUE_ALCANCE if objetos["espada"] else ATAQUE_ALCANCE_ZARPAZO
        if self.direction >= 0:
            return pygame.Rect(h.right, h.top + 5, alcance, h.height - 10)
        return pygame.Rect(h.left - alcance, h.top + 5,
                           alcance, h.height - 10)

    def recibir_dano(self, cantidad, origen_x, bloqueable=True):
        # Devuelve "inmune", "bloqueado" o "dano"
        global vidas
        if self.invuln > 0:
            return "inmune"
        delante = (origen_x - self.hitbox.centerx) * self.direction > 0
        if bloqueable and self.defendiendo and delante:
            self.empuje = -self.direction * 2     # el escudo amortigua el golpe
            return "bloqueado"
        vidas -= cantidad
        self.invuln = INVULN_FRAMES
        self.atq_frame = -1
        self.empuje = KNOCK_ROBIN if self.hitbox.centerx >= origen_x else -KNOCK_ROBIN
        if self.stands_on:
            self.y_speed = -3
            self.stands_on = False
        return "dano"

    def parpadeo(self):
        # True en los frames en que no se dibuja (invulnerable)
        return self.invuln > 0 and (self.invuln // 5) % 2 == 0

    # ------------------------------------------------------------------
    # ZONA DEL JAMÓN (mientras esté cerrada)
    # ------------------------------------------------------------------
    def en_zona(self):
        # Puntos del "núcleo" de Robin (estrecho, para no dar falsos positivos
        # en rampas inclinadas). Si alguno cae dentro del polígono, está dentro
        hb = self.hitbox
        cx = hb.centerx
        puntos = [
            (cx - 5, hb.top), (cx + 5, hb.top),
            (cx - 5, hb.centery), (cx + 5, hb.centery),
            (cx, hb.bottom - 4),
        ]
        for (px, py) in puntos:
            if punto_en_poligono(px, py, zona_poly):
                return True
        return False

    def comprobar_zona(self, prev_x, prev_y):
        if not zona_bloqueada:
            return
        # Si está apoyado en el techo de la cueva (por fuera) no está dentro
        if getattr(self.stands_on, "solido", False):
            return
        if not self.en_zona():
            return
        self.toco_barrera = True
        # Red de seguridad: se empuja a Robin a la izquierda hasta salir
        for _ in range(ZONA_EMPUJE_MAX):
            self.hitbox.x -= 1
            if not self.en_zona():
                self.sincronizar()
                return
        # Si no basta, vuelve a la posición válida del frame anterior
        self.hitbox.x = prev_x
        self.pos_y = prev_y
        self.y_speed = 0
        self.sincronizar()

    # ------------------------------------------------------------------
    # ANIMACIÓN (solo lee el estado; nunca toca la hitbox)
    # ------------------------------------------------------------------
    def determinar_estado(self):
        # Prioridad: ataque > escudo > salto > caminar > quieto
        if self.atq_frame >= 0:
            return "attack" if objetos["espada"] else "attack_no"
        if self.defendiendo:
            return "shield"
        if not self.stands_on:
            return "jump"
        if self.x_speed != 0 and self.moviendose:
            return "walk"
        return "idle"

    def actualizar_animacion(self):
        self.estado = self.determinar_estado()
        self.animador.set(self.estado)
        self.animador.tick()
        self.image = self.animador.imagen(self.direction)
        # Se re-ancla por los pies: la posición no cambia con el tamaño de imagen
        self.rect = self.image.get_rect(midbottom=self.hitbox.midbottom)

    def actualizar_temporizadores(self):
        if self.atq_frame >= 0:
            self.atq_frame += 1
            if self.atq_frame >= ATAQUE_DURACION:
                self.atq_frame = -1
        if self.atq_cooldown > 0:
            self.atq_cooldown -= 1
        if self.invuln > 0:
            self.invuln -= 1
        self.empuje *= 0.85
        if abs(self.empuje) < 0.5:
            self.empuje = 0.0

    # Método update, actualizamos nuestra imagen y ubicación
    def update(self):
        prev_x = self.hitbox.x
        prev_y = self.pos_y
        self.actualizar_temporizadores()
        self.update_normal()
        self.moviendose = self.hitbox.x != prev_x
        self.comprobar_zona(prev_x, prev_y)
        self.actualizar_animacion()

    def update_normal(self):
        # Plataformas atravesadas: vuelven a ser sólidas cuando los pies ya
        # las han dejado por debajo (así solo se cruza la que se quería cruzar)
        if self.ignoradas:
            pies_ig = self.pos_y + hit_height
            c_ig = self.hitbox.centerx
            self.ignoradas = {
                p for p in self.ignoradas
                if pies_ig <= p.surface_y(c_ig) + DROP_MARGEN
            }

        # ---------- Movimiento horizontal (con la hitbox) ----------
        mov = self.x_speed + round(self.empuje)
        self.hitbox.x += mov

        # Paredes laterales del mapa (borde verde), paredes amarillas del
        # mapa y barrera del jamón (si sigue cerrada)
        for grupo in (limites, muros, barrera_jamon):
            for p in pygame.sprite.spritecollide(
                self, grupo, False, colision_hitbox
            ):
                # Una pared que solo roza la parte alta del cuerpo (su punta inferior)
                # o solo asoma en los pies (un escalón) no bloquea: así Robin pasa
                # bajo rocas colgantes y sube pendientes junto a las paredes
                if grupo is muros and (
                        p.rect.bottom <= self.hitbox.top + MURO_TOL_CABEZA
                        or p.rect.top >= self.hitbox.bottom - MURO_TOL_PIES):
                    continue
                # Solo se resuelve contra paredes que quedan en el sentido
                # en que Robin camina (nunca las que ya deja atrás)
                if mov > 0 and p.rect.centerx > self.hitbox.centerx:
                    self.hitbox.right = min(self.hitbox.right, p.rect.left)
                    if grupo is barrera_jamon:
                        self.toco_barrera = True
                elif mov < 0 and p.rect.centerx < self.hitbox.centerx:
                    self.hitbox.left = max(self.hitbox.left, p.rect.right)
                    if grupo is barrera_jamon:
                        self.toco_barrera = True

        # ---------- Movimiento vertical ----------
        pies_antes = self.pos_y + hit_height
        centro = self.hitbox.centerx

        # Si estaba en el suelo y no sube, sigue la superficie
        # (rampa, escalones pequeños): evita vibrar o caer a saltitos
        if self.stands_on and self.y_speed >= 0:
            # Tiene prioridad la superficie que queda justo bajo el centro de
            # Robin; las que solo entran por el margen de apoyo (PIE_MITAD)
            # se usan si no hay otra. Así baja de una plataforma a una rampa
            # caminando, en vez de quedarse "flotando" en el borde.
            mejor = None
            for p in self.plataformas_bajo_pies():
                y_suelo = p.surface_y(centro)
                dist = abs(y_suelo - pies_antes)
                # Las rampas empinadas permiten un desnivel mayor por paso
                if dist <= p.tolerancia:
                    dentro = 0 if p.x0 <= centro <= p.x1 else 1
                    clave = (dentro, dist)
                    if mejor is None or clave < mejor[0]:
                        mejor = (clave, p, y_suelo)
            if mejor:
                self.y_speed = 0
                self.stands_on = mejor[1]
                self.coyote = COYOTE_FRAMES
                self.pos_y = mejor[2] - hit_height
                self.sincronizar()
                return
            # Se salió del borde de la plataforma: empieza a caer
            self.stands_on = False

        if self.coyote > 0 and not self.stands_on:
            self.coyote -= 1

        pos_antes = self.pos_y      # cabeza de Robin antes de moverse
        self.gravitate()
        self.pos_y += self.y_speed

        # Me estoy moviendo en Y si o no
        if self.y_speed >= 0:
            # Cayendo: aterriza si los pies cruzaron la superficie desde arriba
            pies_ahora = self.pos_y + hit_height
            mejor = None
            for p in self.plataformas_bajo_pies():
                y_suelo = p.surface_y(centro)
                if (pies_antes <= y_suelo + TOLERANCIA_ATERRIZAJE
                        and pies_ahora >= y_suelo):
                    if mejor is None or y_suelo < mejor[1]:
                        mejor = (p, y_suelo)
            if mejor:
                self.y_speed = 0
                self.pos_y = mejor[1] - hit_height
                self.stands_on = mejor[0]
                self.coyote = COYOTE_FRAMES
            self.sincronizar()

        else:
            # Subiendo: las plataformas normales se atraviesan desde abajo;
            # frenan el techo del mapa, los techos "sólidos" (cueva del
            # jamón y bolsillo amarillo) y las paredes amarillas
            self.stands_on = False
            self.sincronizar()
            for p in pygame.sprite.spritecollide(
                self, techos, False, colision_hitbox
            ):
                self.y_speed = 0
                self.pos_y = p.rect.bottom
                self.sincronizar()
            for p in pygame.sprite.spritecollide(
                self, muros, False, colision_hitbox
            ):
                # Solo si es un golpe de cabeza (solape pequeño por arriba)
                if 0 < p.rect.bottom - self.hitbox.top <= 10:
                    self.y_speed = 0
                    self.pos_y = p.rect.bottom
                    self.sincronizar()
            for p in barriers:
                if p.solido and p.x0 <= centro <= p.x1:
                    y_techo = p.surface_y(centro)
                    if pos_antes >= y_techo and self.pos_y < y_techo:
                        self.y_speed = 0
                        self.pos_y = y_techo
                        self.sincronizar()


class Wall(pygame.sprite.Sprite):
    # Plataforma de superficie fina. Si se pasa y_fin es una rampa que va de
    # (x, y) a (x + width, y_fin). El rect es solo para depuración/paredes.
    # solido=True: además de pisarse desde arriba, funciona como TECHO para
    # quien está debajo (se usa en el contorno de la cueva del jamón).
    # atravesable=False: SHIFT no puede cruzarla hacia abajo.
    def __init__(self, x, y, width, height, color=C_GREEN, y_fin=None,
                 solido=False, atravesable=True):
        super().__init__()
        self.x0 = x
        self.x1 = x + width
        self.y0 = y
        self.y1 = y if y_fin is None else y_fin
        self.color = color
        self.solido = solido
        self.atravesable = atravesable
        alto = max(height, abs(self.y1 - self.y0) + GROSOR_DEBUG)
        self.image = pygame.Surface([width, alto])
        self.image.fill(color)
        self.rect = self.image.get_rect(
            topleft=(x, min(self.y0, self.y1))
        )
        # Desnivel máximo que Robin sigue por frame sobre esta superficie:
        # en rampas empinadas crece con la pendiente (px por frame a VEL_ROBIN)
        if self.x1 != self.x0:
            pendiente = abs(self.y1 - self.y0) / (self.x1 - self.x0)
        else:
            pendiente = 0
        self.tolerancia = max(PASO_MAX, pendiente * VEL_ROBIN + 3)

    def surface_y(self, x):
        # Altura de la superficie en la coordenada x
        if self.x1 == self.x0:
            return self.y0
        t = (min(max(x, self.x0), self.x1) - self.x0) / (self.x1 - self.x0)
        return self.y0 + t * (self.y1 - self.y0)


class Recolectable(pygame.sprite.Sprite):
    # Objeto recogible. Cada uno tiene su tipo, posición, tamaño y PNG
    # (si no se indican, se toman los del tipo en TIPOS_ITEM).
    # (x, y) = centro del objeto en coordenadas de la imagen del mapa
    def __init__(self, tipo, x, y, archivo=None, tam=None):
        super().__init__()
        cfg = TIPOS_ITEM[tipo]
        self.tipo = tipo
        self.valor = cfg.get("valor", 1)
        self.image = cargar_ajustada(archivo or cfg["archivo"], tam or cfg["tam"])
        self.rect = self.image.get_rect(center=(round(x * sx), round(y * sy)))


class Bomba(pygame.sprite.Sprite):
    # Trampa estática del juego original (quita una vida y desaparece)
    def __init__(self, x, y, filename=img_bomb, width=60, height=60):
        super().__init__()
        # (x, y) = esquina de la caja width x height; la bomba (recortada y sin deformar)
        # queda centrada y apoyada en el borde inferior de esa caja
        self.image = cargar_ajustada(filename, (width, height))
        self.rect = self.image.get_rect(midbottom=(x + width // 2, y + height))


def pared_entre(a, b):
    # True si hay una pared (amarilla, límite del mapa o barrera mágica) entre dos hitboxes.
    # Se usa para que los enemigos no vean ni golpeen a Robin a través de la roca
    izq = min(a.centerx, b.centerx)
    der = max(a.centerx, b.centerx)
    arriba = max(a.top, b.top)
    abajo = min(a.bottom, b.bottom)
    if abajo <= arriba:                      # sin solape vertical: se usa la banda de en medio
        arriba, abajo = min(a.bottom, b.bottom) - 1, max(a.top, b.top) + 1
        if abajo <= arriba:
            abajo = arriba + 1
    zona = pygame.Rect(izq, arriba, max(1, der - izq), abajo - arriba)
    for grupo in (limites, muros, barrera_jamon):
        for p in grupo:
            if not zona.colliderect(p.rect):
                continue
            # Mismas tolerancias que Robin: una roca colgante o un escalón no cuentan como pared
            if grupo is muros and (p.rect.bottom <= zona.top + MURO_TOL_CABEZA
                                   or p.rect.top >= zona.bottom - MURO_TOL_PIES):
                continue
            return True
    return False


class Enemy(pygame.sprite.Sprite):
    # Enemigo cuerpo a cuerpo. Dos estados: "patrulla" y "ataque".
    # (x, y) = centro de los pies sobre su plataforma; min_x / max_x = límites
    # del centro (dentro de la plataforma, así nunca se cae).
    def __init__(self, x, y, min_x, max_x, anim=None, tam=ENEMIGO_TAM,
                 vida=ENEMIGO_VIDA):
        super().__init__()
        self.animador = Animador(anim or ANIM_ENEMIGO, tam, None, "patrulla")
        self.image = self.animador.imagen(1)
        self.x = float(x)
        self.y_pies = y
        self.min_x = min_x
        self.max_x = max_x
        self.speed = ENEMIGO_VEL
        self.dir = 1
        self.vida = vida
        self.estado = "patrulla"
        self.fase = "acercar"       # acercar / preparar / golpe / recuperar
        self.timer = 0
        self.aturdido = 0
        self.empuje = 0.0
        self.golpeado = False
        self.hit = pygame.Rect(0, 0, *ENEMIGO_HIT)    # cuerpo (para la espada)
        self.rect = self.image.get_rect(midbottom=(round(x), y))
        self.sincronizar()

    def sincronizar(self):
        self.x = max(self.min_x, min(self.x, self.max_x))
        self.hit.midbottom = (round(self.x), self.y_pies)
        self.rect = self.image.get_rect(midbottom=(round(self.x), self.y_pies))

    def rect_ataque(self):
        # Zona de impacto delante del enemigo
        if self.dir >= 0:
            return pygame.Rect(self.hit.right, self.hit.top,
                               ENEMIGO_ALCANCE_GOLPE, self.hit.height)
        return pygame.Rect(self.hit.left - ENEMIGO_ALCANCE_GOLPE, self.hit.top,
                           ENEMIGO_ALCANCE_GOLPE, self.hit.height)

    def recibir_dano(self, cantidad, origen_x):
        self.vida -= cantidad
        if self.vida <= 0:
            self.kill()
            soltar_pocion(self.x, self.y_pies)
            return
        self.aturdido = ENEMIGO_ATURDIDO
        self.empuje = ENEMIGO_EMPUJE if self.x >= origen_x else -ENEMIGO_EMPUJE
        self.estado = "ataque"
        self.fase = "acercar"

    def update(self):
        # Aturdido (golpeado o bloqueado): solo retrocede un poco
        if self.aturdido > 0:
            self.aturdido -= 1
            self.x += self.empuje
            self.empuje *= 0.8
            self.sincronizar()
            self.animador.set("patrulla")
            self.animador.tick()
            self.image = self.animador.imagen(self.dir)
            return

        dx = robin.hitbox.centerx - self.x
        dy = robin.hitbox.bottom - self.y_pies
        # ¿Ve a Robin? Debe estar cerca, a su altura y dentro de su zona
        ve = (abs(dx) <= ENEMIGO_DETECCION
              and abs(dy) <= ENEMIGO_ALTURA_DETECCION
              and self.min_x - 30 <= robin.hitbox.centerx <= self.max_x + 30
              and not pared_entre(self.hit, robin.hitbox))

        anim = "patrulla"
        if self.estado == "patrulla":
            if ve:
                self.estado = "ataque"
                self.fase = "acercar"
            else:
                # Patrulla: da la vuelta al llegar a un extremo
                self.x += self.speed * self.dir
                if self.x <= self.min_x:
                    self.dir = 1
                elif self.x >= self.max_x:
                    self.dir = -1

        if self.estado == "ataque":
            if self.fase == "acercar":
                if not ve:
                    self.estado = "patrulla"
                else:
                    self.dir = 1 if dx > 0 else -1
                    if abs(dx) <= ENEMIGO_ALCANCE:
                        self.fase = "preparar"
                        self.timer = ENEMIGO_PREPARAR
                    else:
                        self.x += ENEMIGO_VEL_ATAQUE * self.dir
            elif self.fase == "preparar":
                anim = "ataque"
                self.timer -= 1
                if self.timer <= 0:
                    self.fase = "golpe"
                    self.timer = ENEMIGO_GOLPE
                    self.golpeado = False
            elif self.fase == "golpe":
                anim = "ataque"
                self.timer -= 1
                if not self.golpeado and \
                        self.rect_ataque().colliderect(robin.hitbox) and \
                        not pared_entre(self.hit, robin.hitbox):
                    self.golpeado = True
                    res = robin.recibir_dano(ENEMIGO_DANO, self.x)
                    if res == "bloqueado":
                        # Robin bloqueó: el enemigo retrocede y queda aturdido
                        self.aturdido = ENEMIGO_ATURDIDO
                        self.empuje = -self.dir * 4
                if self.timer <= 0:
                    self.fase = "recuperar"
                    self.timer = ENEMIGO_RECUPERACION
            elif self.fase == "recuperar":
                self.timer -= 1
                if self.timer <= 0:
                    self.fase = "acercar"

        self.sincronizar()
        self.animador.set(anim)
        self.animador.tick()
        self.image = self.animador.imagen(self.dir)
        self.rect = self.image.get_rect(midbottom=(round(self.x), self.y_pies))


class PocionSuelo(pygame.sprite.Sprite):
    # Poción de vida soltada por un enemigo. Al tocarla se GUARDA (no se bebe sola)
    def __init__(self, x, y_pies):
        super().__init__()
        self.image = cargar_ajustada(
            ASSETS_OBJETOS["pocion"], POCION_TAM, ASSETS_UI["corazon_lleno"]
        )
        self.rect = self.image.get_rect(midbottom=(round(x), round(y_pies) - 2))


class Roca(pygame.sprite.Sprite):
    # Proyectil del jefe: vuela en arco hacia donde estaba Robin al lanzarla
    def __init__(self, x, y, vx, vy, suelo_y):
        super().__init__()
        self.image = cargar_ajustada(JEFE_ROCA_ARCHIVO, JEFE_ROCA_TAM, img_bomb)
        self.fx = float(x)
        self.fy = float(y)
        self.vx = vx
        self.vy = vy
        self.suelo_y = suelo_y
        self.rect = self.image.get_rect(center=(round(x), round(y)))

    def update(self):
        self.vy += JEFE_ROCA_GRAVEDAD
        self.fx += self.vx
        self.fy += self.vy
        self.rect.center = (round(self.fx), round(self.fy))
        # Se rompe contra el suelo o al salir del mapa
        if (self.rect.bottom >= self.suelo_y or self.rect.top > map_height
                or self.rect.right < 0 or self.rect.left > map_width):
            self.kill()
            return
        if self.rect.colliderect(robin.hitbox):
            # Escudo de frente: la bloquea; si no: JEFE_ROCA_DANO corazones
            res = robin.recibir_dano(JEFE_ROCA_DANO, self.fx)
            if res != "inmune":
                self.kill()


class Jefe(pygame.sprite.Sprite):
    # Orco perro final. Fases: espera -> preparar -> (lanza roca) ... -> cooldown
    # (ÚNICO momento en que se le puede dañar) -> espera ... y muerte.
    # (x, y) = centro de los pies en coordenadas de la imagen
    def __init__(self, x, y):
        super().__init__()
        self.animador = Animador(ANIM_JEFE, JEFE_TAM, None, "idle")
        self.image = self.animador.imagen(-1)
        self.x = round(x * sx)
        self.y_pies = snap_y(x, y)
        self.vida_max = JEFE_VIDA
        self.vida = JEFE_VIDA
        self.hit = pygame.Rect(0, 0, *JEFE_HIT)
        self.hit.midbottom = (self.x, self.y_pies)
        self.rect = self.image.get_rect(midbottom=(self.x, self.y_pies))
        self.dir = -1                      # mira hacia donde está Robin (entra por la izquierda)
        self.fase = "espera"
        self.timer = JEFE_ESPERA_INICIAL
        self.rocas_pend = JEFE_ROCAS_POR_ATAQUE
        self.activo = False                # True mientras Robin está dentro de la arena
        self.aviso_dado = False
        self.destello = 0                  # frames de parpadeo al recibir un golpe
        ax0, ay0, ax1, ay1 = JEFE_ARENA
        self.arena = (round(ax0 * sx), round(ay0 * sy), round(ax1 * sx), round(ay1 * sy))

    @property
    def vulnerable(self):
        return self.fase == "cooldown"

    def robin_en_arena(self):
        x0, y0, x1, y1 = self.arena
        c = robin.hitbox.center
        return (not zona_bloqueada) and x0 <= c[0] <= x1 and y0 <= c[1] <= y1

    def lanzar_roca(self):
        ox = self.x + self.dir * JEFE_ROCA_ORIGEN[0]
        oy = self.hit.top + JEFE_ROCA_ORIGEN[1]
        tx = robin.hitbox.centerx + randint(-JEFE_ROCA_DISPERSION, JEFE_ROCA_DISPERSION)
        ty = robin.hitbox.centery
        T = JEFE_ROCA_VUELO
        vx = (tx - ox) / T
        vy = ((ty - oy) - 0.5 * JEFE_ROCA_GRAVEDAD * T * T) / T
        r = Roca(ox, oy, vx, vy, self.y_pies + 2)
        rocas.add(r)
        all_sprites.add(r)

    def recibir_dano(self, cantidad):
        # Devuelve True si el golpe cuenta (solo en cooldown)
        if not self.vulnerable:
            return False
        self.vida -= cantidad
        self.destello = 8
        if self.vida <= 0:
            self.vida = 0
            self.fase = "muerte"
            self.timer = JEFE_MUERTE_FRAMES
            self.animador.forzar("muerte")
            for r in rocas.copy():
                r.kill()
        return True

    def update(self):
        if self.destello > 0:
            self.destello -= 1
        anim = "idle"
        if self.fase == "muerte":
            anim = "muerte"
            self.timer -= 1
            if self.timer <= 0:
                self.kill()
                aparecer_jamon()
                return
        else:
            self.activo = self.robin_en_arena()
            self.dir = 1 if robin.hitbox.centerx > self.x else -1
            if not self.activo:
                # Robin fuera de la arena: el jefe descansa y reinicia su ciclo
                if self.fase != "cooldown":
                    self.fase = "espera"
                    self.timer = JEFE_ESPERA_INICIAL
                    self.rocas_pend = JEFE_ROCAS_POR_ATAQUE
            elif self.fase == "espera":
                self.timer -= 1
                if self.timer <= 0:
                    self.fase = "preparar"
                    self.timer = JEFE_PREPARAR
            elif self.fase == "preparar":
                anim = "lanzar"
                self.timer -= 1
                if self.timer <= 0:
                    self.lanzar_roca()
                    self.rocas_pend -= 1
                    if self.rocas_pend > 0:
                        self.timer = JEFE_ENTRE_ROCAS
                    else:
                        self.fase = "cooldown"          # ¡ahora es vulnerable!
                        self.timer = JEFE_COOLDOWN
                        self.rocas_pend = JEFE_ROCAS_POR_ATAQUE
            elif self.fase == "cooldown":
                anim = "cooldown"
                self.timer -= 1
                if self.timer <= 0:
                    self.fase = "espera"
                    self.timer = JEFE_ESPERA
            if self.fase == "cooldown":
                anim = "cooldown"
        self.animador.set(anim)
        self.animador.tick()
        self.image = self.animador.imagen(self.dir)
        self.rect = self.image.get_rect(midbottom=(self.x, self.y_pies))


class NPC(pygame.sprite.Sprite):
    # Aliado. Todo se configura desde NPC_DEFS (posición, PNG, diálogo, objeto
    # que entrega...). Para añadir otro basta con añadir otra entrada.
    def __init__(self, cfg):
        super().__init__()
        self.id = cfg["id"]
        self.x = round(cfg["x"] * sx)
        self.y = snap_y(cfg["x"], cfg["y"])           # pies del NPC, pegados a su plataforma
        self.radio = cfg.get("radio", 70)             # distancia para hablar
        self.dialogo = TEXTOS[cfg["dialogo"]]
        self.entrega = cfg.get("entrega")             # clave de "objetos" o None
        self.hablado = False
        self.animador = Animador(cfg["anim"], cfg.get("tam", NPC_TAM), None, "idle")
        self.image = self.animador.imagen(1)
        self.rect = self.image.get_rect(midbottom=(self.x, self.y))

    def cerca(self, hero):
        return (abs(hero.hitbox.centerx - self.x) <= self.radio
                and abs(hero.hitbox.bottom - self.y) <= 50)

    def interactuar(self):
        # Primera vez entrega el objeto (queda registrado: no se repite)
        if self.entrega and not objetos[self.entrega]:
            objetos[self.entrega] = True
            aplicar_entrega(self.entrega)
            paginas = self.dialogo["primera"]
        elif self.entrega or self.hablado:
            paginas = self.dialogo["despues"]
        else:
            paginas = self.dialogo["primera"]
        self.hablado = True
        interfaz.iniciar_dialogo(self.dialogo["nombre"], paginas)

    def update(self):
        self.animador.tick()
        # Mira hacia Robin si está cerca
        direccion = 1 if robin.hitbox.centerx >= self.x else -1
        self.image = self.animador.imagen(direccion)
        self.rect = self.image.get_rect(midbottom=(self.x, self.y))


# ---------------------------------------------------------------------------
# INTERFAZ: corazones, contador, avisos y cuadros de diálogo (posición fija)
# ---------------------------------------------------------------------------


class SafeDict(dict):
    def __missing__(self, clave):
        return "{" + clave + "}"


def vars_texto():
    return {
        "atacar": nombre_tecla("atacar"), "defender": nombre_tecla("defender"),
        "interactuar": nombre_tecla("interactuar"), "bajar": nombre_tecla("bajar"),
        "saltar": nombre_tecla("saltar"), "cantidad": REQ_CANTIDAD,
        "curar": nombre_tecla("curar"), "pociones": pociones,
        "reiniciar": nombre_tecla("reiniciar"), "salir": nombre_tecla("salir"),
        "pociones_regalo": POCIONES_REGALO, "cura": POCION_CURA,
        "golpes_zarpazo": -(-ENEMIGO_VIDA // DANO_ZARPAZO),
        "golpes_espada": -(-ENEMIGO_VIDA // DANO_ESPADA),
        "objeto": TIPOS_ITEM[REQ_TIPO]["nombre"],
        "actual": contadores.get(REQ_TIPO, 0),
    }


def formatear(texto):
    return texto.format_map(SafeDict(vars_texto()))


def envolver(texto, fuente, ancho):
    # Divide el texto en líneas que caben en "ancho" píxeles
    lineas, actual = [], ""
    for palabra in texto.split(" "):
        prueba = (actual + " " + palabra).strip()
        if fuente.size(prueba)[0] <= ancho:
            actual = prueba
        else:
            lineas.append(actual)
            actual = palabra
    lineas.append(actual)
    return lineas


def dibujar_panel(superficie, rect, fondo_color=UI_FONDO, oscuro=UI_BORDE_OSCURO,
                  claro=UI_BORDE_CLARO, acento=UI_ACENTO):
    # Cuadro gris claro translúcido con borde pixel art de dos tonos y esquinas
    # (los colores son opcionales: las pantallas finales usan los suyos)
    fondo = pygame.Surface(rect.size, pygame.SRCALPHA)
    fondo.fill(fondo_color)
    superficie.blit(fondo, rect.topleft)
    pygame.draw.rect(superficie, oscuro, rect, 4)
    pygame.draw.rect(superficie, claro, rect.inflate(-8, -8), 2)
    for cx in (rect.left, rect.right - 8):
        for cy in (rect.top, rect.bottom - 8):
            pygame.draw.rect(superficie, acento, (cx, cy, 8, 8))
            pygame.draw.rect(superficie, oscuro, (cx, cy, 8, 8), 1)


class Interfaz:
    def __init__(self):
        self.img_lleno = cargar_ajustada(ASSETS_UI["corazon_lleno"], CORAZON_TAM)
        self.img_vacio = cargar_ajustada(ASSETS_UI["corazon_vacio"], CORAZON_TAM)
        self.iconos = {k: cargar_ajustada(v, ICONO_TAM) for k, v in ASSETS_OBJETOS.items()
                       if k != "pocion"}
        self.icono_item = cargar_ajustada(
            TIPOS_ITEM[REQ_TIPO]["archivo"], (22, 22)
        )
        self.icono_pocion = cargar_ajustada(
            ASSETS_OBJETOS["pocion"], (22, 26), ASSETS_UI["corazon_lleno"]
        )
        self.aviso_texto = ""
        self.aviso_timer = 0
        self.dialogo = None

    def dibujar_barra_jefe(self, win, jefe):
        # Barra de vida del jefe: posición fija arriba en el centro de la pantalla
        w, h = JEFE_BARRA_ANCHO, 22
        caja = pygame.Rect((win_width - w) // 2 + 10, 10, w, h)
        pygame.draw.rect(win, UI_BORDE_OSCURO, caja.inflate(8, 8))
        pygame.draw.rect(win, (60, 20, 30), caja)
        ancho = round(w * max(0, jefe.vida) / jefe.vida_max)
        if ancho > 0:
            pygame.draw.rect(win, (210, 40, 60), pygame.Rect(caja.x, caja.y, ancho, h))
        # Borde dorado mientras es vulnerable (¡es el momento de atacar!)
        borde = (255, 220, 60) if jefe.vulnerable else UI_BORDE_CLARO
        pygame.draw.rect(win, borde, caja.inflate(8, 8), 2)
        t = font_peq.render(JEFE_NOMBRE, True, (255, 255, 255))
        win.blit(t, t.get_rect(center=caja.center))

    def reiniciar(self):
        self.aviso_timer = 0
        self.dialogo = None

    @property
    def dialogo_activo(self):
        return self.dialogo is not None

    def aviso(self, texto, frames=AVISO_FRAMES):
        self.aviso_texto = texto
        self.aviso_timer = frames

    def iniciar_dialogo(self, nombre, paginas):
        self.dialogo = {
            "nombre": nombre, "paginas": [formatear(p) for p in paginas],
            "i": 0, "chars": 0.0,
        }

    def avanzar(self):
        # Tecla de avanzar: primero completa la página; luego pasa a la siguiente
        d = self.dialogo
        if d is None:
            return
        if d["chars"] < len(d["paginas"][d["i"]]):
            d["chars"] = len(d["paginas"][d["i"]])
        else:
            d["i"] += 1
            d["chars"] = 0.0
            if d["i"] >= len(d["paginas"]):
                self.dialogo = None

    def actualizar(self):
        if self.dialogo:
            self.dialogo["chars"] += DIALOGO_VELOCIDAD
        elif self.aviso_timer > 0:
            self.aviso_timer -= 1

    def dibujar_hud(self, win):
        # Corazones: posición fija en pantalla (no dependen de la cámara)
        for i in range(max_vidas):
            img = self.img_lleno if i < vidas else self.img_vacio
            win.blit(img, (10 + i * (CORAZON_TAM[0] + 4), 10 + (CORAZON_TAM[1] - img.get_height()) // 2))
        # Contador de recolectables
        win.blit(self.icono_item, (12, 50))
        txt = font_peq.render(
            str(contadores.get(REQ_TIPO, 0)) + "/" + str(REQ_CANTIDAD),
            True, (255, 255, 255)
        )
        win.blit(txt, (40, 52))
        # Pociones de vida guardadas y la tecla para beberlas
        win.blit(self.icono_pocion, (12, 78))
        txt = font_peq.render(
            "x" + str(pociones) + "   [" + nombre_tecla("curar") + "]",
            True, (255, 255, 255)
        )
        win.blit(txt, (44, 82))
        # Objetos obtenidos y su tecla
        x = win_width - 44
        for clave, tecla in (("escudo", "defender"), ("espada", "atacar")):
            if objetos[clave]:
                win.blit(self.iconos[clave], (x, 10))
                t = font_peq.render(nombre_tecla(tecla), True, (255, 255, 255))
                win.blit(t, t.get_rect(midtop=(x + 14, 40)))
                x -= 44

    def dibujar_prompt(self, win, pos, texto):
        # Burbuja pequeña "E" sobre un NPC cercano
        t = font_peq.render(texto, True, UI_TEXTO)
        caja = t.get_rect(midbottom=pos).inflate(16, 10)
        dibujar_panel(win, caja)
        win.blit(t, t.get_rect(center=caja.center))

    def dibujar(self, win):
        if self.dialogo:
            d = self.dialogo
            caja = pygame.Rect(30, win_height - 150, win_width - 60, 130)
            dibujar_panel(win, caja)
            # Etiqueta con el nombre del que habla
            nombre = font_peq.render(d["nombre"], True, UI_BORDE_CLARO)
            etiqueta = nombre.get_rect(topleft=(caja.left + 18, caja.top - 14)).inflate(20, 10)
            pygame.draw.rect(win, UI_BORDE_OSCURO, etiqueta)
            pygame.draw.rect(win, UI_ACENTO, etiqueta, 2)
            win.blit(nombre, nombre.get_rect(center=etiqueta.center))
            # Texto con efecto máquina de escribir
            texto = d["paginas"][d["i"]]
            lineas = envolver(texto, font_peq, caja.width - 48)
            restante = int(d["chars"])
            y = caja.top + 24
            for linea in lineas:
                parte = linea[:max(0, restante)]
                restante -= len(linea) + 1
                if parte:
                    win.blit(font_peq.render(parte, True, UI_TEXTO), (caja.left + 24, y))
                y += 26
            # Indicador de "continuar"
            if d["chars"] >= len(texto) and (pygame.time.get_ticks() // 400) % 2 == 0:
                tx = font_peq.render(nombre_tecla("avanzar_dialogo"), True, UI_BORDE_OSCURO)
                r = tx.get_rect(bottomright=(caja.right - 44, caja.bottom - 14))
                win.blit(tx, r)
                pygame.draw.polygon(win, UI_BORDE_OSCURO, [
                    (r.right + 6, r.centery - 4), (r.right + 18, r.centery - 4),
                    (r.right + 12, r.centery + 5)])
        elif self.aviso_timer > 0:
            lineas = envolver(self.aviso_texto, font_peq, 520)
            ancho = max(font_peq.size(l)[0] for l in lineas) + 40
            alto = 26 * len(lineas) + 24
            caja = pygame.Rect(0, 0, ancho, alto)
            caja.midbottom = (win_width // 2, win_height - 20)
            dibujar_panel(win, caja)
            for i, l in enumerate(lineas):
                t = font_peq.render(l, True, UI_TEXTO)
                win.blit(t, t.get_rect(midtop=(caja.centerx, caja.top + 12 + i * 26)))


# Inicializar grupos
all_sprites = pygame.sprite.Group()
barriers = pygame.sprite.Group()    # plataformas (se pisan desde arriba)
limites = pygame.sprite.Group()     # paredes laterales del área jugable
techos = pygame.sprite.Group()      # techo del área jugable
muros = pygame.sprite.Group()       # paredes amarillas/naranjas (bloquean de lado y de cabeza)
barrera_jamon = pygame.sprite.Group()   # barrera invisible de la entrada (se vacía al desbloquear)
recolectables = pygame.sprite.Group()      # recompensas (círculos azules)
enemies = pygame.sprite.Group()
bombs = pygame.sprite.Group()
npcs = pygame.sprite.Group()        # aliados
jefes = pygame.sprite.Group()       # jefe final
rocas = pygame.sprite.Group()       # rocas lanzadas por el jefe
pociones_suelo = pygame.sprite.Group()   # pociones soltadas por los enemigos

interfaz = Interfaz()

# ---------------------------------------------------------------------------
# PLATAFORMAS (trazos rojos): (x_inicio, x_fin, y_superficie) en coordenadas de
# la imagen de referencia. Son las partes PLANAS; las diagonales están en
# "rampas". Medidas sobre los píxeles de la imagen (centro de cada trazo).
# ---------------------------------------------------------------------------
plataformas = [
    (902, 969, 148),
    (1337, 1419, 181),
    (935, 1053, 212),
    (1398, 1543, 245),
    (206, 303, 246),
    (502, 679, 254),
    (1129, 1250, 265),
    (341, 406, 272),
    (711, 758, 284),
    (878, 992, 285),
    (1041, 1088, 288),
    (437, 528, 296),
    (1329, 1364, 316),
    (1235, 1273, 317),
    (980, 1090, 333),
    (1125, 1150, 340),
    (558, 658, 372),
    (1277, 1394, 390),
    (1503, 1583, 400),
    (694, 793, 408),
    (1444, 1486, 410),
    (873, 962, 416),
    (971, 1038, 436),
    (209, 298, 443),
    (1041, 1154, 443),
    (301, 350, 446),
    (1342, 1393, 449),
    (1105, 1135, 464),
    (1394, 1462, 469),
    (1216, 1284, 474),
    (345, 383, 479),
    (596, 660, 484),
    (687, 725, 484),
    (408, 431, 494),
    (469, 542, 500),
    (739, 824, 508),
    (545, 596, 510),
    (894, 942, 515),
    (960, 1015, 521),
    (287, 342, 524),
    (1450, 1495, 525),
    (1503, 1564, 532),
    (846, 896, 544),
    (1309, 1413, 545),
    (959, 1078, 546),
    (650, 745, 551),
    (1100, 1148, 573),
    (803, 957, 579),
    (1504, 1598, 600),
    (1228, 1316, 604),
    (1083, 1205, 612),
    (390, 609, 625),
    (231, 329, 648),
    (801, 844, 653),
    (995, 1102, 669),
    (721, 804, 670),
    (596, 683, 692),
    (825, 915, 708),
    (216, 273, 712),
    (271, 432, 730),
    (962, 1006, 736),
    (891, 945, 749),
    (455, 547, 783),
    (1063, 1157, 783),
    (623, 746, 788),
    (936, 985, 789),
    (1013, 1054, 793),
    (600, 667, 816),
    (954, 1011, 822),
    (1160, 1578, 822),
    (850, 925, 827),
]

# Rampas (pasto/escalera inclinados): (x_inicio, y_inicio, x_fin, y_fin)
# Robin las sube y baja caminando. Cada rampa enlaza justo con los bordes de
# las plataformas vecinas (ya recortadas por MARGEN_EXTREMO), sin huecos:
# empieza en (x_fin_plataforma - 3) y acaba en (x_inicio_siguiente + 3).
# La rampa (339, 524) -> (470, 623) es la escalera de piedra diagonal (trazo
# rosa inclinado): se conserva. La escalera VERTICAL ya no existe.
rampas = [
    (300, 246, 344, 272),
    (403, 272, 440, 296),
    (676, 254, 714, 284),
    (1087, 333, 1128, 340),
    (1291, 342, 1318, 350),
    (1318, 350, 1393, 358),
    (1391, 390, 1447, 410),
    (1483, 410, 1506, 400),
    (655, 372, 697, 408),
    (380, 479, 411, 494),
    (593, 510, 653, 551),
    (742, 551, 806, 579),
    (1132, 464, 1203, 472),
    (1410, 545, 1453, 525),
    (1492, 525, 1506, 532),
    (1078, 551, 1103, 573),
    (1202, 612, 1231, 604),
    (544, 783, 566, 799),
    (566, 799, 603, 816),
    (942, 749, 965, 736),
    (339, 524, 470, 623),
]

for (x0, x1, y) in plataformas:
    w = Wall(
        round(x0 * sx) + MARGEN_EXTREMO,
        round(y * sy),
        round((x1 - x0) * sx) - 2 * MARGEN_EXTREMO,
        GROSOR_DEBUG
    )
    barriers.add(w)

for (x0, y0, x1, y1) in rampas:
    w = Wall(
        round(x0 * sx),
        round(y0 * sy),
        round((x1 - x0) * sx),
        GROSOR_DEBUG,
        y_fin=round(y1 * sy)
    )
    barriers.add(w)


def sp(x, y):
    # Convierte un punto de la imagen de referencia a coordenadas del mundo
    return (round(x * sx), round(y * sy))


def snap_y(x_ref, y_ref, tolerancia=30):
    # Altura de pies (en coordenadas del mundo) de la superficie más cercana a
    # (x_ref, y_ref) de la imagen: así los NPC quedan exactamente sobre su plataforma
    x = round(x_ref * sx)
    mejor = None
    for p in barriers:
        if p.x0 <= x <= p.x1:
            ys = p.surface_y(x)
            d = abs(ys - y_ref * sy)
            if d <= tolerancia * sy and (mejor is None or d < mejor[0]):
                mejor = (d, ys)
    return round(mejor[1]) if mejor else round(y_ref * sy)


def contorno_solido(puntos):
    # Contorno amarillo que se pisa por arriba y frena la cabeza por abajo
    # (techo de la cueva del jamón y del bolsillo de la derecha).
    # No se puede atravesar con SHIFT.
    for (ax, ay), (bx, by) in zip(puntos, puntos[1:]):
        ax, ay = sp(ax, ay)
        bx, by = sp(bx, by)
        barriers.add(Wall(ax, ay, bx - ax, GROSOR_DEBUG, y_fin=by,
                          solido=True, atravesable=False))


def muro_polilinea(puntos, grupo, grosor=6, paso=3):
    # Pared fina siguiendo un trazo amarillo: se divide en pequeños rects.
    # Así la colisión sigue la forma dibujada y no un rectángulo grande
    for (ax, ay), (bx, by) in zip(puntos, puntos[1:]):
        ax, ay = sp(ax, ay)
        bx, by = sp(bx, by)
        n = max(1, int(max(abs(bx - ax), abs(by - ay)) // paso))
        for i in range(n + 1):
            px = ax + (bx - ax) * i / n
            py = ay + (by - ay) * i / n
            # El rect arranca en la altura del trazo (no centrado): así una pared
            # que empieza justo al nivel de una plataforma no roza los pies de
            # Robin y no le impide caminar sobre ella
            grupo.add(Wall(
                round(px - grosor / 2), round(py), grosor, grosor
            ))


# ---------------------------------------------------------------------------
# ZONAS AMARILLAS Y NARANJAS (medidas sobre los píxeles de la referencia)
# ---------------------------------------------------------------------------
# 1) Techo de la cueva del jamón: arco amarillo grande. Se pisa por
#    arriba (Robin camina sobre el techo) y es techo sólido por debajo.
#    El lado izquierdo del arco (bajada empinada hasta la flecha de entrada)
#    NO es pisable: es la barrera de entrada (BARRERA_ENTRADA, más abajo).
ARCO_JAMON = [
    (1191, 671), (1261, 650), (1288, 633), (1318, 626),
    (1501, 626), (1536, 670), (1551, 676), (1583, 718), (1608, 734),
]
contorno_solido(ARCO_JAMON)

# Pared derecha de la cueva del jefe: baja desde el final del arco hasta el suelo
PARED_CUEVA_JEFE = [(1608, 734), (1596, 750), (1588, 770), (1581, 790), (1578, 822)]
muro_polilinea(PARED_CUEVA_JEFE, muros)

# 2) Bolsillo amarillo de la derecha (aliada del cofre): el techo es una PARED
#    (bloquea de lado y de cabeza). La plataforma roja de la izquierda acaba
#    justo contra él, así que no se puede subir por encima.
BOLSILLO_TECHO = [
    (1450, 464), (1460, 463), (1489, 442), (1520, 455), (1553, 457),
]
muro_polilinea(BOLSILLO_TECHO, muros)

# 3) Resto de paredes (cada trazo = una polilínea que se convierte en una pared
#    fina que sigue su forma). NO incluye el arco verde junto a la antigua
#    escalera vertical: esa colisión se ha eliminado.
MUROS_AMARILLOS = [
    # Arriba a la izquierda (arco de la entrada) y repisas de los hongos
    [(279, 109), (242, 133), (222, 166), (215, 182), (201, 255)],
    [(506, 255), (506, 294)],
    # Arriba al centro: repisa de la cascada y cristales
    [(894, 108), (895, 155)],
    [(1058, 207), (1056, 216), (1037, 236), (1035, 295)],
    [(1126, 262), (1126, 336)],
    [(1246, 266), (1241, 313)],
    [(1277, 309), (1281, 343), (1287, 353)],
    # Arriba a la derecha
    [(1480, 118), (1515, 140), (1538, 170), (1550, 198), (1551, 251)],
    [(1594, 287), (1606, 304), (1606, 339), (1600, 370), (1585, 405)],
    [(1271, 387), (1276, 447), (1270, 470)],
    [(1409, 399), (1409, 441), (1403, 444), (1401, 453)],
    # Bolsillo del cofre: pared derecha y arco del borde
    [(1553, 457), (1553, 525)],
    [(1581, 492), (1585, 501), (1603, 511), (1613, 538), (1613, 558), (1595, 596)],
    # Izquierda: ruinas (aliado del escudo) y alcobas
    [(297, 303), (246, 316), (224, 338), (210, 365), (199, 402), (196, 434), (204, 450)],
    [(580, 288), (557, 310), (551, 339), (552, 382)],
    [(609, 402), (600, 411), (578, 417), (567, 438), (566, 465), (595, 486)],
    [(286, 496), (245, 536), (224, 577), (221, 621), (227, 665), (209, 686), (209, 720)],
    [(612, 623), (601, 667), (600, 692)],
    [(433, 734), (434, 747), (452, 782)],
    # Centro: roca bajo las plataformas y lago
    [(814, 598), (789, 626), (788, 641), (795, 644), (798, 654)],
    [(809, 666), (807, 693), (821, 716)],
    [(990, 664), (990, 677), (1014, 692), (1017, 703), (1016, 719), (1001, 733)],
    [(958, 541), (957, 548), (963, 551), (963, 582)],
    [(1077, 545), (1074, 549), (1075, 578)],
    [(1314, 545), (1315, 596)],
    [(1086, 612), (1083, 667)],
    # Abajo
    [(1060, 782), (1058, 803)],
    [(942, 789), (930, 832)],
    [(1014, 794), (1015, 824)],
]
for _pts in MUROS_AMARILLOS:
    muro_polilinea(_pts, muros)

# ---------------------------------------------------------------------------
# ZONA DEL JAMÓN (bloqueada al empezar)
# Polígono interior de la cueva: limitado arriba por el arco amarillo, a la
# izquierda por la pared de entrada (flecha amarilla) y abajo/derecha por el
# borde del mapa. Todos los accesos quedan cubiertos:
#  - Por arriba: el arco es una superficie pisable, Robin no puede caer dentro.
#  - Por la izquierda (entrada): barrera invisible con colisión.
#  - Por abajo: la barrera llega por debajo de la zona de muerte.
#  - Por la derecha: el arco acaba contra el borde del mapa.
#  - Red de seguridad: si Robin acabara dentro, se le empuja fuera.
# ---------------------------------------------------------------------------
BARRERA_ENTRADA = [(1191, 671), (1155, 778), (1155, 960)]
zona_poly = [sp(1155, 960), sp(1155, 778)] + [sp(x, y) for (x, y) in ARCO_JAMON] \
    + [sp(1640, 734), sp(1640, 960)]


def crear_barrera_jamon():
    barrera_jamon.empty()
    muro_polilinea(BARRERA_ENTRADA, barrera_jamon)


def desbloquear_zona():
    global zona_bloqueada
    zona_bloqueada = False
    barrera_jamon.empty()      # el desbloqueo dura toda la partida


crear_barrera_jamon()

# Zona de muerte: ya NO hay suelo en el borde inferior. Si Robin cae por
# debajo del límite inferior (más un pequeño margen) pierde una vida.
zona_muerte_y = round(BORDE_INF * sy) + ZONA_MUERTE_MARGEN

# Paredes laterales y techo (justo por fuera del borde verde)
limites.add(Wall(round(BORDE_IZQ * sx) - 40, 0, 40, map_height))
limites.add(Wall(round(BORDE_DER * sx), 0, 40, map_height))
techos.add(Wall(
    round(BORDE_IZQ * sx), round(BORDE_SUP * sy) - 40,
    round((BORDE_DER - BORDE_IZQ) * sx), 40
))

# Posición inicial de Robin: sobre la plataforma superior izquierda
# (equivale al inicio arriba a la izquierda del mapa original).
# (x_start, y_start) es la esquina superior izquierda de la imagen de Robin.
x_start = round(240 * sx - h_width / 2)
y_start = round(246 * sy) - 1 - h_height
robin = Hero(x_start, y_start, h_width, h_height)
all_sprites.add(robin)

# ---------------------------------------------------------------------------
# ENEMIGOS: x, y (pies en la plataforma) y min_x / max_x = límites del CENTRO
# del enemigo; cada rango queda dentro de una plataforma plana, así que nunca
# se cae. La referencia no marca enemigos: están repartidos por la ruta, lejos
# de los aliados y del inicio.
# ---------------------------------------------------------------------------
ENEMIGOS_MAPA = [
    {"x": 500, "y": 625, "min_x": 410, "max_x": 590},     # plataforma larga inferior izquierda
    {"x": 870, "y": 578, "min_x": 820, "max_x": 930},     # orilla del lago
    {"x": 1190, "y": 265, "min_x": 1145, "max_x": 1235},  # cristales (arriba)
    {"x": 1050, "y": 669, "min_x": 1012, "max_x": 1090},  # centro-derecha inferior
    {"x": 1360, "y": 545, "min_x": 1325, "max_x": 1400},  # zona media derecha
    {"x": 350, "y": 730, "min_x": 290, "max_x": 415},     # inferior izquierda
    {"x": 915, "y": 416, "min_x": 892, "max_x": 945},     # ruinas junto a la cascada
    {"x": 1335, "y": 390, "min_x": 1297, "max_x": 1380},  # arriba derecha
    {"x": 745, "y": 408, "min_x": 712, "max_x": 780},     # ruinas bajo la cascada
]


def crear_enemigos_y_bombas():
    for cfg in ENEMIGOS_MAPA:
        en = Enemy(
            round(cfg["x"] * sx), snap_y(cfg["x"], cfg["y"]),
            round(cfg["min_x"] * sx), round(cfg["max_x"] * sx),
            cfg.get("anim"), cfg.get("tam", ENEMIGO_TAM),
            cfg.get("vida", ENEMIGO_VIDA)
        )
        all_sprites.add(en)
        enemies.add(en)

    # Bomba: en el camino superior, sobre la plataforma de los hongos
    bomb = Bomba(round(605 * sx), round(224 * sy), img_bomb, 30, 30)
    bombs.add(bomb)


crear_enemigos_y_bombas()

# ---------------------------------------------------------------------------
# RECOMPENSAS (círculos azules de la referencia, centro = punto verde).
# (x, y) = centro en la imagen. El diseño de cada cristal se elige de
# CRISTAL_DISENOS según CRISTAL_ORDEN (4 colores alternados); "tam" y "archivo"
# son opcionales y sustituyen a los del tipo. Para un tipo nuevo, añádelo a TIPOS_ITEM.
# ---------------------------------------------------------------------------
ITEMS_MAPA = [
    {"tipo": "cristal", "x": 945, "y": 121},
    {"tipo": "cristal", "x": 1392, "y": 150},
    {"tipo": "cristal", "x": 605, "y": 342},
    {"tipo": "cristal", "x": 928, "y": 380},
    {"tipo": "cristal", "x": 1384, "y": 424},
    {"tipo": "cristal", "x": 628, "y": 454},
    {"tipo": "cristal", "x": 324, "y": 492},
    {"tipo": "cristal", "x": 1560, "y": 560},
    {"tipo": "cristal", "x": 826, "y": 632},
    {"tipo": "cristal", "x": 253, "y": 680},
    {"tipo": "cristal", "x": 894, "y": 796},
]


def crear_recolectables():
    recolectables.empty()
    contadores.clear()
    for tipo in TIPOS_ITEM:
        contadores[tipo] = 0
    for i, cfg in enumerate(ITEMS_MAPA):
        archivo = cfg.get("archivo")
        if archivo is None and cfg["tipo"] == "cristal":
            archivo = CRISTAL_DISENOS[CRISTAL_ORDEN[i % len(CRISTAL_ORDEN)] % len(CRISTAL_DISENOS)]
        recolectables.add(Recolectable(
            cfg["tipo"], cfg["x"], cfg["y"], archivo, cfg.get("tam")
        ))


crear_recolectables()

# ---------------------------------------------------------------------------
# ALIADOS (NPC): (x, y) = pies del NPC sobre su plataforma (la y se ajusta
# sola a la superficie). Posiciones tomadas de las figuras marrones de la
# referencia. Para añadir otro basta con añadir una entrada aquí y su texto en
# TEXTOS (sin tocar el bucle).
#   "entrega": clave de "objetos" que concede la primera vez (o None)
#   "anim": {"idle": {...}} igual que las demás animaciones
# ---------------------------------------------------------------------------
NPC_DEFS = [
    # figura con la marca rosa (arriba a la derecha): espada
    {"id": "espada", "dialogo": "npc_espada", "x": 1522, "y": 245, "entrega": "espada",
     "anim": {"idle": {"archivos": [ruta("npcs", "espada_0.png")], "fps": 4}}},
    # figura con la marca amarilla (izquierda, ruinas): escudo
    {"id": "escudo", "dialogo": "npc_escudo", "x": 260, "y": 443, "entrega": "escudo",
     "anim": {"idle": {"archivos": [ruta("npcs", "escudo_0.png")], "fps": 4}}},
    # figuras sin marca: consejos
    {"id": "consejo_a", "dialogo": "npc_consejo_a", "x": 1521, "y": 532, "entrega": None,
     "anim": {"idle": {"archivos": [ruta("npcs", "consejo_a_0.png")], "fps": 4}}},
    {"id": "consejo_b", "dialogo": "npc_consejo_b", "x": 276, "y": 648, "entrega": "kit_pociones",
     "anim": {"idle": {"archivos": [ruta("npcs", "consejo_b_0.png")], "fps": 4}}},
]


def crear_npcs():
    for cfg in NPC_DEFS:
        n = NPC(cfg)
        all_sprites.add(n)
        npcs.add(n)


crear_npcs()

# Jamón: en la zona final, sobre la plataforma del portal (pies en y=822).
# NO existe en el escenario hasta derrotar al jefe (aparecer_jamon).
jamon = Jamon(img_jamon, round(JAMON_POS[0] * sx), snap_y(JAMON_POS[0], JAMON_POS[1]))


def aparecer_jamon():
    global jamon_visible
    jamon_visible = True
    all_sprites.add(jamon)
    interfaz.aviso(formatear(TEXTOS["jamon_aparece"]))


def crear_jefe():
    j = Jefe(*JEFE_POS)
    all_sprites.add(j)
    jefes.add(j)


crear_jefe()


def soltar_pocion(x, y_pies):
    # Los enemigos sueltan una poción con probabilidad DROP_POCION_PROB
    if random() < DROP_POCION_PROB:
        pociones_suelo.add(PocionSuelo(x, y_pies))


def aplicar_entrega(clave):
    # Efecto extra de un objeto entregado por un aliado (la espada y el escudo
    # se leen directamente de "objetos")
    global pociones
    if clave == "kit_pociones":
        pociones = min(POCIONES_MAX, pociones + POCIONES_REGALO)


def usar_pocion():
    # Beber una poción: solo cuando el jugador lo decide
    global vidas, pociones
    if pociones <= 0:
        interfaz.aviso(formatear(TEXTOS["sin_pociones"]), 90)
    elif vidas >= max_vidas:
        interfaz.aviso(formatear(TEXTOS["vida_completa"]), 90)
    else:
        pociones -= 1
        vidas = min(max_vidas, vidas + POCION_CURA)
        interfaz.aviso(formatear(TEXTOS["pocion_curar"]), 90)


def intentar_interactuar():
    # Habla con el primer aliado a su alcance (si no hay ninguno, no pasa nada)
    for n in npcs:
        if n.cerca(robin):
            n.interactuar()
            return


def mostrar_intro():
    # Diálogo de inicio con la historia y los controles (al empezar y al reiniciar)
    interfaz.iniciar_dialogo(TEXTOS["intro"]["nombre"], TEXTOS["intro"]["primera"])


def reiniciar_partida():
    # Reinicio completo: Robin, vidas, enemigos, bomba, recompensas, objetos,
    # NPC y zona del jamón
    global robin, vidas, ultimo_golpe, finished, zona_bloqueada
    global pociones, jamon_visible, fin_tipo, fin_t
    robin.kill()
    for s in (list(enemies) + list(bombs) + list(npcs) + list(jefes)
              + list(rocas) + list(pociones_suelo)):
        s.kill()
    jamon.kill()
    jamon_visible = False
    pociones = 0
    robin = Hero(x_start, y_start, h_width, h_height)
    all_sprites.add(robin)
    crear_enemigos_y_bombas()
    crear_npcs()
    crear_jefe()
    crear_recolectables()
    for k in objetos:
        objetos[k] = False
    zona_bloqueada = True
    crear_barrera_jamon()
    interfaz.reiniciar()
    mostrar_intro()
    vidas = max_vidas
    ultimo_golpe = 0
    finished = False
    fin_tipo = None
    fin_t = 0


# ---------------------------------------------------------------------------
# PANTALLAS FINALES (victoria y derrota). Se dibujan cada fotograma sobre una
# captura tintada y oscurecida del último fotograma de la partida
# ---------------------------------------------------------------------------
FIN_ESTILO = {
    "victoria": {"tinte": (150, 120, 215), "panel": (28, 18, 58, 235), "oscuro": (60, 32, 110),
                 "borde": (255, 214, 79), "claro": (255, 240, 190), "titulo": (255, 214, 79),
                 "sombra": (92, 40, 140), "suelo": (58, 36, 104), "suelo_luz": (120, 84, 190),
                 "texto": (246, 236, 255)},
    "derrota": {"tinte": (115, 38, 52), "panel": (30, 10, 16, 238), "oscuro": (70, 14, 24),
                "borde": (205, 55, 65), "claro": (235, 150, 150), "titulo": (240, 70, 80),
                "sombra": (60, 8, 16), "suelo": (48, 16, 24), "suelo_luz": (110, 40, 52),
                "texto": (245, 215, 215)},
}
fondo_final = None          # captura del último fotograma (se crea en terminar_partida)
particulas_final = []       # cristales que flotan (victoria) o cenizas que caen (derrota)
brillo_final = None         # halo luminoso de la pantalla de victoria
cache_texto = {}


def texto_pixel(texto, tam, color, borde, escala=2):
    # Texto grande con aspecto pixel art: se dibuja pequeño con contorno y se amplía sin suavizar
    clave = (texto, tam, color, borde, escala)
    if clave not in cache_texto:
        f = pygame.font.Font(None, tam)
        base = f.render(texto, False, color)
        sombra = f.render(texto, False, borde)
        w, h = base.get_size()
        s = pygame.Surface((w + 2, h + 2), pygame.SRCALPHA)
        for dx in (0, 1, 2):
            for dy in (0, 1, 2):
                s.blit(sombra, (dx, dy))
        s.blit(base, (1, 1))
        cache_texto[clave] = pygame.transform.scale(s, ((w + 2) * escala, (h + 2) * escala))
    return cache_texto[clave]


def ampliar(img, k):
    # Amplía un sprite k veces entero (pixel art sin deformar ni suavizar)
    return pygame.transform.scale(img, (img.get_width() * k, img.get_height() * k))


def crear_particulas(tipo):
    lista = []
    if tipo == "victoria":
        # Los 4 diseños de cristal flotando hacia arriba
        imgs = [cargar_ajustada(d, (22, 22)) for d in CRISTAL_DISENOS]
        for i in range(28):
            lista.append({"img": imgs[i % len(imgs)], "x": randint(0, win_width),
                          "y": randint(0, win_height), "vy": -0.3 - random() * 0.9,
                          "fase": random() * 6.28, "amp": 5 + random() * 12})
    else:
        # Ascuas y ceniza cayendo despacio
        colores = [(170, 40, 50), (110, 30, 40), (200, 90, 80), (90, 80, 95)]
        for i in range(40):
            lista.append({"tam": randint(2, 4), "col": colores[i % len(colores)],
                          "x": randint(0, win_width), "y": randint(0, win_height),
                          "vy": 0.3 + random() * 0.9, "fase": random() * 6.28,
                          "amp": 4 + random() * 10})
    return lista


def terminar_partida(tipo):
    # Pasa a la pantalla final ("victoria" o "derrota") conservando el último fotograma de fondo
    global finished, fin_tipo, fin_t, fondo_final, particulas_final, brillo_final
    finished = True
    fin_tipo = tipo
    fin_t = 0
    est = FIN_ESTILO[tipo]
    # Fondo = el mundo del último fotograma (sin corazones ni cuadros de texto encima)
    fondo_final = pygame.Surface((win_width, win_height))
    fondo_final.blit(scaled_world, (0, 0))
    fondo_final.fill(est["tinte"], special_flags=pygame.BLEND_RGB_MULT)
    # Viñeta: bordes de la pantalla más oscuros
    vineta = pygame.Surface((win_width, win_height), pygame.SRCALPHA)
    for i in range(0, 140, 7):
        pygame.draw.rect(vineta, (0, 0, 0, int(max(0, 190 - i * 1.4))),
                         pygame.Rect(i, i, win_width - 2 * i, win_height - 2 * i), 7)
    fondo_final.blit(vineta, (0, 0))
    particulas_final = crear_particulas(tipo)
    # Halo dorado detrás del jamón
    brillo_final = pygame.Surface((220, 220), pygame.SRCALPHA)
    for r in range(110, 0, -10):
        pygame.draw.circle(brillo_final, (255, 214, 79, int(70 * (1 - r / 110) + 8)), (110, 110), r)


def dibujar_pantalla_final():
    global fin_t
    fin_t += 1
    est = FIN_ESTILO[fin_tipo]
    cfg = TEXTOS["fin_" + fin_tipo]
    victoria = fin_tipo == "victoria"
    window.blit(fondo_final, (0, 0))

    # Partículas animadas del fondo
    for p in particulas_final:
        p["y"] += p["vy"]
        if p["y"] < -24:
            p["y"] = win_height + 24
        elif p["y"] > win_height + 24:
            p["y"] = -24
        x = p["x"] + sin(fin_t * 0.03 + p["fase"]) * p["amp"]
        if "img" in p:
            window.blit(p["img"], (round(x), round(p["y"])))
        else:
            pygame.draw.rect(window, p["col"], (round(x), round(p["y"]), p["tam"], p["tam"]))

    # Panel central
    caja = pygame.Rect(70, 50, win_width - 140, win_height - 100)
    dibujar_panel(window, caja, est["panel"], est["oscuro"], est["claro"], est["borde"])

    # Título (la victoria late suave; la derrota tiembla un instante al empezar)
    dx = dy = 0
    if victoria:
        dy = round(sin(fin_t * 0.07) * 4)
    elif fin_t < 30:
        dx, dy = randint(-3, 3), randint(-2, 2)
    titulo = texto_pixel(cfg["titulo"], 64, est["titulo"], est["sombra"], 2)
    window.blit(titulo, titulo.get_rect(midtop=(win_width // 2 + dx, caja.top + 22 + dy)))
    # Línea decorativa bajo el título
    pygame.draw.rect(window, est["borde"], (caja.left + 90, caja.top + 128, caja.width - 180, 4))
    pygame.draw.rect(window, est["oscuro"], (caja.left + 90, caja.top + 132, caja.width - 180, 2))

    # Mensaje
    y = caja.top + 148
    for linea in cfg["lineas"]:
        for sub in envolver(linea, font_peq, caja.width - 100):
            t = font_peq.render(sub, True, est["texto"])
            window.blit(t, t.get_rect(midtop=(win_width // 2, y)))
            y += 26
        y += 4

    # Escena central sobre una repisa de piedra (se coloca justo bajo el mensaje, sea cual sea su largo)
    suelo_y = min(y + 16 + 112, caja.bottom - 130)
    pygame.draw.rect(window, est["suelo"], (caja.left + 110, suelo_y, caja.width - 220, 14))
    pygame.draw.rect(window, est["suelo_luz"], (caja.left + 110, suelo_y, caja.width - 220, 4))
    cat = robin.animador.anims["idle"].der[0]
    if victoria:
        ham = ampliar(jamon.image, 2)
        salto_ham = round(sin(fin_t * 0.09) * 4)
        centro_ham = (win_width // 2 + 100, suelo_y - 4 + salto_ham)
        window.blit(brillo_final, brillo_final.get_rect(center=(centro_ham[0], centro_ham[1] - ham.get_height() // 2)))
        window.blit(ampliar(cat, 2), ampliar(cat, 2).get_rect(midbottom=(win_width // 2 - 110, suelo_y)))
        window.blit(ham, ham.get_rect(midbottom=centro_ham))
    else:
        # Robin apagado (tintado) junto a un corazón roto
        gato = ampliar(cat, 2)
        gato.fill((105, 95, 120), special_flags=pygame.BLEND_RGB_MULT)
        window.blit(gato, gato.get_rect(midbottom=(win_width // 2 - 110, suelo_y)))
        corazon = ampliar(interfaz.img_vacio, 3)
        rc = corazon.get_rect(midbottom=(win_width // 2 + 100, suelo_y - 6))
        window.blit(corazon, rc)
        # grieta del corazón
        gx, gy = rc.centerx, rc.top + 4
        pygame.draw.lines(window, est["borde"], False,
                          [(gx, gy), (gx - 7, gy + 17), (gx + 5, gy + 31), (gx - 5, gy + 47), (gx + 2, gy + 60)], 3)

    # Resumen de la partida
    datos = [(interfaz.icono_item, str(contadores.get(REQ_TIPO, 0)) + "/" + str(len(ITEMS_MAPA))),
             (interfaz.icono_pocion, "x" + str(pociones)),
             (interfaz.img_lleno, str(max(0, vidas)) + "/" + str(max_vidas))]
    piezas = []
    for icono, txt in datos:
        render = font_peq.render(txt, True, est["texto"])
        piezas.append((icono, render, icono.get_width() + 8 + render.get_width()))
    total = sum(p[2] for p in piezas) + 40 * (len(piezas) - 1)
    x = win_width // 2 - total // 2
    for icono, render, ancho in piezas:
        window.blit(icono, (x, suelo_y + 28 + (30 - icono.get_height()) // 2))
        window.blit(render, (x + icono.get_width() + 8, suelo_y + 34))
        x += ancho + 40

    # Indicación de teclas (parpadea suavemente)
    pie_color = est["claro"] if (fin_t // 30) % 2 == 0 else est["texto"]
    pie = font_peq.render(formatear(TEXTOS["fin_pie"]), True, pie_color)
    window.blit(pie, pie.get_rect(midbottom=(win_width // 2, caja.bottom - 14)))


# Juego principal
mostrar_intro()
run = True
finished = False
clock = pygame.time.Clock()

while run:
    clock.tick(FPS)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False

        elif event.type == pygame.KEYDOWN:
            k = event.key
            if es_tecla(k, "reiniciar") and finished:
                reiniciar_partida()

            elif es_tecla(k, "salir") and finished:
                run = False

            elif es_tecla(k, "depurar"):
                debug = not debug

            elif finished:
                pass

            elif interfaz.dialogo_activo:
                # Con un diálogo abierto solo se puede avanzar el texto
                if es_tecla(k, "avanzar_dialogo"):
                    interfaz.avanzar()

            elif es_tecla(k, "saltar"):
                robin.jump(salto)

            elif es_tecla(k, "bajar"):
                # Un pulso = una bajada (el KEYDOWN no se repite al mantener)
                robin.bajar_plataforma()

            elif es_tecla(k, "interactuar"):
                intentar_interactuar()

            elif es_tecla(k, "curar"):
                usar_pocion()

            elif es_tecla(k, "atacar"):
                robin.iniciar_ataque()

        elif event.type == pygame.KEYUP:
            # Salto variable: soltar ESPACIO acorta el salto
            if es_tecla(event.key, "saltar"):
                robin.cut_jump()

    if not finished:
        if interfaz.dialogo_activo:
            # Mundo en pausa mientras se habla
            robin.x_speed = 0
            interfaz.actualizar()
        else:
            robin.leer_entrada(pygame.key.get_pressed())
            all_sprites.update()
            interfaz.actualizar()

            # Espada: daña a los enemigos en la zona de impacto (una vez por golpe)
            if robin.ataque_activo():
                zona = robin.rect_ataque()
                for en in enemies.copy():
                    if en not in robin.golpeados and zona.colliderect(en.hit):
                        robin.golpeados.add(en)
                        en.recibir_dano(robin.dano_ataque(), robin.hitbox.centerx)
                # El jefe solo recibe daño mientras está en recuperación
                for j in jefes.copy():
                    if j not in robin.golpeados and zona.colliderect(j.hit):
                        robin.golpeados.add(j)
                        if not j.recibir_dano(robin.dano_jefe()) and not j.aviso_dado:
                            j.aviso_dado = True
                            interfaz.aviso(formatear(TEXTOS["jefe_guardia"]))

            # Comprobar colisión con las bombas
            if pygame.sprite.spritecollide(robin, bombs, True, colision_hitbox):
                vidas -= 1
                robin.invuln = INVULN_FRAMES

            # Recolectables: se cuentan por tipo y, al llegar a la cantidad
            # requerida, se abre la zona del jamón (resto de la partida)
            for c in pygame.sprite.spritecollide(
                robin, recolectables, True, colision_hitbox
            ):
                contadores[c.tipo] = contadores.get(c.tipo, 0) + c.valor
            # Pociones del suelo: se guardan (no se beben solas)
            for p in pygame.sprite.spritecollide(
                robin, pociones_suelo, True, colision_hitbox
            ):
                if pociones < POCIONES_MAX:
                    pociones += 1
                    interfaz.aviso(formatear(TEXTOS["pocion_recogida"]), 120)
                else:
                    pociones_suelo.add(p)      # inventario lleno: se queda en el suelo
            if zona_bloqueada and contadores.get(REQ_TIPO, 0) >= REQ_CANTIDAD:
                desbloquear_zona()
                interfaz.aviso(TEXTOS["zona_desbloqueada"])

            # Robin chocó con la barrera de la zona cerrada: aviso en pantalla
            if robin.toco_barrera:
                robin.toco_barrera = False
                if zona_bloqueada:
                    interfaz.aviso(formatear(TEXTOS["zona_bloqueada"]))

            # Zona de muerte: Robin cayó por debajo del mapa jugable
            if robin.hitbox.top > zona_muerte_y:
                vidas -= 1
                robin.respawn(x_start, y_start)   # vuelve al punto inicial

        # Cámara de seguimiento: centra a Robin (horizontal y vertical) y
        # se limita al tamaño REAL de la imagen, así nunca se ve negro.
        # Los sprites ya no se mueven: solo se resta la posición de la cámara.
        cam_x = robin.hitbox.centerx - view_w // 2
        cam_y = robin.hitbox.centery - view_h // 2
        cam_x = max(0, min(cam_x, map_width - view_w))
        cam_y = max(0, min(cam_y, map_height - view_h))

        # Dibujar el mundo en una superficie independiente
        world_surface.blit(back, (-cam_x, -cam_y))
        for c in recolectables:
            world_surface.blit(c.image, (c.rect.x - cam_x, c.rect.y - cam_y))
        for p in pociones_suelo:
            world_surface.blit(p.image, (p.rect.x - cam_x, p.rect.y - cam_y))
        for s in all_sprites:
            if s is robin and robin.parpadeo():
                continue
            if isinstance(s, Jefe) and s.destello > 0 and s.destello % 2 == 0:
                continue
            world_surface.blit(s.image, (s.rect.x - cam_x, s.rect.y - cam_y))
        for b in bombs:
            world_surface.blit(b.image, (b.rect.x - cam_x, b.rect.y - cam_y))

        # Depuración (F1): plataformas, paredes, hitbox
        if debug:
            for p in barriers:
                pygame.draw.line(
                    world_surface, (255, 255, 0) if p.solido else C_RED,
                    (p.x0 - cam_x, p.y0 - cam_y),
                    (p.x1 - cam_x, p.y1 - cam_y), 2
                )
            for p in list(limites) + list(techos) + list(muros):
                pygame.draw.rect(
                    world_surface, C_GREEN,
                    p.rect.move(-cam_x, -cam_y), 1
                )
            for p in barrera_jamon:
                pygame.draw.rect(
                    world_surface, (255, 128, 0),
                    p.rect.move(-cam_x, -cam_y), 1
                )
            if zona_bloqueada:
                pygame.draw.lines(
                    world_surface, (255, 128, 0), True,
                    [(x - cam_x, y - cam_y) for (x, y) in zona_poly], 1
                )
            for n in npcs:
                pygame.draw.circle(
                    world_surface, (255, 105, 220),
                    (n.x - cam_x, n.y - cam_y), n.radio, 1
                )
            for en in enemies:
                pygame.draw.rect(
                    world_surface, (255, 0, 255), en.hit.move(-cam_x, -cam_y), 1
                )
                pygame.draw.line(
                    world_surface, (255, 0, 255),
                    (en.min_x - cam_x, en.y_pies - cam_y),
                    (en.max_x - cam_x, en.y_pies - cam_y), 1
                )
                if en.estado == "ataque" and en.fase == "golpe":
                    pygame.draw.rect(
                        world_surface, C_RED,
                        en.rect_ataque().move(-cam_x, -cam_y), 1
                    )
            for j in jefes:
                pygame.draw.rect(
                    world_surface, (255, 220, 60) if j.vulnerable else (255, 0, 255),
                    j.hit.move(-cam_x, -cam_y), 1
                )
                x0, y0, x1, y1 = j.arena
                pygame.draw.rect(
                    world_surface, (255, 128, 0),
                    pygame.Rect(x0 - cam_x, y0 - cam_y, x1 - x0, y1 - y0), 1
                )
            for r in rocas:
                pygame.draw.rect(world_surface, C_RED, r.rect.move(-cam_x, -cam_y), 1)
            if robin.ataque_activo():
                pygame.draw.rect(
                    world_surface, (0, 255, 255),
                    robin.rect_ataque().move(-cam_x, -cam_y), 1
                )
            pygame.draw.line(
                world_surface, (255, 128, 0),
                (0, zona_muerte_y - cam_y),
                (map_width, zona_muerte_y - cam_y), 1
            )
            pygame.draw.rect(
                world_surface, (255, 255, 0),
                robin.hitbox.move(-cam_x, -cam_y), 1
            )

        # Aplicar zoom (la superficie ya cubre exactamente la ventana)
        scaled_world = pygame.transform.scale(
            world_surface,
            (int(view_w * zoom), int(view_h * zoom))
        )

        window.blit(scaled_world, (0, 0))

        # Burbuja "E" sobre el aliado cercano (en pantalla, no en el mundo)
        if not interfaz.dialogo_activo:
            for n in npcs:
                if n.cerca(robin):
                    interfaz.dibujar_prompt(
                        window,
                        (round((n.rect.centerx - cam_x) * zoom),
                         round((n.rect.top - cam_y) * zoom) - 4),
                        nombre_tecla("interactuar")
                    )
                    break

        # Interfaz fija: corazones, contador, objetos y mensajes
        interfaz.dibujar_hud(window)
        for j in jefes:
            if j.activo or j.fase == "muerte":
                interfaz.dibujar_barra_jefe(window, j)
        interfaz.dibujar(window)

        # Comprobar victoria
        if jamon_visible and colision_hitbox(robin, jamon):
            terminar_partida("victoria")

        # Comprobar derrota (tiene prioridad si coincide con la victoria en el mismo fotograma)
        if vidas <= 0:
            terminar_partida("derrota")
    else:
        # Partida terminada: pantalla final animada (R reinicia, ESC sale)
        dibujar_pantalla_final()

    pygame.display.update()

pygame.quit()