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


## Prototype local pour la soutenance du 3 novembre 2026

Cette branche ajoute **Prototype local** dans la navigation : une démo entièrement hors ligne avec trois documents **fictifs**, des références page/document, des passages candidats, et un avertissement sur deux dates limites divergentes. Elle ne change pas les résultats historiques de `eval/`.

### Installation locale (Ubuntu 24.04 / WSL2)

```bash
git switch feature/local-demo-scoping-alignment
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m streamlit run app.py
```

Sur Windows, utiliser la procédure PowerShell décrite en tête de ce README, puis sélectionner **Prototype local** dans la barre latérale. Cliquer sur **Charger le dossier fictif (3 documents)**. La recherche BM25 et la vérification indicative des dates ne nécessitent ni Groq, ni Ollama, ni connexion Internet.

### Hybrid RAG et réponse locale (facultatifs)

Pour montrer le chemin technique de la scoping canvas, installer et lancer Ollama **sur la machine locale** avec les modèles correspondants :

```bash
ollama pull bge-m3
ollama pull qwen2.5:7b
ollama serve
```

Si Ollama est déjà lancé comme service, ne pas démarrer une seconde instance. Dans **Prototype local**, sélectionner **Hybrid BM25 + embeddings Ollama**, puis **Rechercher les passages**. Cliquer sur **Générer une réponse avec Ollama** uniquement après avoir vérifié que les passages pertinents ont été retrouvés. Des modèles différents peuvent être sélectionnés par `OLLAMA_EMBED_MODEL`, `OLLAMA_MODEL` et `OLLAMA_BASE_URL` (HTTP localhost seulement). Le mode hybride indexe temporairement les fragments par requête ; **Chroma / index persistant et reranking ne sont pas encore implémentés**.

### Évaluation, sécurité et limites

Lire `docs/SYSTEM_CARD.md`, `docs/DEMO_SCRIPT.md`, `docs/EVALUATION_REPORT.md` et `docs/RED_TEAM_LOG.md`. Les tests unitaires sur les dates et le classement hybride sont déterministes et ne démontrent pas la qualité réelle des LLM. L'ancienne évaluation contient seulement 20 références initiales d'un marché historique ; elle doit encore être relue indépendamment. Les citations trouvées ne garantissent pas que leur interprétation est correcte. Les avertissements sur les échéances sont des candidats à vérifier manuellement et **non des décisions juridiques**.

**Sources et jeux de données :** le dossier fictif est écrit spécifiquement pour la démonstration. Pour une analyse réelle, charger les PDFs officiels téléchargeables et vérifier les droits de réutilisation, la version, les éventuels rectificatifs et les pages sans texte. L'outil ne soumet pas de candidature.

**Utilisation d'assistants IA :** cette branche a été rédigée avec l'aide de ChatGPT pour la conception, la programmation et la documentation ; chaque membre de l'équipe doit relire les modifications et pouvoir justifier les résultats.

## Périmètre après retour du superviseur (2 novembre 2026)

**Source des avis en production : BOAMP / DILA uniquement**, via l'API publique OpenDataSoft. L'écran **Avis BOAMP** récupère **un identifiant exact** (ex. `26-99630`), affiche les champs publics et leur provenance et renvoie vers le lien officiel. Il ne se connecte à **aucun profil acheteur** et ne tente pas de récupérer le RC/CCTP/CCAP derrière un login. Ces documents peuvent être ajoutés manuellement *uniquement s'ils sont librement accessibles et réutilisables*, et ne sont pas revendiqués comme obtenus par l'API BOAMP. Le texte brut BOAMP et ses champs ne suffisent pas à démontrer l'éligibilité d'une entreprise.

### Comparaison avec le gold set

La référence de 20 cas du RC 2024 sert de contrôle historique ; elle **ne représente pas un jeu d'avis BOAMP diversifié**. L'export Groq historique est un pipeline d'**extraction structurée** (PAS un baseline prompt-only).

```bash
python -m eval.field_metrics
# Pour un baseline réellement prompt-only à partir du même RC, sans retrieval :
python -m eval.run_prompt_only --backend groq
python -m eval.field_metrics --compare eval/prompt_only_groq.json
# Alternative uniquement locale, avec un modèle différent :
python -m eval.run_prompt_only --backend ollama
python -m eval.field_metrics --compare eval/prompt_only_ollama.json
```

Ces commandes exigent le PDF historique local (`eval/README.md`). La commande Groq exige une clé définie dans `.env` et envoie le PDF au fournisseur **uniquement lorsque vous la lancez** ; à exécuter uniquement pour des documents publics et autorisés. La variante Ollama ne quitte pas l'ordinateur, mais le modèle différent empêche d'attribuer les écarts uniquement au RAG. Le rapport est généré à `eval/reports/field_metrics.json`.

