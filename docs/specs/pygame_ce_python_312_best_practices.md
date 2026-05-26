# Guide de Référence — Best Practices Python 3.12 & Pygame-CE [Reference]

> **Type de document :** Référence de développement / State of the Art
> **Technologies cibles :** Python 3.12+, Pygame-CE (Community Edition) 2.4.0+
> **Objectif :** Établir les standards de codage, d'architecture et d'optimisation pour concevoir des moteurs de jeu 2D professionnels et ultra-performants.

---

## 1. Pourquoi Pygame-CE (Community Edition) ?

**Pygame-CE** est le fork officiel et activement maintenu par la communauté des développeurs d'origine. Contrairement à la version héritée (`pygame` upstream), Pygame-CE apporte :
* **Performances SIMD et AVX2** : Rendu de surfaces et manipulations arithmétiques largement accélérées.
* **Modernisation des API** : Introduction de structures modernes comme `FRect`, `fblits`, et `pygame.system`.
* **Compatibilité continue** : Support optimal des dernières versions de Python (3.11, 3.12, et versions futures).

*Règle d'installation : Ne jamais installer les deux dans le même environnement virtuel (virtualenv).*
```bash
pip uninstall pygame
pip install pygame-ce
```

---

## 2. Rendu Graphique & Optimisations Pygame-CE

Le rendu en Python est souvent limité par l'overhead du CPU (le "passage de frontière" entre Python et le code C de SDL). Pour maintenir un framerate stable à 60 FPS ou plus, vous devez appliquer ces techniques de pointe.

### 2.1 L'utilisation massive de `Surface.fblits`
La méthode classique `Surface.blit` appelée dans une boucle `for` en Python crée un goulot d'étranglement CPU à cause de l'interprétation de la boucle à chaque frame.
* **La solution** : Regrouper vos rendus (par exemple, le rendu de la grille de tuiles d'une carte ou d'un système de particules) et appeler `fblits` en une seule opération.

```python
# ❌ ANTI-PATTERN : Lent, boucle de blits en Python
for texture, position in render_queue:
    screen.blit(texture, position)

#   BEST PRACTICE : Traitement groupé ultra-rapide (C-loop interne)
# render_queue est une liste de tuples (Surface, coordonnees_ou_rect)
screen.fblits(render_queue)
```
> **Impact de performance constaté** : Réduction du temps de rendu d'une carte complète de 8ms à 2ms (soit un gain de 300% sur le frame budget).

### 2.2 `FRect` (Floating-point Rectangle)
Le `Rect` historique de Pygame tronquait toutes les coordonnées en entiers (`int`), provoquant des micro-saccades ("jittering") lors de mouvements à faible vitesse ou de déplacements de caméra fluides.
* **La solution** : Utiliser `pygame.FRect` pour toutes les entités physiques et la caméra. Il gère les décimaux (`float`) pour les calculs physiques et arrondit proprement uniquement au moment du rendu de l'image.

```python
import pygame

# Créer un rectangle flottant
entity_frect = pygame.FRect(10.5, 20.75, 32.0, 64.0)

# Mouvement fluide avec delta time
entity_frect.x += velocity_x * dt

# Récupérer un FRect depuis une Surface
sprite_frect = surface.get_frect(topleft=(x, y))
```

### 2.3 Conversion systématique des formats de pixel
Ne jamais oublier de convertir les images immédiatement après leur chargement. Sans cela, Pygame doit convertir le format de pixel à chaque frame lors du `blit`, ce qui détruit les performances.
* `.convert()` : Pour les images opaques (sans transparence).
* `.convert_alpha()` : Pour les images contenant de la transparence (per-pixel alpha).

```python
#   Best Practice : Chargeur sécurisé et optimisé
def load_texture(path: str, use_alpha: bool = True) -> pygame.Surface:
    raw_surf = pygame.image.load(path)
    return raw_surf.convert_alpha() if use_alpha else raw_surf.convert()
```

### 2.4 Caching du Rendu de Textes (Font Rendering)
Le rendu de texte avec `font.render()` est l'une des opérations les plus lentes dans Pygame car elle génère une nouvelle surface pixel par pixel à la volée.
* **Règle** : Ne jamais appeler `font.render` dans votre boucle de dessin principale (`draw()`) pour des textes statiques ou semi-statiques. Générez-les une fois, stockez-les dans un cache (dictionnaire) et dessinez la surface pré-rendue.

