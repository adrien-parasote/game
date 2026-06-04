# Stratégie : Kitbashing / Stamp Scattering

Ce document définit la nouvelle architecture de génération de textures, passant d'un modèle purement mathématique (bruit abstrait) à un modèle d'assemblage d'éléments sémantiques (Kitbashing), tout en préservant le respect strict des palettes de couleurs et du *seamless*.

## Le Concept Central
L'algorithme dessine programmatiquement de petits "tampons" (stamps) en mémoire (en utilisant `PIL.ImageDraw` pour simuler des coups de pinceau) avec 3 niveaux de gris (Ombre, Demi-ton, Lumière). Ensuite, il répartit intelligemment ces tampons sur une toile de 32x32 pour créer une texture continue et riche sémantiquement, sans jamais nécessiter de fichiers PNG externes ni d'IA.

## Conséquences sur l'Architecture (Impact Scan)

1. **Remplacement du "Bruit" par des "Tampons Procéduraux"**
   - L'algorithme génère des formes vectorielles (brins d'herbe, cailloux) en niveaux de gris directement en mémoire.
   - Le slider `Density` contrôle combien de tampons sont appliqués sur l'image.
   - Plus besoin de fournir de fichiers PNG externes !

2. **Garantie du *Seamless* (Tuilage parfait)**
   - Quand l'algorithme "pose" un brin d'herbe aux coordonnées (30, 15), sachant que l'image fait 32x32, le brin va déborder à droite. 
   - L'algorithme coupera mathématiquement ce qui dépasse et le redessinera aux coordonnées (0, 15) sur le bord gauche (et gère aussi le haut/bas). Le tuilage parfait est ainsi garanti à 100%.

3. **Gestion stricte des Couleurs (Quantization / Palette) inspirée de TofuPixel**
   - Pour conserver la force de l'outil et respecter une palette de 4 couleurs (ex: GameBoy), les *stamps* fournis seront dessinés en 3 niveaux de gris spécifiques (+ fond transparent).
   - Le fond de la toile de 32x32 sera rempli avec la Couleur 0 (la plus sombre : le sol / les ombres profondes).
   - Le Gris Foncé du stamp (ex: RGB 85,85,85) sera mappé à la Couleur 1 (L'ombre du brin d'herbe).
   - Le Gris Moyen du stamp (ex: RGB 170,170,170) sera mappé à la Couleur 2 (Le ton de base du brin d'herbe).
   - Le Blanc du stamp (RGB 255,255,255) sera mappé à la Couleur 3 (La lumière/highlight sur le brin d'herbe).
   - Ainsi, l'herbe ressemblera à de l'herbe professionnelle (ombre, base, lumière), mais s'adaptera instantanément à n'importe quelle palette rétro sélectionnée dans l'UI.

## 7 Questions Stratégiques

| Question | Réponse pour cette feature |
|---|---|
| **1. Who is the user?** | Le développeur solo qui veut une texture sémantique (herbe, pierre) avec une belle structure artistique (inspirée des tutos TofuPixel) sans dessiner chaque pixel ni dépendre d'une IA. |
| **2. What problem does it solve?** | Le bruit mathématique abstrait manque de sémantique. L'IA est instable et coûteuse. Les stamps externes demandent du travail manuel. Les tampons procéduraux résolvent tout. |
| **3. What are the constraints?** | Doit rester 100% hors-ligne, sans IA, rapide, générer les formes en mémoire (`PIL.ImageDraw`), respecter la palette, et être tuilable (*seamless*). |
| **4. What does success look like?** | L'herbe ressemble visuellement à de l'herbe stylisée tout en étant mathématiquement "seamless" sans intervention manuelle ni image externe. |
| **5. What exists already?** | Le moteur de Live Preview, le système d'export `.tsx`, la gestion des palettes. Le `generator.py` sera réécrit pour dessiner et distribuer des formes en mémoire. |
| **6. What is the smallest slice?** | 1. Générateur de tampons (herbe) en PIL. 2. Algo de pose avec *wrapping* 2D. 3. Quantization par remplacement direct des 3 niveaux de gris. |
| **7. What are the metrics?** | Temps de génération < 0.2s pour le *Live Preview*. Respect de la palette à 100%. |
