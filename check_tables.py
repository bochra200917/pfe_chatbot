import re
import os

ROOT = "."  # racine du projet

# Pattern strict : ne capture que les tables après FROM ou JOIN (usage SQL réel)
PATTERN_SQL_USAGE = re.compile(
    r"(?:FROM|JOIN)\s+(m38h_[a-zA-Z_]+)", re.IGNORECASE
)

tables_found = set()

for dirpath, dirnames, filenames in os.walk(ROOT):
    # Ignorer les dossiers inutiles
    dirnames[:] = [d for d in dirnames if d not in (
        ".git", "__pycache__", "venv", ".venv", "node_modules", "logs"
    )]
    for fname in filenames:
        if fname.endswith((".py", ".json", ".sql")):
            fpath = os.path.join(dirpath, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
                    matches = PATTERN_SQL_USAGE.findall(content)
                    if matches:
                        tables_found.update(matches)
            except Exception as e:
                print(f"Erreur lecture {fpath}: {e}")

print(f"\n{len(tables_found)} table(s) trouvee(s) dans le code (usage SQL reel FROM/JOIN) :\n")
for t in sorted(tables_found):
    print(f"  - {t}")

# ── Comparaison avec la whitelist ──────────────────────────────────────
ALLOWED_TABLES = [
    "m38h_facture", "m38h_facturedet", "m38h_commande", "m38h_commandedet",
    "m38h_societe", "m38h_socpeople", "m38h_product", "m38h_product_stock",
    "m38h_stock_mouvement", "m38h_entrepot", "m38h_paiement",
    "m38h_paiement_facture", "m38h_accounting_account",
    "m38h_accounting_bookkeeping", "m38h_bank", "m38h_bank_account",
    "m38h_user", "m38h_salary", "m38h_projet", "m38h_projet_task",
]

unused = set(ALLOWED_TABLES) - tables_found
used_not_whitelisted = tables_found - set(ALLOWED_TABLES)

print(f"\n--- Tables whitelistees mais JAMAIS utilisees dans FROM/JOIN ({len(unused)}) ---")
for t in sorted(unused):
    print(f"  - {t}")

print(f"\n--- Tables utilisees dans FROM/JOIN mais PAS dans la whitelist ({len(used_not_whitelisted)}) ---")
for t in sorted(used_not_whitelisted):
    print(f"  - {t}")