```python
class TextCache:
    def __init__(self, font: pygame.font.Font):
        self.font = font
        self._cache: dict[str, pygame.Surface] = {}

    def get_text_surface(self, text: str, color: pygame.Color) -> pygame.Surface:
        key = f"{text}_{color.r}_{color.g}_{color.b}"
        if key not in self._cache:
            self._cache[key] = self.font.render(text, True, color).convert_alpha()
        return self._cache[key]
```

### 2.5 Frustum Culling (Rendu sélectif)
Inutile d'envoyer des centaines de tuiles ou d'entités à la carte graphique si elles se situent hors de l'écran.
* **Best Practice** : Calculez l'intersection entre le rectangle de la caméra (`camera_frect`) et le rectangle de l'entité/tuile avant de l'ajouter à la file d'attente de rendu.

```python
# Rendu uniquement si visible à l'écran
if camera_frect.colliderect(entity.frect):
    render_queue.append((entity.image, entity.frect.topleft - camera_offset))
```

---

## 3. Améliorations Mathématiques & API système de Pygame-CE

### 3.1 Manipulation de Vecteurs avec `Vector2`
Pygame-CE a optimisé les classes `pygame.math.Vector2` et `Vector3` en C, rendant leur instanciation et leurs calculs très performants.
* **`Vector2.move_towards(target, distance)`** : Calcule le déplacement vers une cible sans jamais la dépasser (évite les oscillations et le codage manuel de la trigonométrie).

```python
pos = pygame.Vector2(10, 10)
target = pygame.Vector2(100, 100)
speed = 4.5 * dt

# Déplacement direct et sécurisé sans dépassement (overshoot)
pos.move_towards_ip(target, speed)
```

### 3.2 Accès aux chemins système avec `pygame.system`
Gérer les chemins de sauvegarde manuellement selon l'OS (Windows, macOS, Linux) est source d'erreurs et de violations de permissions. Pygame-CE intègre un module système robuste.

```python
import pygame.system

# Récupérer un dossier d'écriture garanti et sécurisé pour les sauvegardes
# Windows : C:\Users\Nom\AppData\Roaming\MyCompany\MyGame
# macOS   : /Users/Nom/Library/Application Support/MyCompany/MyGame
save_dir = pygame.system.get_pref_path(org="MyCompany", app="MyGame")

# Obtenir les préférences linguistiques de l'OS de l'utilisateur
user_locales = pygame.system.get_pref_locales()
# Retourne par exemple: [{'language': 'fr', 'country': 'FR'}]
```

---

## 4. Intégration des Fonctionnalités Modernes de Python 3.12

Python 3.12 introduit des fonctionnalités majeures qui simplifient le code de jeu et améliorent drastiquement le typage statique (validé par `pyright`).

### 4.1 Syntaxe simplifiée des Génériques (PEP 695)
Plus besoin d'importer `TypeVar` ou `Generic` pour définir des classes ou des fonctions génériques. La syntaxe est désormais intégrée directement à la signature.

```python
#   BEST PRACTICE : Gestionnaire d'entités générique en Python 3.12
class EntityManager[T]:
    def __init__(self):
        self._entities: list[T] = []

    def register(self, entity: T) -> None:
        self._entities.append(entity)

    def get_all(self) -> list[T]:
        return self._entities
```

### 4.2 Déclaration de Type Alias explicite (`type`)
Rend les signatures de fonctions beaucoup plus lisibles en évitant les surcharges de types complexes.

```python
import pygame

# Déclarer des alias de type clairs et réutilisables
type Coordinate = tuple[float, float] | pygame.Vector2
type RenderItem = tuple[pygame.Surface, pygame.FRect | Coordinate]

def queue_render(item: RenderItem) -> None:
    ...
```