### Résultat de contrôle automatique sur l'ancien export (historique, non validé humainement)

- Exacte citation sur la bonne page / cas de référence : **15/20**.
- **Valeur exigée présente dans le résumé ET passage source correspondant : 10/20 = 50%**, Wilson 95% **29,9%–70,1%**.
- **Date/heure exactes dans le résumé : 0/1**, Wilson 95% **0%–79,4%**.
- **Baseline prompt-only : non mesuré tant que la génération n'a pas réellement tourné.**
- Les vingt vérifications sont des chaînes normalisées strictes ; c'est un **proxy**, pas une validation sémantique, un rappel exhaustif, ni une mesure de généralisation. Un seul dossier de consultation = observations corrélées.

Une **contradiction de dates** figure dans le dossier fictif de démonstration : l'interface affiche en évidence **REQUIRES VERIFICATION / À VÉRIFIER** et toutes les citations. Une annonce BOAMP marquée `RECTIFICATIF` ou liée à une autre affiche également une alerte.


## Correctifs de démonstration du 3 novembre 2026

- **BOAMP** : le champ de recherche propose désormais l'avis BOAMP `26-99630` (identifiant présent dans la liste publique DILA), au lieu d'un identifiant d'essai non confirmé. La requête API demande seulement les champs utiles via `select=`, pour ne pas télécharger les structures XML volumineuses. Les erreurs HTTP, DNS et JSON sont distinguées. **Le test en direct est nécessaire sur le poste WSL**, car le CI teste des réponses simulées.
- **Plan B BOAMP** : bouton **Charger un exemple réel BOAMP (copie hors ligne)**. Ce résultat est explicitement marqué « NOT LIVE », avec une échéance à vérifier ; il ne constitue pas une preuve de fonctionnement de l'API.
- **Ollama** : dans **Analyse intelligente**, choisissez **Ollama · local**, après avoir chargé le dossier fictif dans **Prototype local**, puis cliquez sur **Extraire localement avec Ollama**. Extraction structurée fragment par fragment, citation exacte contrôlée, reprise en session ; aucun appel Groq. `qwen2.5:7b` doit être installé et Ollama démarré. Le système peut rejeter des propositions non sourcées ; la qualité sémantique reste à évaluer.
- **Groq** : une clé présente dans `.env` ne prouve pas son autorisation. Une erreur HTTP 401 signale l'authentification ; HTTP 403 signale une permission insuffisante. Si Groq est inaccessible, utilisez Ollama ou les règles locales.

Pour tester directement l'API sur Ubuntu/WSL (aucune clé API requise) :

```bash
curl --fail-with-body -sS -G \
  'https://boamp-datadila.opendatasoft.com/api/explore/v2.0/catalog/datasets/boamp/records' \
  --data-urlencode 'select=idweb,objet,nomacheteur,datelimitereponse,dateparution,etat' \
  --data-urlencode 'where=idweb="26-99630"' \
  --data-urlencode 'limit=1'
```

Si le service répond `{"results": [...]}`, les données sont issues de l'API ; si les résultats sont vides, vérifier l'ID/le jeu de données. Si `curl` échoue, relever le code HTTP ou l'erreur DNS et utiliser le plan B pour la démonstration.


## xAI Grok provider — separate from Groq

Grok is xAI's model service; it does **not** use the Groq key. Configure in the ignored .env file (do not commit or paste tokens):

    XAI_API_KEY=<paste-your-key-locally>
    XAI_MODEL=grok-4.7

The app uses the xAI Responses API at https://api.x.ai/v1/responses with strict JSON Schema, Pydantic validation and page-bound exact-citation checking. xAI is a paid external provider. No text is sent until you explicitly authorize and press a Grok action button. This is separate from **Groq · IA** and **Ollama · local**.

- Load a public BOAMP record or a fictitious dossier.
- In **Analyse intelligente**, select **Grok · xAI**, authorize transmission, then click **Extraire les exigences avec Grok (xAI)**.
- In **Assistant IA**, select **Grok (xAI) + RAG BM25** for BM25-grounded questions.
- For a *real* Grok prompt-only evaluation: python -m eval.run_prompt_only --backend grok, then python -m eval.field_metrics --compare eval/prompt_only_grok.json. This is a new model and not a controlled within-model Groq comparison.

Citations verify that quotes occur in transmitted sources, **not** the semantic correctness of interpretations. Pages without OCR are still not analyzed. Do not send private documents without appropriate authorization. The model must be enabled for your xAI account and can incur charges. The application does not store the xAI key or place it in exported JSON.

### BOAMP live response correction

The official OpenDataSoft BOAMP endpoint was confirmed from the user's Ubuntu/WSL terminal: HTTP 200 for notice 26-99630. Its actual JSON nests records under records[].record.fields; the older reader assumed results[]. The app now handles both, and selects only six known public fields to avoid unsupported-field API errors.
