# app/predictor.py
# Analyse prédictive et apprentissage continu
# Fonctionnalités :
#   - Prévision CA mois suivant (régression linéaire/polynomiale)
#   - Alertes stock rupture prévue
#   - Score fidélité clients
#   - Apprentissage continu depuis les feedbacks

import json
import os
import statistics
from datetime import datetime, timedelta
from collections import Counter
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.metrics import mean_absolute_error, r2_score

# ─────────────────────────────────────────────
# 1. Prévision CA mensuel (version ML améliorée)
# ─────────────────────────────────────────────

def predict_ca_next_month(monthly_data: list) -> dict:
    """
    Prédit le CA du mois suivant par régression polynomiale (degré 2).
    Gère les données partielles (mois en cours avec valeurs manquantes).

    Args:
        monthly_data: liste de dicts {"mois": "YYYY-MM", "CA_HT": float, "CA_TTC": float}

    Returns:
        dict avec predicted_ca_ht, predicted_ca_ttc, trend, confidence, method
    """
    # Filtrer les données valides (CA non nul et non None)
    valid_data = []
    for d in monthly_data:
        ca_ht = d.get("CA_HT")
        if ca_ht is not None and ca_ht != "" and float(ca_ht) > 0:
            valid_data.append({
                "mois": d["mois"],
                "CA_HT": float(ca_ht),
                "CA_TTC": float(d.get("CA_TTC", ca_ht * 1.19))
            })
    
    n = len(valid_data)
    
    if n < 2:
        return {
            "predicted_ca_ht":  None,
            "predicted_ca_ttc": None,
            "trend":            "insufficient_data",
            "confidence":       "low",
            "method":           "N/A",
            "message":          f"Au moins 2 mois de données nécessaires. Actuellement : {n} mois"
        }

    # Extraire les valeurs
    months = [d["mois"] for d in valid_data]
    values_ht = [d["CA_HT"] for d in valid_data]
    mean_y = statistics.mean(values_ht) if values_ht else 0
    
    # Créer des indices numériques pour la régression
    X = np.array(range(n)).reshape(-1, 1)
    y = np.array(values_ht)

    # ─────────────────────────────────────
    # ML MODEL : Régression polynomiale (degré 2)
    # Capture mieux les tendances saisonnières
    # ─────────────────────────────────────
    
    poly = PolynomialFeatures(degree=min(2, n-1))
    X_poly = poly.fit_transform(X)
    
    model = LinearRegression()
    model.fit(X_poly, y)
    
    # Prédiction pour le mois suivant (indice = n)
    X_next = poly.transform([[n]])
    predicted_ht = model.predict(X_next)[0]
    predicted_ht = max(0, round(float(predicted_ht), 2))
    predicted_ttc = round(predicted_ht * 1.19, 2) if predicted_ht > 0 else 0
    
    # Calcul du R² pour évaluer la qualité du modèle
    y_pred = model.predict(X_poly)
    r2 = r2_score(y, y_pred) if len(y) > 1 else 0
    
    # Calcul de l'erreur moyenne
    mae = mean_absolute_error(y, y_pred) if len(y) > 1 else 0
    
    # Tendance basée sur la pente de la régression linéaire simple
    simple_model = LinearRegression()
    simple_model.fit(X, y)
    slope = simple_model.coef_[0]
    
    if slope > 0.02 * mean_y:
        trend = "hausse"
    elif slope < -0.02 * mean_y:
        trend = "baisse"
    else:
        trend = "stable"
    
    # Confiance basée sur R² et nombre de points
    if n >= 6 and r2 > 0.7:
        confidence = "high"
    elif n >= 4 and r2 > 0.5:
        confidence = "medium"
    elif n >= 3:
        confidence = "medium"
    else:
        confidence = "low"
    
    # Variation par rapport au dernier mois
    last_ca = values_ht[-1]
    variation = round(((predicted_ht - last_ca) / last_ca * 100), 1) if last_ca != 0 else 0
    
    # Calcul du mois prédit (mois suivant après le dernier mois connu)
    last_month_str = months[-1]
    try:
        last_date = datetime.strptime(last_month_str, "%Y-%m")
        next_month = last_date + timedelta(days=32)
        predicted_month = next_month.strftime("%Y-%m")
    except:
        predicted_month = "?"
    
    return {
        "predicted_ca_ht":  predicted_ht,
        "predicted_ca_ttc": predicted_ttc,
        "predicted_month":  predicted_month,
        "trend":            trend,
        "confidence":       confidence,
        "method":           "polynomial_regression_degree2",
        "slope":            round(slope, 2),
        "r2_score":         round(r2, 3),
        "mae":              round(mae, 2),
        "variation_pct":    variation,
        "based_on_months":  n,
        "months_used":      months,
        "message":          f"Prévision basée sur {n} mois · R²={r2:.2f} · Tendance : {trend} ({variation:+.1f}%)"
    }