### 4.3 Décorateur de surcharge explicite (`@override`)
Pour sécuriser le polymorphisme (très fréquent dans les architectures d'entités ou de UI de jeux vidéo). Le décorateur `@override` de la bibliothèque `typing` permet aux outils comme `pyright` de lever immédiatement une erreur si la méthode de la classe mère change de signature ou de nom.

```python
from typing import override
import pygame

class BaseEntity(pygame.sprite.Sprite):
    def update(self, dt: float) -> None:
        pass

class Player(BaseEntity):
    @override
    def update(self, dt: float) -> None:
        # Si la méthode parente "update" était renommée, Pyright lèverait une erreur ici.
        self.move_player(dt)
```

### 4.4 Typage précis des configurations avec `Unpack` et `TypedDict`
Idéal pour passer des configurations ou des paramètres de création d'entités complexes sans perdre le typage automatique de l'autocomplétion.

```python
from typing import TypedDict, Unpack

class EntityConfig(TypedDict):
    speed: float
    health: int
    name: str
    can_teleport: bool

#   Usage : kwargs est maintenant entièrement typé et validé statiquement !
def spawn_entity(x: float, y: float, **kwargs: Unpack[EntityConfig]) -> None:
    speed = kwargs.get("speed", 100.0)
    name = kwargs.get("name", "NPC")
```

### 4.5 F-Strings surpuissants
Les f-strings en Python 3.12 n'ont plus de limitations sur les guillemets et autorisent le nesting, les retours à la ligne et les commentaires directement dans les expressions.
* **Le specifier `=`** : Indispensable pour les logs de debugging rapide.

```python
pos = pygame.Vector2(45.2, 89.1)
# Affiche directement : pos=Vector2(45.2, 89.1)
print(f"{pos=}") 

# F-string complexe autorisé en 3.12 (multi-lignes et expressions imbriquées)
debug_info = f"Entity: {
    'Active' if entity.is_alive 
    else 'Dead' # Commentaire autorisé ici !
}"
```

---

## 5. Architecture de Jeu "State-of-the-Art"

Pour éviter que le code d'un jeu vidéo ne devienne un "plat de spaghettis" illisible après quelques semaines, structurez votre code selon ces principes rigoureux.

```
src/
├── main.py                           # Point d'entrée unique
├── config.py                         # Paramètres globaux (classe Settings persistante)
├── engine/
│   ├── game.py                       # Boucle principale (Init, Events, Update, Draw)
│   ├── audio.py                      # Gestionnaire de sons et musique
│   └── state.py                      # Machine à états (Menu, Game, Inventory...)
├── entities/
│   ├── base.py                       # Classe abstraite BaseEntity
│   ├── player.py                     # Classe Player (hérite de BaseEntity)
│   └── groups.py                     # Groupes de sprites personnalisés (Y-Sorted)
├── map/
│   ├── manager.py                    # Chargement des cartes et transitions
│   └── tmj_parser.py                 # Parser JSON Tiled (TMX optimisé JSON)
└── ui/
    ├── manager.py                    # Gestionnaire d'interfaces et de fenêtres
    └── components.py                 # Boutons, boîtes de dialogues, grilles d'inventaire
```

### 5.1 Séparation stricte de la Physique et du Rendu
* Le calcul physique s'effectue dans `update(dt)`.
* Le dessin s'effectue dans `draw(screen)`.
* **Aucun calcul physique ni déplacement ne doit être codé dans la méthode de dessin.**

### 5.2 Rendu Y-Sorted (Profondeur de champ 2.5D)
Pour un RPG 2.5D, les entités doivent se dessiner selon leur ordonnée Y (`centery` ou `bottom`). Les objets situés plus bas à l'écran se dessinent *au-dessus* des objets situés plus haut.
* **Best Practice** : Hériter de `pygame.sprite.Group` et surcharger la méthode de dessin.

```python
class YSortedCameraGroup(pygame.sprite.Group):
    def __init__(self):
        super().__init__()
        self.display_surface = pygame.display.get_surface()
        self.offset = pygame.Vector2()

    def custom_draw(self, camera_frect: pygame.FRect):
        # 1. Calculer le décalage de la caméra
        self.offset.x = camera_frect.x
        self.offset.y = camera_frect.y

        # 2. Trier les entités par leur coordonnée Y basse (bottom)
        # 3. Construire la render_queue pour fblits
        render_queue = []
        sorted_sprites = sorted(self.sprites(), key=lambda sprite: sprite.frect.bottom)
        
        for sprite in sorted_sprites:
            # Frustum Culling
            if camera_frect.colliderect(sprite.frect):
                render_pos = sprite.frect.topleft - self.offset
                render_queue.append((sprite.image, render_pos))

        # 4. Effectuer le rendu de masse ultra-rapide
        self.display_surface.fblits(render_queue)
```

### 5.3 Stabilisation du Delta Time (FPS Independence)
Les calculs physiques doivent être multipliés par le temps écoulé depuis la dernière frame (`dt` exprimé en secondes).
* **Attention au piège** : Si le jeu subit un gel (freeze) de 2 secondes (par exemple lors du chargement d'un niveau ou d'un break dans le débuggeur), le `dt` grimpe en flèche, ce qui peut projeter le joueur à travers les murs lors de la frame suivante.
* **Solution** : Clamper la valeur maximale du pas de temps (`dt_clamp`).

```python
class Game:
    def __init__(self):
        self.clock = pygame.Clock()
        self.target_fps = 60

    def run(self) -> None:
        while self.running:
            # dt en secondes (ex: 1/60 = 0.016s)
            raw_dt = self.clock.tick(self.target_fps) / 1000.0
            
            # Sécurité anti-téléportation : limiter dt à un équivalent de 10 FPS min (0.1s max)
            dt = min(raw_dt, 0.1)
            
            self.handle_events()
            self.update(dt)
            self.draw()
```

---

## 6. Anti-Patterns absolus à bannir (DO NOT)

| Pratique Interdite ❌ | Conséquence Technique | Pratique Recommandée ✅ |
| :--- | :--- | :--- |
| Instancier des objets (`Vector2`, `FRect`, `Surface`) dans la boucle principale | Explosion du ramasse-miettes (Garbage Collector), provoquant des micro-saccades de framerate régulières. | Instancier une fois dans le constructeur (`__init__`) et modifier les propriétés existantes (ex: utiliser `move_towards_ip`). |
| Rendre les textes ou charger les polices de caractères à chaque frame | Chute dramatique du FPS (< 15 FPS) car la génération de texture de police est extrêmement lourde pour le CPU. | Charger les polices une fois et pré-calculer/cacher les surfaces textuelles. |
| Utiliser `pygame.display.flip()` si seule une petite partie de l'écran change | Transfert inutile de données vers l'écran. | Utiliser `pygame.display.update(rect_list)` pour limiter la mise à jour aux zones de mouvements (Dirty Rects). |
| Utiliser des chemins d'accès bruts avec des slashes (`/` ou `\`) | Crash instantané lors du portage du jeu d'un OS à un autre (ex: de macOS vers Windows). | Toujours construire les chemins avec `os.path.join` ou `pathlib.Path`. |
| Omettre d'appeler `.convert()` ou `.convert_alpha()` sur une surface | Perte de 200 à 300% de vitesse d'affichage de l'image (CPU obligé de décoder les bits à chaque frame). | Appliquer la conversion dès le chargement de l'asset graphique. |
| Omettre de clamper le Delta Time (`dt`) | Traversée de murs, bugs de collisions physiques majeurs en cas de baisse soudaine de framerate ou pendant les pauses débug. | Clamper rigoureusement la valeur maximale de `dt`. |

---

## 7. Configuration de Qualité Préconisée

Pour garantir le maintien de ces standards élevés, configurez vos outils statiques avec ces paramètres :

### Configuration Pyright (`pyrightconfig.json`)
```json
{
  "include": ["src"],
  "exclude": ["**/__pycache__", "venv"],
  "pythonVersion": "3.12",
  "pythonPlatform": "All",
  "typeCheckingMode": "strict",
  "useLibraryCodeForTypes": true,
  "reportMissingTypeStubs": false
}
```

### Configuration Ruff (`pyproject.toml`)
```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = [
    "E",   # Erreurs pycodestyle
    "W",   # Avertissements pycodestyle
    "F",   # Pyflakes (détection bugs)
    "B",   # Bugbear (anti-patterns)
    "I",   # Isort (organisation des imports)
    "UP",  # Upgrade (modernisation vers Python 3.12)
    "T20"  # Interdire les prints sauvages (privilégier le logging)
]
```
