# Bid/No-Bid Copilot

Application d’aide à l’analyse des appels d’offres pour une PME informatique.

## Démarrer sur Windows

Dans PowerShell, depuis le dossier du projet :

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Dans VS Code, sélectionner `.venv\Scripts\python.exe` via **Python: Select Interpreter**.
L’activation de l’environnement n’est pas nécessaire avec ces commandes.

## Les six espaces

- **Tableau de bord** : dossiers de la session, verdicts manuels, échéances à vérifier et avancement.
- **Mes appels d’offres** : import, lecture des pages et historique de session.
- **Analyse intelligente** : règles locales ou extraction structurée Groq avec citations vérifiées.
- **Profil entreprise** : capacités de la PME, enregistrées en session et exportables.
- **Décision Bid/No-Bid** : checklist manuelle et justification du verdict.
- **Assistant IA** : recherche locale ou réponse Groq fondée sur les fragments retrouvés par BM25.

Les écrans indiquent le moteur réellement utilisé. Aucun appel Groq automatique :
un clic et l’autorisation d’envoi du texte sont nécessaires. Le RAG est lexical BM25,
sans embeddings ni reranker. La décision reste fondée sur une checklist humaine.

## Configurer Groq et faire un premier essai

Les dépendances sont dans `requirements.txt`. Dans `.env` à la racine, renseigner
`GROQ_API_KEY` avec une clé créée depuis https://console.groq.com/keys. Le modèle
par défaut est `openai/gpt-oss-20b`, configurable via `GROQ_MODEL`. `.env` est ignoré
par Git ; ne jamais partager la clé dans un chat ou dans le code. `.env.example`
fournit le modèle de configuration. La clé est lue côté serveur, jamais exportée.

1. Relancer Streamlit depuis la racine après l’installation des dépendances.
2. Charger un vrai RC et éventuellement son CCTP dans **Mes appels d’offres**.
3. Dans **Analyse intelligente**, choisir **Groq · IA**, autoriser l’envoi du texte
   à Groq et cliquer sur **Extraire les exigences avec Groq**.
4. Relire chaque résumé et sa citation dans le PDF officiel, puis exporter le JSON.
5. Dans **Assistant IA**, choisir **Groq + RAG BM25** et poser une question précise.
   Les fragments sont sélectionnés localement, puis envoyés au modèle au clic.

Le client utilise le SDK Groq et JSON Schema strict, puis valide les données avec
Pydantic. Une citation sans fragment connu, vide ou absente du texte transmis fait
écarter la proposition concernée. Les variations d’espaces, espaces insécables et
retours à la ligne sont tolérées ; le texte original est restitué dans l’export.
Les autres modifications (mots, nombres, ponctuation) ne sont pas corrigées.
Une extraction partielle affiche le nombre de propositions rejetées ; si toutes
sont rejetées, aucun nouveau résultat n’est enregistré. Pour une réponse RAG,
une citation invalide fait rejeter la réponse entière.
Cela vérifie l’existence de la citation, pas l’exactitude de
l’interprétation. Les fragments sont limités à une page et l’extraction couvre tous
ceux qui contiennent du texte, par lots de 2 (maximum 120 fragments par dossier).
Si la limite de génération est atteinte, le lot est séparé en deux. Un fragment seul
dispose d’une unique nouvelle tentative avec un budget de sortie plus élevé. Les
réponses tronquées ne sont jamais interprétées comme une extraction complète.
Les lots terminés sont conservés en session. Après une limite de débit Groq (429),
un nouveau clic reprend les lots restants du même dossier et du même modèle.
L’écran affiche la progression ; une extraction interrompue n’est pas une analyse complète.
Sur une erreur 429, le délai `Retry-After` communiqué par Groq est respecté ; sans ce
délai, une pause indicative de 60 secondes est proposée. Les boutons Groq sont
désactivés pendant cette pause dans les deux écrans ; **Actualiser le délai** ne
fait aucun appel API. Les exigences déjà sourcées sont exportables en JSON partiel.
Cette pause ne permet pas de contourner un quota journalier épuisé.
Les catégories transmises au modèle utilisent des codes ASCII puis sont affichées
en français. Les prestations techniques et options sont distinctes des critères de
sélection. Une erreur Groq `json_validate_failed` déclenche une reprise bornée sur des
lots plus petits ; les autres erreurs 400 ne sont pas retentées automatiquement.
Les dossiers trop longs sont refusés avant tout envoi, sans troncature silencieuse.
Les pages sans texte sont signalées ; l’OCR reste à ajouter. Les erreurs et réponses
tronquées n’écrasent pas un précédent résultat valide. Chaque dossier conserve ses
propres résultats IA pendant la session.