def predict_ca_multiple_months(monthly_data: list, months_ahead: int = 3) -> dict:
    """
    Prédit le CA pour plusieurs mois à venir.

    Args:
        monthly_data: données historiques
        months_ahead: nombre de mois à prédire (défaut: 3)

    Returns:
        dict avec historique, prédictions et métriques
    """
    valid_data = []
    for d in monthly_data:
        ca_ht = d.get("CA_HT")
        if ca_ht is not None and ca_ht != "" and float(ca_ht) > 0:
            valid_data.append({
                "mois": d["mois"],
                "CA_HT": float(ca_ht)
            })
    
    n = len(valid_data)
    
    if n < 2:
        return {
            "error": f"Données insuffisantes ({n}/2 mois minimum)",
            "historique": monthly_data,
            "predictions": []
        }
    
    # Préparer les données pour le modèle
    X = np.array(range(n)).reshape(-1, 1)
    y = np.array([d["CA_HT"] for d in valid_data])
    
    # Régression polynomiale
    degree = min(2, n-1)
    poly = PolynomialFeatures(degree=degree)
    X_poly = poly.fit_transform(X)
    
    model = LinearRegression()
    model.fit(X_poly, y)
    
    # Prédictions
    predictions = []
    last_date = datetime.strptime(valid_data[-1]["mois"], "%Y-%m")
    
    last_value = valid_data[-1]["CA_HT"]
    
    for i in range(1, months_ahead + 1):
        X_next = poly.transform([[n + i - 1]])
        pred_value = model.predict(X_next)[0]
        pred_value = max(0, round(float(pred_value), 2))
        
        # Date du mois prédit
        pred_date = last_date + timedelta(days=32 * i)
        pred_date = pred_date.replace(day=1)
        pred_month = pred_date.strftime("%Y-%m")
        
        # Variation
        if i == 1:
            variation = round(((pred_value - last_value) / last_value * 100), 1) if last_value != 0 else 0
        else:
            variation = round(((pred_value - predictions[-1]["CA_HT_predit"]) / predictions[-1]["CA_HT_predit"] * 100), 1) if predictions[-1]["CA_HT_predit"] != 0 else 0
        
        predictions.append({
            "mois": pred_month,
            "CA_HT_predit": pred_value,
            "CA_TTC_predit": round(pred_value * 1.19, 2),
            "variation_pct": variation
        })
    
    # Score du modèle
    y_pred = model.predict(X_poly)
    r2 = r2_score(y, y_pred) if len(y) > 1 else 0
    
    return {
        "historique": valid_data,
        "predictions": predictions,
        "r2_score": round(r2, 3),
        "based_on_months": n,
        "trend": "hausse" if predictions[0]["CA_HT_predit"] > valid_data[-1]["CA_HT"] else "baisse"
    }


# ─────────────────────────────────────────────
# 2. Alertes stock rupture
# ─────────────────────────────────────────────

def predict_stock_alert(stock_data: list, consumption_rate: float = 0.1) -> list:
    """
    Prédit les produits à risque de rupture dans les 30 jours.

    Args:
        stock_data: liste de dicts {"produit_ref": str, "produit_nom": str, "stock_disponible": int}
        consumption_rate: taux de consommation journalier estimé (fraction du stock initial)

    Returns:
        liste de produits avec niveau d'alerte
    """
    alerts = []

    for item in stock_data:
        stock = float(item.get("stock_disponible", 0) or 0)

        if stock <= 0:
            level = "rupture"
            days_remaining = 0
        else:
            # Estimation jours restants
            daily_consumption = max(0.1, stock * consumption_rate)
            days_remaining    = int(stock / daily_consumption)

            if days_remaining <= 7:
                level = "critique"
            elif days_remaining <= 15:
                level = "warning"
            elif days_remaining <= 30:
                level = "attention"
            else:
                level = "ok"

        if level != "ok":
            alerts.append({
                "produit_ref":     item.get("produit_ref", ""),
                "produit_nom":     item.get("produit_nom", ""),
                "stock_actuel":    stock,
                "jours_restants":  days_remaining,
                "niveau_alerte":   level,
                "action_suggérée": _stock_action(level)
            })

    # Trier par criticité
    order = {"rupture": 0, "critique": 1, "warning": 2, "attention": 3}
    alerts.sort(key=lambda a: order.get(a["niveau_alerte"], 9))

    return alerts


def _stock_action(level: str) -> str:
    actions = {
        "rupture":   "Commander immédiatement",
        "critique":  "Commander dans les 48h",
        "warning":   "Planifier une commande cette semaine",
        "attention": "Surveiller et planifier"
    }
    return actions.get(level, "")


