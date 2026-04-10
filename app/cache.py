# app/cache.py
# Cache en mémoire avec stratégie d'invalidation intelligente
# Basée sur : fréquence d'accès + criticité des données + TTL

import time
import hashlib
import json
from threading import Lock


# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────

# TTL (Time To Live) par catégorie de template — en secondes
TTL_CONFIG = {
    # Données très dynamiques (paiements, factures récentes) → TTL court
    "get_factures_non_payees":         60,    # 1 minute
    "get_factures_partiellement_payees": 60,  # 1 minute
    "get_total_paiements":             60,    # 1 minute

    # Données moyennement dynamiques (ventes mensuelles) → TTL moyen
    "get_total_ventes_mois":           300,   # 5 minutes
    "get_factures_between":            300,   # 5 minutes
    "get_factures_par_client":         300,   # 5 minutes
    "get_factures_negatives":          300,   # 5 minutes

    # Données peu dynamiques (stocks, clients) → TTL long
    "get_produits_stock_faible":       600,   # 10 minutes
    "get_clients_multiple_commandes":  600,   # 10 minutes
}

DEFAULT_TTL      = 300   # 5 minutes par défaut
MAX_CACHE_SIZE   = 100   # nombre maximum d'entrées en cache
MIN_ACCESS_COUNT = 2     # nombre minimum d'accès pour garder en cache

class CacheEntry:
    """Entrée du cache avec métadonnées"""
    def __init__(self, result, ttl, template_name):
        self.result        = result
        self.template_name = template_name
        self.created_at    = time.time()
        self.expires_at    = time.time() + ttl
        self.access_count  = 1
        self.last_accessed = time.time()

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def touch(self):
        """Met à jour les stats d'accès"""
        self.access_count += 1
        self.last_accessed = time.time()

    def ttl_remaining(self) -> float:
        return max(0, self.expires_at - time.time())


class ChatbotCache:
    """
    Cache en mémoire avec stratégie d'invalidation intelligente.

    Stratégie :
    - TTL variable selon la criticité du template
    - Éviction LFU (Least Frequently Used) quand le cache est plein
    - Invalidation automatique des entrées expirées
    """

    def __init__(self):
        self._cache: dict = {}
        self._lock  = Lock()
        self._stats = {
            "hits":        0,
            "misses":      0,
            "evictions":   0,
            "expirations": 0
        }

    def _make_key(self, template_name: str, params: dict) -> str:
        """Génère une clé unique basée sur template + paramètres"""
        key_data = json.dumps(
            {"template": template_name, "params": params},
            sort_keys=True,
            ensure_ascii=False
        )
        return hashlib.md5(key_data.encode()).hexdigest()

    def get(self, template_name: str, params: dict):
        """
        Récupère un résultat depuis le cache.
        Retourne None si absent ou expiré.
        """
        key = self._make_key(template_name, params)

        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._stats["misses"] += 1
                return None

            if entry.is_expired():
                del self._cache[key]
                self._stats["expirations"] += 1
                self._stats["misses"] += 1
                return None

            entry.touch()
            self._stats["hits"] += 1
            return entry.result

    def set(self, template_name: str, params: dict, result):
        """
        Stocke un résultat dans le cache.
        Applique le TTL selon la criticité du template.
        """
        key = self._make_key(template_name, params)
        ttl = TTL_CONFIG.get(template_name, DEFAULT_TTL)

        with self._lock:
            # Éviction si cache plein
            if len(self._cache) >= MAX_CACHE_SIZE:
                self._evict()

            self._cache[key] = CacheEntry(result, ttl, template_name)

    def invalidate(self, template_name: str = None):
        """
        Invalide les entrées du cache.
        Si template_name fourni : invalide uniquement ce template.
        Sinon : invalide tout le cache.
        """
        with self._lock:
            if template_name:
                keys_to_delete = [
                    k for k, v in self._cache.items()
                    if v.template_name == template_name
                ]
                for k in keys_to_delete:
                    del self._cache[k]
            else:
                self._cache.clear()

    def _evict(self):
        """
        Stratégie d'éviction LFU (Least Frequently Used).
        Supprime d'abord les entrées expirées,
        puis les entrées les moins accédées.
        """
        # 1. Supprimer les entrées expirées
        expired = [k for k, v in self._cache.items() if v.is_expired()]
        for k in expired:
            del self._cache[k]
            self._stats["evictions"] += 1

        # 2. Si encore plein, supprimer les LFU
        if len(self._cache) >= MAX_CACHE_SIZE:
            sorted_entries = sorted(
                self._cache.items(),
                key=lambda x: (x[1].access_count, x[1].last_accessed)
            )
            to_remove = sorted_entries[:MAX_CACHE_SIZE // 4]
            for k, _ in to_remove:
                del self._cache[k]
                self._stats["evictions"] += 1

    def get_stats(self) -> dict:
        """Retourne les statistiques du cache"""
        with self._lock:
            total      = self._stats["hits"] + self._stats["misses"]
            hit_rate   = round(self._stats["hits"] / total * 100, 2) if total > 0 else 0
            size       = len(self._cache)

            # Répartition par template
            by_template = {}
            for entry in self._cache.values():
                t = entry.template_name
                by_template[t] = by_template.get(t, 0) + 1

            return {
                "size":          size,
                "max_size":      MAX_CACHE_SIZE,
                "hits":          self._stats["hits"],
                "misses":        self._stats["misses"],
                "hit_rate":      hit_rate,
                "evictions":     self._stats["evictions"],
                "expirations":   self._stats["expirations"],
                "by_template":   by_template
            }

    def clear_expired(self):
        """Nettoie les entrées expirées — à appeler périodiquement"""
        with self._lock:
            expired = [k for k, v in self._cache.items() if v.is_expired()]
            for k in expired:
                del self._cache[k]
                self._stats["expirations"] += 1
            return len(expired)


# Instance globale du cache
chatbot_cache = ChatbotCache()