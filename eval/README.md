# Premier cas d’évaluation : RC Cœur d’Hérault 2024

Cette évaluation est locale : aucun appel Groq, aucune clé API nécessaire.
Elle ne modifie pas le modèle ni ses prompts. Son but est de figer un point de départ
avant de changer l’extraction et de comparer les versions sur la même référence.

## Fichiers

- `baseline_rc.json` : copie inchangée de l’export partagé par l’utilisateur (52 éléments).
- `gold_rc.jsonl` : 20 attentes rédigées à partir du RC, avec page, citation, ancrage,
  catégories acceptables, conditions et contrôles ciblés.
- `build_reference.py` : annotations lisibles et génération de la référence ; toutes
  les citations sont vérifiées dans le texte extrait. Ne pas adapter les attentes
  pour faire passer un résultat de modèle.
- `evaluate.py` : validation des sources et comparaison hors ligne.
- `reports/baseline.md` et `.json` : rapport initial reproductible.

La référence initiale est préparée par l’assistant et demande une validation
indépendante par l’équipe, idéalement par un responsable d’appels d’offres. Ce
n’est pas encore un jeu de référence validé par un expert. L’attente décrit le
contenu de ce document ancien, pas les règles juridiques actuelles.

## Source publique

[Page du marché](https://www.coeur-herault.fr/l-institution/marches-publics/marche-de-service-maintenance-informatique)

[RC original](https://www.coeur-herault.fr/sites/default/files//field/pdf/consultation-maintenance_informatique-reglement-juin2024-v1.pdf)

Placer le RC dans `data/samples/RC_Coeur_Herault_2024.pdf`. Le fichier PDF reste
exclu de Git. Son empreinte SHA-256 est enregistrée dans chaque cas : une autre
version du document provoque une erreur, plutôt qu’une comparaison trompeuse.

## Exécuter depuis la racine

```powershell
.\.venv\Scripts\python.exe -m eval.evaluate
```

Pour une prochaine extraction, enregistrer le nouvel export sans écraser la base,
puis lancer par exemple :

```powershell
.\.venv\Scripts\python.exe -m eval.evaluate --prediction data/exports/nouvelle_extraction.json --output eval/reports/nouvelle_extraction
```

## Ce que mesurent les résultats

- **Existence des citations** : citation exacte présente sur la page et dans le
  document annoncés. Ce contrôle ne garantit pas qu’elle étaye tout le résumé.
- **Couverture des passages de référence** : au moins une citation valide contient
  l’ancrage attendu, à la bonne page. Les citations de plusieurs éléments peuvent
  couvrir un même cas. Ce n’est pas un rappel exhaustif de toutes les exigences.
- **Alertes ciblées** : catégories, conditions explicites et motifs de négation
  définis pour ces cas. Les motifs sont sensibles à la formulation et ne remplacent
  pas une lecture humaine. Une paraphrase peut nécessiter une vérification manuelle.

Aucune précision sémantique, F1, éligibilité ou confiance statistique n’est calculée.
Les 20 cas proviennent du même marché : ils ne sont pas 20 marchés indépendants.
Les 10 propositions rejetées ne sont pas conservées dans l’export, donc leur
contenu et la justification de chaque rejet ne peuvent pas être évalués ici.

## Première lecture des résultats

L’export contient 55 citations existantes mais cinq passages attendus ne sont pas
retrouvés par les ancrages, dont les trois pondérations principales et les références.
Le résumé sur les surcoûts inverse le sens de sa source malgré une citation exacte.
Les champs conditionnels demandent un schéma qui distingue obligation et applicabilité.
Les catégories « Durées et calendrier », « Modalités de réponse », etc. expriment
des attentes de classement ; certaines ne sont pas encore proposées au modèle actuel.

Le RC lui-même contient des incohérences : refus de sous-traitance puis pièces DC4,
prix pondéré à 45 % puis méthode sur 50, annonce de quatre sous-critères alors que
trois sont listés. Les signaler pour vérification, sans décider arbitrairement
quelle version fait foi.

## Relecture en équipe

Dans `reports/baseline.md`, chaque cas a un attendu, les numéros d’éléments
correspondants et un champ « Validation humaine : À relire ». Pour chaque cas,
relire le PDF puis l’export et noter : correct / incomplet / incorrect / absent,
avec une justification. Traiter en premier `rc17` (négation), `rc08` et `rc09`
(conditions), puis `rc13` à `rc15` (pondérations). Une fois la référence validée,
corriger l’extraction puis comparer un nouvel export avec exactement les mêmes cas.