# ─────────────────────────────────────────────
# 3. Score fidélité clients
# ─────────────────────────────────────────────

def compute_loyalty_score(client_data: list) -> list:
    """
    Calcule un score de fidélité pour chaque client.

    Args:
        client_data: liste de dicts {"client_id", "client_nom", "nb_commandes"}

    Returns:
        liste avec score et segment
    """
    if not client_data:
        return []

    max_cmd = max(float(d.get("nb_commandes", 0) or 0) for d in client_data)
    if max_cmd == 0:
        return client_data

    scored = []
    for item in client_data:
        nb  = float(item.get("nb_commandes", 0) or 0)
        score = round((nb / max_cmd) * 100, 1)

        if score >= 80:
            segment = "VIP"
        elif score >= 50:
            segment = "Fidèle"
        elif score >= 20:
            segment = "Régulier"
        else:
            segment = "Occasionnel"

        scored.append({
            **item,
            "loyalty_score": score,
            "segment": segment
        })

    scored.sort(key=lambda x: x["loyalty_score"], reverse=True)
    return scored


# ─────────────────────────────────────────────
# 4. Apprentissage continu depuis feedbacks
# ─────────────────────────────────────────────

FEEDBACK_FILE = "logs/feedback.jsonl"


def load_feedbacks() -> list:
    """Charge tous les feedbacks enregistrés."""
    if not os.path.exists(FEEDBACK_FILE):
        return []
    feedbacks = []
    with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    feedbacks.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return feedbacks


def get_learning_insights() -> dict:
    """
    Analyse les feedbacks pour identifier les patterns à améliorer.

    Returns:
        dict avec questions_problematiques, satisfaction_rate, suggestions
    """
    feedbacks = load_feedbacks()

    if not feedbacks:
        return {
            "total":                   0,
            "satisfaction_rate":       None,
            "questions_problematiques": [],
            "patterns_negatifs":       [],
            "suggestions":             []
        }

    total     = len(feedbacks)
    positifs  = [f for f in feedbacks if f.get("rating") == "positive"]
    negatifs  = [f for f in feedbacks if f.get("rating") == "negative"]

    satisfaction_rate = round(len(positifs) / total * 100, 1) if total > 0 else 0

    # Questions problématiques (feedbacks négatifs répétés)
    neg_questions = Counter(f.get("question", "") for f in negatifs)
    questions_prob = [
        {"question": q, "nb_signalements": n}
        for q, n in neg_questions.most_common(10)
        if n >= 1
    ]

    # Patterns dans les commentaires négatifs
    comments = [f.get("comment", "").lower() for f in negatifs if f.get("comment")]
    patterns = []
    keywords = {
        "mauvais résultat":  ["mauvais", "incorrect", "faux", "erreur"],
        "réponse incomplète": ["incomplet", "manque", "partiel"],
        "incompréhension":   ["compris", "comprenait", "sens", "voulais"],
        "lenteur":           ["lent", "long", "temps", "lenteur"]
    }
    for pattern, kws in keywords.items():
        count = sum(1 for c in comments if any(kw in c for kw in kws))
        if count > 0:
            patterns.append({"pattern": pattern, "occurrences": count})

    # Suggestions d'amélioration automatiques
    suggestions = []
    if satisfaction_rate < 70:
        suggestions.append("Satisfaction < 70% — revoir les templates les plus utilisés")
    if questions_prob:
        suggestions.append(f"{len(questions_prob)} question(s) signalée(s) — envisager de nouveaux patterns regex")
    for p in patterns:
        if p["pattern"] == "incompréhension" and p["occurrences"] >= 2:
            suggestions.append("Améliorer la détection des questions ambiguës")
        if p["pattern"] == "mauvais résultat" and p["occurrences"] >= 2:
            suggestions.append("Vérifier les requêtes SQL des templates concernés")

    return {
        "total":                   total,
        "positifs":                len(positifs),
        "negatifs":                len(negatifs),
        "satisfaction_rate":       satisfaction_rate,
        "questions_problematiques": questions_prob,
        "patterns_negatifs":       patterns,
        "suggestions":             suggestions,
        "derniere_analyse":        datetime.now().isoformat()
    }


def get_improvement_candidates() -> list:
    """
    Identifie les questions négatives qui pourraient améliorer
    la couverture du chatbot si ajoutées au golden set.
    """
    feedbacks = load_feedbacks()
    negatifs  = [f for f in feedbacks if f.get("rating") == "negative"]

    candidates = []
    seen = set()

    for fb in negatifs:
        q = fb.get("question", "").strip()
        if q and q not in seen:
            seen.add(q)
            candidates.append({
                "question":   q,
                "comment":    fb.get("comment", ""),
                "timestamp":  fb.get("timestamp", ""),
                "suggestion": "Ajouter au golden set comme cas d'échec"
            })

    return candidates