Références : [SDK et démarrage Groq](https://console.groq.com/docs/quickstart),
[sorties structurées Groq](https://console.groq.com/docs/structured-outputs).

## Fonctionnalités disponibles

- Import de plusieurs PDF.
- Extraction du texte avec nom du document et numéro de page.
- Consultation page par page et export JSON.
- Signalement des pages sans texte et des PDF illisibles.
- Détection indicative RC / CCTP / CCAP / AE / BOAMP.
- Points clés repérés par règles avec document, page et citation exacte.
- Checklist manuelle avec verdict Go / No-Go / À vérifier et export JSON.

Cliquez sur **Charger ces documents** après avoir sélectionné les PDF. Les documents
restent disponibles dans les six écrans pendant la session. Charger un dossier
crée une nouvelle entrée d’historique avec sa propre checklist. Le dossier précédent
reste accessible dans **Historique de session**. **Nouvelle analyse** prépare un espace
vide sans supprimer les anciens dossiers. **Vider le dossier** efface uniquement le
dossier actif et sa checklist. Rien n’est sauvegardé sur disque
automatiquement ; les exports se téléchargent dans le navigateur.

Le verdict dépend des vérifications saisies par l’utilisateur : un critère obligatoire
non satisfait déclenche No-Go. Go exige une checklist résolue et la confirmation
d’une revue complète. Il ne constitue pas une validation automatique d’éligibilité.

## Organisation

`app.py` configure l’application et sélectionne l’écran. `core/` contient la lecture
PDF, la détection documentaire, le repérage par règles et la décision, sans importer
Streamlit. `ui/` contient les six écrans et la navigation. Les pages sont partagées
via `st.session_state["pages"]`. Le thème reste dans `.streamlit/config.toml` ;
`ui/styles.py` fournit un point d’extension sans injecter de CSS inutile.

`data/samples/` peut accueillir vos PDF locaux de test et `data/exports/` vos exports
enregistrés manuellement. Ces données sont exclues du suivi Git.

## Vérification

Un premier jeu d’évaluation hors ligne contient 20 cas issus du RC de test et une
copie de l’export initial. Voir [eval/README.md](eval/README.md). Pour régénérer le
rapport sans appel Groq :

```powershell
.\.venv\Scripts\python.exe -m eval.evaluate
```

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

L’import des PDF est local et en mémoire. Les modes Groq envoient le texte nécessaire
à un service externe après validation explicite. Le profil entreprise n’est pas envoyé.
Les scans nécessitant un OCR ne sont pas encore pris en charge.

## Prochaines étapes

1. Valider l’extraction et les réponses Groq sur un véritable DCE.
2. Comparer automatiquement les exigences avec le profil : Met / Not met / Unclear / Not found.
3. Proposer une recommandation argumentée, soumise à vérification humaine.
4. Évaluer sur des documents annotés, notamment les faux verdicts d’éligibilité.

Les tests automatisés utilisent des réponses Groq simulées : ils ne mesurent ni
la qualité réelle du modèle ni sa résistance aux injections sur un DCE. Le prompt
traite les sources comme des données non fiables ; aucun outil externe ni action
de candidature n’est donné au modèle. Les citations exactes et les formats structurés
ne suffisent pas à prouver la pertinence ou l’exhaustivité des conclusions.
