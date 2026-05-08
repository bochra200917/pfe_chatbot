import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from datetime import datetime, timedelta

def predict_ca_mensuel(historical_data: list, months_ahead: int = 1) -> dict:
    """
    Prédiction du CA mensuel basée sur les données historiques
    historical_data: liste de dict [{"mois": "2025-10", "CA_HT": 15000}, ...]
    """
    if len(historical_data) < 3:
        return {"error": "Données historiques insuffisantes (minimum 3 mois)"}
    
    # Convertir les dates en numériques
    df = pd.DataFrame(historical_data)
    df["mois_num"] = range(1, len(df) + 1)
    X = df[["mois_num"]].values
    y = df["CA_HT"].values
    
    # Régression polynomiale (degré 2 pour capturer les tendances)
    poly = PolynomialFeatures(degree=2)
    X_poly = poly.fit_transform(X)
    model = LinearRegression()
    model.fit(X_poly, y)
    
    # Prédiction
    last_month_num = len(df)
    predictions = []
    for i in range(1, months_ahead + 1):
        next_month_num = last_month_num + i
        X_pred = poly.transform([[next_month_num]])
        pred_value = model.predict(X_pred)[0]
        
        # Calculer la date du mois prédit
        last_date = datetime.strptime(df["mois"].iloc[-1], "%Y-%m")
        pred_date = last_date + timedelta(days=32*i)
        pred_date = pred_date.replace(day=1)
        
        predictions.append({
            "mois": pred_date.strftime("%Y-%m"),
            "CA_HT_predit": round(pred_value, 2),
            "variation_pct": None
        })
    
    # Calculer les variations
    for i, pred in enumerate(predictions):
        if i == 0:
            last_real = df["CA_HT"].iloc[-1]
            pred["variation_pct"] = round(((pred["CA_HT_predit"] - last_real) / last_real) * 100, 1) if last_real != 0 else 0
        else:
            prev_pred = predictions[i-1]["CA_HT_predit"]
            pred["variation_pct"] = round(((pred["CA_HT_predit"] - prev_pred) / prev_pred) * 100, 1) if prev_pred != 0 else 0
    
    return {
        "historique": historical_data,
        "predictions": predictions,
        "model_score": round(model.score(X_poly, y), 3),
        "tendance": "hausse" if predictions[0]["CA_HT_predit"] > df["CA_HT"].iloc[-1] else "baisse"
    }


def predict_stock_rupture(products: list, seuil: int = 5) -> list:
    """
    Prédiction des produits en risque de rupture
    products: liste de dict [{"produit_nom": "X", "stock_disponible": 10, ...}, ...]
    """
    alerts = []
    for p in products:
        # Récupérer le stock (supporte plusieurs noms de clé)
        stock_actuel = None
        for key in ["stock_disponible", "stock", "stock_actuel", "quantite", "qty"]:
            if key in p:
                stock_actuel = p[key]
                break
        
        if stock_actuel is None:
            continue
        
        # Récupérer le nom du produit
        produit_nom = None
        for key in ["produit_nom", "label", "nom", "produit", "name", "product_name"]:
            if key in p:
                produit_nom = p[key]
                break
        
        if produit_nom is None:
            produit_nom = "Inconnu"
        
        # Convertir en float
        try:
            stock_actuel = float(stock_actuel)
        except (ValueError, TypeError):
            continue
        
        # Ignorer les stocks négatifs (erreurs de données)
        if stock_actuel < 0:
            continue
        
        # Vérifier si le stock est inférieur au seuil
        if stock_actuel < seuil:
            alerts.append({
                "produit": str(produit_nom),
                "stock_actuel": stock_actuel,
                "seuil": seuil,
                "niveau_risque": "critique" if stock_actuel == 0 else "alerte_stock_faible"
            })
    
    return sorted(alerts, key=lambda x: x["stock_actuel"])


def predict_fidelite_clients(historique_commandes: list) -> list:
    """
    Prédiction de la fidélité des clients
    historique_commandes: liste de dict [{"nom": "X", "nombre_commandes": 10, "derniere_commande": "2026-03-15"}, ...]
    """
    predictions = []
    today = datetime.now().date()
    
    for client in historique_commandes:
        # Récupérer le nom du client
        client_nom = None
        for key in ["nom", "client", "societe", "name"]:
            if key in client:
                client_nom = client[key]
                break
        
        if client_nom is None:
            client_nom = "Inconnu"
        
        # Récupérer le nombre de commandes
        nb_cmd = None
        for key in ["nombre_commandes", "nb_commandes", "commandes", "count"]:
            if key in client:
                nb_cmd = client[key]
                break
        
        if nb_cmd is None:
            continue
        
        try:
            nb_cmd = int(nb_cmd)
        except (ValueError, TypeError):
            continue
        
        # Récupérer la date de dernière commande
        derniere = None
        for key in ["derniere_commande", "date_derniere_commande", "last_order_date"]:
            if key in client:
                derniere = client[key]
                break
        
        if derniere:
            try:
                if isinstance(derniere, str):
                    derniere_date = datetime.strptime(derniere, "%Y-%m-%d").date()
                else:
                    derniere_date = derniere
                jours_inactif = (today - derniere_date).days
            except Exception:
                jours_inactif = 999
        else:
            jours_inactif = 999
        
        # Score de fidélité (0-100)
        score_fidelite = min(100, (nb_cmd * 10) + (30 - min(30, jours_inactif)))
        score_fidelite = max(0, score_fidelite)
        
        # Prédiction de réachat
        if jours_inactif > 90:
            prediction_rachat = "faible"
        elif nb_cmd > 5 and jours_inactif < 30:
            prediction_rachat = "élevée"
        elif nb_cmd > 2:
            prediction_rachat = "moyenne"
        else:
            prediction_rachat = "à surveiller"
        
        predictions.append({
            "client": client_nom,
            "nb_commandes": nb_cmd,
            "jours_sans_achat": jours_inactif if jours_inactif < 999 else "N/A",
            "score_fidelite": score_fidelite,
            "prediction_rachat": prediction_rachat
        })
    
    return sorted(predictions, key=lambda x: -x["score_fidelite"])