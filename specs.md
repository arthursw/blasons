
1. Contexte et objectif du projet
L'objectif du projet est de telecharger automatiquement les blasons SVG de toutes les communes de France (environ 35 000 communes), depuis Wikipedia et Wikimedia Commons, afin de constituer une bibliotheque structuree et normalisee d'emblemes heraldiques.
Ces blasons sont ensuite renommes selon une convention precise et classes dans une arborescence hierarchique par region, puis par departement.

2. Convention de nommage des fichiers SVG
2.1 Format du nom de fichier
STKBL{DEP}_{CODE_POSTAL}_{NOM_VILLE}_{INDEX:02d}.svg
Exemples :
•	STKBL01_01400_L_ABERGEMENT_CLEMENCIAT_01.svg
•	STKBL01_01000_BOURG_EN_BRESSE_02_NON_VERIFIE.svg
2.2 Regles de nommage
•	DEP = code departement sur 2 chiffres (ex: 01, 75)
•	CODE_POSTAL = sur 5 chiffres (ex: 01400)
•	NOM_VILLE = depuis colonne nom_sans_accent du CSV, en MAJUSCULES, espaces et tirets remplaces par _
•	INDEX = numero d'ordre du blason pour cette commune (01, 02, 03...)
•	Blasons etrangers (arms, wappen...) : suffixe _NON_VERIFIE avant .svg
2.3 Structure des dossiers
Desktop/blasons/
  AUVERGNE_RHONE_ALPES/
    _AUVERGNE_RHONE_ALPES.svg
    01_AIN/
      _AIN.svg
      STKBL01_01400_L_ABERGEMENT_CLEMENCIAT_01.svg
      ...
