"""Décision prudente fondée sur une checklist humaine explicite."""
STATUSES = ("À vérifier", "Satisfait", "Non satisfait", "Sans objet")


def score_requirements(requirements: list[dict], *, review_complete: bool = False) -> dict:
    for item in requirements:
        if item.get("status") not in STATUSES:
            raise ValueError("Statut de vérification inconnu.")
    blockers = [r for r in requirements if r.get("mandatory") is True and r["status"] == "Non satisfait"]
    unresolved = [r for r in requirements if r["status"] == "À vérifier"]
    if blockers:
        return {"verdict": "No-Go", "reason": "Au moins une exigence obligatoire a été marquée non satisfaite."}
    if not requirements or unresolved or not review_complete:
        return {"verdict": "À vérifier", "reason": "La revue complète du dossier et la validation des exigences sont nécessaires."}
    return {"verdict": "Go", "reason": "La checklist a été validée et la revue complète a été confirmée par l’utilisateur."}
