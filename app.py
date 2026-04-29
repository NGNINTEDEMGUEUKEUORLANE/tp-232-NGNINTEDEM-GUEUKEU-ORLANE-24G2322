import json
import os
import math
import re
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import csv
import io

app = Flask(__name__)
CORS(app)

DATA_FILE = "ventes.json"
# ==================== SECURITE ====================
ADMIN_PASSWORD = "alina329" 										
# ==================== CHARGEMENT / SAUVEGARDE ====================
def load_patients():
    """Charge les ventes depuis le fichier JSON"""
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return []

def save_patients(patients):
    """Sauvegarde les ventes dans le fichier JSON"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(patients, f, indent=2, ensure_ascii=False)

# ==================== VALIDATION ====================
def valider_nom(nom):
    """Valide le nom du client (optionnel, pas de chiffres)"""
    if not nom or nom.strip() == "":
        return True, ""
    nom = nom.strip()
    if len(nom) < 2:
        return False, "Le nom doit contenir au moins 2 caracteres"
    if len(nom) > 100:
        return False, "Le nom ne doit pas depasser 100 caracteres"
    if re.search(r'\d', nom):
        return False, "Le nom ne doit pas contenir de chiffres"
    if not re.match(r'^[a-zA-ZÀ-ÿ\s\-]+$', nom):
        return False, "Caracteres autorises : lettres, espaces et tirets"
    return True, ""

def valider_age(age):
    """Valide l'age (obligatoire, 18-120, entier)"""
    if age is None or age == "":
        return False, "L'age est obligatoire"
    try:
        age = float(age)
        if age < 0:
            return False, "L'age ne peut pas etre negatif"
        if age < 18:
            return False, "L'age minimum est de 18 ans"
        if age > 120:
            return False, "L'age maximum est de 120 ans"
        if not age.is_integer():
            return False, "L'age doit etre un nombre entier"
        return True, ""
    except (ValueError, TypeError):
        return False, "Veuillez entrer un nombre valide pour l'age"

def valider_sexe(sexe):
    """Valide le sexe (obligatoire)"""
    if not sexe:
        return False, "Le sexe est obligatoire"
    if sexe not in ["Homme", "Femme"]:
        return False, "Le sexe doit etre 'Homme' ou 'Femme'"
    return True, ""

def valider_prix(prix):
    """Valide le prix unitaire (obligatoire, > 0, max 10M FCFA)"""
    if prix is None or prix == "":
        return False, "Le prix unitaire est obligatoire"
    try:
        prix = float(prix)
        if prix < 0:
            return False, "Le prix ne peut pas etre negatif"
        if prix == 0:
            return False, "Le prix doit etre superieur a 0 FCFA"
        if prix > 10000000:
            return False, "Le prix maximum est de 10 000 000 FCFA"
        return True, ""
    except (ValueError, TypeError):
        return False, "Veuillez entrer un nombre valide pour le prix"

def valider_quantite(quantite):
    """Valide la quantite (obligatoire, > 0, entier, max 1000)"""
    if quantite is None or quantite == "":
        return False, "La quantite est obligatoire"
    try:
        quantite = float(quantite)
        if quantite < 0:
            return False, "La quantite ne peut pas etre negative"
        if quantite == 0:
            return False, "La quantite doit etre superieure a 0"
        if not quantite.is_integer():
            return False, "La quantite doit etre un nombre entier"
        if quantite > 1000:
            return False, "La quantite maximum est de 1000 articles"
        return True, ""
    except (ValueError, TypeError):
        return False, "Veuillez entrer un nombre valide pour la quantite"

def valider_satisfaction(satisfaction):
    """Valide la satisfaction (optionnelle, 1-5)"""
    if satisfaction is None or satisfaction == "":
        return True, ""
    try:
        sat = float(satisfaction)
        if sat < 0:
            return False, "La satisfaction ne peut pas etre negative"
        if sat < 1 or sat > 5:
            return False, "La satisfaction doit etre entre 1 et 5"
        return True, ""
    except (ValueError, TypeError):
        return False, "Veuillez entrer un nombre valide pour la satisfaction"

def valider_achats(achats):
    """Valide les achats precedents (optionnel, 0-999, entier)"""
    if achats is None or achats == "":
        return True, ""
    try:
        achats = float(achats)
        if achats < 0:
            return False, "Le nombre d'achats ne peut pas etre negatif"
        if not achats.is_integer():
            return False, "Le nombre d'achats doit etre un nombre entier"
        if achats > 999:
            return False, "Le nombre d'achats maximum est de 999"
        return True, ""
    except (ValueError, TypeError):
        return False, "Veuillez entrer un nombre valide pour les achats"

def valider_remise(remise):
    """Valide la remise (optionnelle, 0-100%)"""
    if remise is None or remise == "":
        return True, ""
    try:
        remise = float(remise)
        if remise < 0:
            return False, "La remise ne peut pas etre negative"
        if remise > 100:
            return False, "La remise maximum est de 100%"
        return True, ""
    except (ValueError, TypeError):
        return False, "Veuillez entrer un nombre valide pour la remise"

def valider_ville(ville):
    """Valide la ville (optionnelle, pas de chiffres)"""
    if not ville or ville.strip() == "":
        return True, ""
    ville = ville.strip()
    if len(ville) > 100:
        return False, "Le nom de la ville ne doit pas depasser 100 caracteres"
    if re.search(r'\d', ville):
        return False, "La ville ne doit pas contenir de chiffres"
    if not re.match(r'^[a-zA-ZÀ-ÿ\s\-]+$', ville):
        return False, "Caracteres autorises : lettres, espaces et tirets"
    return True, ""

def valider_paiement(paiement):
    """Valide le mode de paiement (obligatoire)"""
    if not paiement:
        return False, "Le mode de paiement est obligatoire"
    modes_valides = ["Mobile Money", "Carte bancaire", "Especes", "Virement"]
    if paiement not in modes_valides:
        return False, f"Mode de paiement invalide. Choisir parmi : {', '.join(modes_valides)}"
    return True, ""

def valider_categories(categories):
    """Valide les categories de produits"""
    if not categories:
        return True, ""
    categories_valides = ["Electronique", "Mode", "Alimentation", "Maison",
                         "Beaute", "Sport", "Livres", "Autres"]
    if isinstance(categories, list):
        for cat in categories:
            if cat and cat not in categories_valides:
                return False, f"Categorie invalide : {cat}"
    return True, ""

def valider_donnees(data):
    """Valide toutes les donnees et retourne la liste des erreurs"""
    erreurs = []
    
    valid, msg = valider_nom(data.get("nom", ""))
    if not valid: erreurs.append(msg)
    
    valid, msg = valider_age(data.get("age"))
    if not valid: erreurs.append(msg)
    
    valid, msg = valider_sexe(data.get("sexe"))
    if not valid: erreurs.append(msg)
    
    valid, msg = valider_prix(data.get("poids"))
    if not valid: erreurs.append(msg)
    
    valid, msg = valider_quantite(data.get("taille"))
    if not valid: erreurs.append(msg)
    
    valid, msg = valider_satisfaction(data.get("glycemie"))
    if not valid: erreurs.append(msg)
    
    valid, msg = valider_achats(data.get("pression_sys"))
    if not valid: erreurs.append(msg)
    
    valid, msg = valider_remise(data.get("pression_dia"))
    if not valid: erreurs.append(msg)
    
    valid, msg = valider_ville(data.get("commune", ""))
    if not valid: erreurs.append(msg)
    
    valid, msg = valider_paiement(data.get("paiement"))
    if not valid: erreurs.append(msg)
    
    valid, msg = valider_categories(data.get("pathologies", []))
    if not valid: erreurs.append(msg)
    
    return erreurs

# ==================== CALCULS ====================
def compute_imc(poids, taille):
    """Calcule le total de la commande (prix x quantite)"""
    if poids and taille and taille > 0:
        return round(poids * taille, 2)
    return None

def compute_stats(values):
    """Calcule les statistiques descriptives"""
    if not values:
        return {}
    values_sorted = sorted(values)
    n = len(values)
    mean = sum(values) / n
    variance = sum((x - mean) ** 2 for x in values) / n
    std = math.sqrt(variance)
    q1 = values_sorted[int(0.25 * n)] if int(0.25 * n) < n else values_sorted[0]
    q2 = values_sorted[int(0.50 * n)] if int(0.50 * n) < n else values_sorted[0]
    q3 = values_sorted[int(0.75 * n)] if int(0.75 * n) < n else values_sorted[-1]
    return {
        "count": n,
        "moyenne": round(mean, 2),
        "ecart_type": round(std, 2),
        "minimum": round(min(values), 2),
        "maximum": round(max(values), 2),
        "Q1": round(q1, 2),
        "Q2": round(q2, 2),
        "Q3": round(q3, 2)
    }

def pearson_corr(x, y):
    """Calcule la correlation de Pearson"""
    n = len(x)
    if n < 2:
        return 0
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    num = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    den_x = sum((xi - mean_x) ** 2 for xi in x)
    den_y = sum((yi - mean_y) ** 2 for yi in y)
    if den_x == 0 or den_y == 0:
        return 0
    return round(num / math.sqrt(den_x * den_y), 4)

# ==================== NETTOYAGE (SECURISE) ====================
@app.route("/api/nettoyer", methods=["POST"])
def nettoyer_base():
    """Nettoie la base de donnees des valeurs erronees"""
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {ADMIN_PASSWORD}":
        return jsonify({"error": "Acces refuse. Mot de passe admin requis."}), 401
    
    patients = load_patients()
    if not patients:
        return jsonify({"error": "Base de donnees vide"}), 404
    
    modifications = 0
    for p in patients:
        if p.get("nom") and re.search(r'\d', str(p["nom"])):
            p["nom"] = re.sub(r'\d', '', str(p["nom"])).strip()
            if len(p["nom"]) < 2: p["nom"] = ""
            modifications += 1
        
        if p.get("age") is not None:
            if p["age"] < 0: p["age"] = abs(p["age"]); modifications += 1
            if p["age"] < 18: p["age"] = 18; modifications += 1
            if p["age"] > 120: p["age"] = 120; modifications += 1
            p["age"] = int(p["age"])
        
        if p.get("poids") is not None:
            if p["poids"] <= 0: p["poids"] = abs(p["poids"]) if p["poids"] != 0 else 1.0; modifications += 1
            if p["poids"] > 10000000: p["poids"] = 10000000.0; modifications += 1
        
        if p.get("taille") is not None:
            if p["taille"] <= 0: p["taille"] = abs(p["taille"]) if p["taille"] != 0 else 1; modifications += 1
            if p["taille"] > 1000: p["taille"] = 1000; modifications += 1
            p["taille"] = int(p["taille"])
        
        if p.get("poids") is not None and p.get("taille") is not None:
            p["imc"] = round(p["poids"] * p["taille"], 2); modifications += 1
        
        if p.get("glycemie") is not None:
            if p["glycemie"] < 0: p["glycemie"] = abs(p["glycemie"]); modifications += 1
            if p["glycemie"] < 1: p["glycemie"] = None; modifications += 1
            elif p["glycemie"] > 5: p["glycemie"] = 5.0; modifications += 1
        
        if p.get("pression_sys") is not None:
            if p["pression_sys"] < 0: p["pression_sys"] = abs(p["pression_sys"]); modifications += 1
            if p["pression_sys"] > 999: p["pression_sys"] = 999; modifications += 1
            p["pression_sys"] = int(p["pression_sys"])
        
        if p.get("pression_dia") is not None:
            if p["pression_dia"] < 0: p["pression_dia"] = abs(p["pression_dia"]); modifications += 1
            if p["pression_dia"] > 100: p["pression_dia"] = 100.0; modifications += 1
        
        if p.get("commune") and re.search(r'\d', str(p["commune"])):
            p["commune"] = re.sub(r'\d', '', str(p["commune"])).strip(); modifications += 1
    
    save_patients(patients)
    return jsonify({
        "message": f"Nettoyage termine. {modifications} modification(s) effectuee(s).",
        "modifications": modifications
    }), 200

# ==================== CRUD VENTES ====================
@app.route("/api/patients", methods=["GET"])
def get_patients():
    """Retourne toutes les ventes"""
    patients = load_patients()
    return jsonify(patients)

@app.route("/api/patients", methods=["POST"])
def add_patient():
    """Ajoute une nouvelle vente (publique)"""
    data = request.json
    if not data:
        return jsonify({"error": "Aucune donnee recue"}), 400
    
    erreurs = valider_donnees(data)
    if erreurs:
        return jsonify({"error": " | ".join(erreurs)}), 400

    patients = load_patients()
    new_id = max([p["id"] for p in patients], default=0) + 1

    poids = float(data["poids"])
    taille = int(float(data["taille"]))
    total = compute_imc(poids, taille)

    pathologies = data.get("pathologies", [])
    if isinstance(pathologies, list):
        pathologies_str = ",".join(pathologies) if pathologies else "Autres"
    else:
        pathologies_str = str(pathologies) if pathologies else "Autres"

    vente = {
        "id": new_id,
        "nom": data.get("nom", "").strip(),
        "age": int(float(data["age"])),
        "sexe": data["sexe"].strip(),
        "poids": poids,
        "taille": taille,
        "imc": total,
        "glycemie": float(data["glycemie"]) if data.get("glycemie") else None,
        "pression_sys": int(float(data["pression_sys"])) if data.get("pression_sys") else None,
        "pression_dia": float(data["pression_dia"]) if data.get("pression_dia") else None,
        "pathologies": pathologies_str,
        "commune": data.get("commune", "").strip(),
        "paiement": data["paiement"].strip(),
        "date_enregistrement": datetime.now().isoformat()
    }
    
    patients.append(vente)
    save_patients(patients)
    return jsonify({
        "message": "Vente enregistree avec succes",
        "id": new_id,
        "imc": total
    }), 201

@app.route("/api/patients/<int:patient_id>", methods=["PUT"])
def update_patient(patient_id):
    """Modifie une vente existante (securise)"""
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {ADMIN_PASSWORD}":
        return jsonify({"error": "Acces refuse. Mot de passe admin requis."}), 401
    
    data = request.json
    if not data:
        return jsonify({"error": "Aucune donnee recue"}), 400
    
    patients = load_patients()
    index = next((i for i, p in enumerate(patients) if p["id"] == patient_id), None)
    if index is None:
        return jsonify({"error": "Vente non trouvee"}), 404
    
    erreurs = valider_donnees(data)
    if erreurs:
        return jsonify({"error": " | ".join(erreurs)}), 400
    
    poids = float(data["poids"])
    taille = int(float(data["taille"]))
    total = compute_imc(poids, taille)
    
    pathologies = data.get("pathologies", [])
    if isinstance(pathologies, list):
        pathologies_str = ",".join(pathologies) if pathologies else "Autres"
    else:
        pathologies_str = str(pathologies) if pathologies else "Autres"
    
    patients[index].update({
        "nom": data.get("nom", "").strip(),
        "age": int(float(data["age"])),
        "sexe": data["sexe"].strip(),
        "poids": poids,
        "taille": taille,
        "imc": total,
        "glycemie": float(data["glycemie"]) if data.get("glycemie") else None,
        "pression_sys": int(float(data["pression_sys"])) if data.get("pression_sys") else None,
        "pression_dia": float(data["pression_dia"]) if data.get("pression_dia") else None,
        "pathologies": pathologies_str,
        "commune": data.get("commune", "").strip(),
        "paiement": data["paiement"].strip()
    })
    
    save_patients(patients)
    return jsonify({
        "message": f"Vente {patient_id} modifiee avec succes",
        "imc": total
    }), 200

@app.route("/api/patients/<int:patient_id>", methods=["DELETE"])
def delete_patient(patient_id):
    """Supprime une vente (securise)"""
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {ADMIN_PASSWORD}":
        return jsonify({"error": "Acces refuse. Mot de passe admin requis."}), 401
    
    patients = load_patients()
    patient = next((p for p in patients if p["id"] == patient_id), None)
    if not patient:
        return jsonify({"error": "Vente non trouvee"}), 404
    
    patients.remove(patient)
    save_patients(patients)
    return jsonify({"message": f"Vente {patient_id} supprimee avec succes"}), 200

# ==================== CARROUSELS ====================
@app.route("/api/carrousel/ventes", methods=["GET"])
def carrousel_ventes():
    patients = load_patients()
    if not patients: return jsonify([])
    dernieres = sorted(patients, key=lambda x: x.get("date_enregistrement", ""), reverse=True)[:8]
    return jsonify([{
        "id": p.get("id"), "client": p.get("nom") or "Client anonyme",
        "total": p.get("imc"), "ville": p.get("commune") or "Non specifie",
        "date": p.get("date_enregistrement", "")[:10] if p.get("date_enregistrement") else "",
        "paiement": p.get("paiement", "")
    } for p in dernieres])

@app.route("/api/carrousel/stats", methods=["GET"])
def carrousel_stats():
    patients = load_patients()
    if not patients: return jsonify([])
    total = len(patients)
    totals = [p.get("imc") for p in patients if p.get("imc")]
    satisf = [p.get("glycemie") for p in patients if p.get("glycemie")]
    ages = [p.get("age") for p in patients if p.get("age")]
    mm = len([p for p in patients if p.get("paiement") == "Mobile Money"])
    villes = len(set(p.get("commune") for p in patients if p.get("commune")))
    return jsonify([
        {"icon": "bi-cart-check", "valeur": str(total), "label": "Ventes totales"},
        {"icon": "bi-cash-stack", "valeur": f"{round(sum(totals)/len(totals)):,} FCFA".replace(",", " ") if totals else "0 FCFA", "label": "Panier moyen"},
        {"icon": "bi-star-fill", "valeur": f"{round(sum(satisf)/len(satisf), 1)}/5" if satisf else "--/5", "label": "Satisfaction client"},
        {"icon": "bi-graph-up-arrow", "valeur": f"{max(totals):,} FCFA".replace(",", " ") if totals else "0 FCFA", "label": "Plus grande vente"},
        {"icon": "bi-phone", "valeur": str(mm), "label": "Paiements Mobile Money"},
        {"icon": "bi-geo-alt", "valeur": str(villes), "label": "Villes couvertes"},
        {"icon": "bi-people", "valeur": f"{round(sum(ages)/len(ages))} ans" if ages else "-- ans", "label": "Age moyen clients"}
    ])

@app.route("/api/carrousel/categories", methods=["GET"])
def carrousel_categories():
    patients = load_patients()
    if not patients: return jsonify([])
    cats = {}
    for p in patients:
        if p.get("pathologies"):
            for cat in p["pathologies"].split(","):
                cat = cat.strip()
                if cat and cat != "Autres": cats[cat] = cats.get(cat, 0) + 1
    total = sum(cats.values())
    icones = {"Electronique": "bi-phone", "Mode": "bi-handbag", "Alimentation": "bi-cart",
              "Maison": "bi-house", "Beaute": "bi-palette", "Sport": "bi-trophy", "Livres": "bi-book"}
    return jsonify([{
        "icon": icones.get(cat, "bi-box"), "nom": cat,
        "pourcentage": round((count/total)*100) if total > 0 else 0, "count": count
    } for cat, count in sorted(cats.items(), key=lambda x: x[1], reverse=True)])

# ==================== STATISTIQUES ====================
@app.route("/api/stats/descriptives", methods=["GET"])
def stats_descriptives():
    patients = load_patients()
    if not patients: return jsonify({"total": 0, "message": "Aucune donnee"})
    ages = [p["age"] for p in patients if p.get("age") is not None]
    poids = [p["poids"] for p in patients if p.get("poids")]
    tailles = [p["taille"] for p in patients if p.get("taille")]
    imcs = [p["imc"] for p in patients if p.get("imc")]
    glycemies = [p["glycemie"] for p in patients if p.get("glycemie")]
    press_sys = [p["pression_sys"] for p in patients if p.get("pression_sys")]
    press_dia = [p["pression_dia"] for p in patients if p.get("pression_dia")]
    return jsonify({
        "total": len(patients), "age": compute_stats(ages), "poids": compute_stats(poids),
        "taille": compute_stats(tailles), "imc": compute_stats(imcs), "glycemie": compute_stats(glycemies),
        "pression": {"systolique": compute_stats(press_sys), "diastolique": compute_stats(press_dia)}
    })

@app.route("/api/correlation", methods=["GET"])
def correlation_matrix():
    patients = load_patients()
    if len(patients) < 3: return jsonify({"error": "Pas assez de donnees"})
    variables = ["age", "imc", "glycemie", "pression_sys", "pression_dia"]
    filtered = [p for p in patients if all(p.get(v) is not None for v in variables)]
    if len(filtered) < 3: return jsonify({"error": "Donnees insuffisantes"})
    data_map = {v: [p[v] for p in filtered] for v in variables}
    matrix = [[pearson_corr(data_map[v1], data_map[v2]) for v2 in variables] for v1 in variables]
    return jsonify({"variables": variables, "matrix": matrix})

@app.route("/api/stats/paiement", methods=["GET"])
def stats_by_paiement():
    patients = load_patients()
    if not patients: return jsonify({"error": "Aucune donnee"}), 404
    stats = {}
    for p in patients:
        mode = p.get("paiement", "Non specifie")
        if mode not in stats: stats[mode] = {"count": 0, "montant_total": 0, "satisfaction": []}
        stats[mode]["count"] += 1
        if p.get("imc"): stats[mode]["montant_total"] += p["imc"]
        if p.get("glycemie"): stats[mode]["satisfaction"].append(p["glycemie"])
    return jsonify({mode: {
        "count": d["count"], "montant_total": round(d["montant_total"], 2),
        "panier_moyen": round(d["montant_total"]/d["count"], 2) if d["count"] > 0 else 0,
        "satisfaction_moyenne": round(sum(d["satisfaction"])/len(d["satisfaction"]), 2) if d["satisfaction"] else None
    } for mode, d in stats.items()})

@app.route("/api/stats/categories", methods=["GET"])
def stats_by_categories():
    patients = load_patients()
    if not patients: return jsonify({"error": "Aucune donnee"}), 404
    cats_stats = {}
    for p in patients:
        if p.get("pathologies"):
            for cat in p["pathologies"].split(","):
                cat = cat.strip()
                if cat not in cats_stats: cats_stats[cat] = {"count": 0, "montant_total": 0}
                cats_stats[cat]["count"] += 1
                if p.get("imc"): cats_stats[cat]["montant_total"] += p["imc"]
    return jsonify({cat: {
        "count": d["count"], "montant_total": round(d["montant_total"], 2),
        "panier_moyen": round(d["montant_total"]/d["count"], 2) if d["count"] > 0 else 0
    } for cat, d in cats_stats.items()})

@app.route("/api/stats/age", methods=["GET"])
def stats_by_age():
    patients = load_patients()
    if not patients: return jsonify({"error": "Aucune donnee"}), 404
    tranches = {"18-25": [0, 0], "26-35": [0, 0], "36-50": [0, 0], "51+": [0, 0]}
    for p in patients:
        age = p.get("age")
        if age:
            t = "18-25" if age <= 25 else "26-35" if age <= 35 else "36-50" if age <= 50 else "51+"
            tranches[t][0] += 1
            if p.get("imc"): tranches[t][1] += p["imc"]
    return jsonify({t: {"count": c, "montant_total": round(mt, 2), "panier_moyen": round(mt/c, 2) if c > 0 else 0} for t, (c, mt) in tranches.items()})

@app.route("/api/stats/ville", methods=["GET"])
def stats_by_ville():
    patients = load_patients()
    if not patients: return jsonify({"error": "Aucune donnee"}), 404
    villes = {}
    for p in patients:
        v = p.get("commune", "").strip() or "Non specifie"
        if v not in villes: villes[v] = {"count": 0, "montant_total": 0}
        villes[v]["count"] += 1
        if p.get("imc"): villes[v]["montant_total"] += p["imc"]
    top = dict(sorted(villes.items(), key=lambda x: x[1]["count"], reverse=True)[:10])
    return jsonify({v: {"count": d["count"], "montant_total": round(d["montant_total"], 2), "panier_moyen": round(d["montant_total"]/d["count"], 2) if d["count"] > 0 else 0} for v, d in top.items()})

# ==================== EXPORT CSV ====================
@app.route("/api/export/csv", methods=["GET"])
def export_csv():
    patients = load_patients()
    if not patients: return "Aucune donnee a exporter", 404
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id","client","age","sexe","prix_unitaire_FCFA","quantite","total_commande_FCFA",
                     "satisfaction","achats_precedents","remise_pct","categories","ville","paiement","date"])
    for p in patients:
        writer.writerow([p.get("id"), p.get("nom"), p.get("age"), p.get("sexe"), p.get("poids"),
                        p.get("taille"), p.get("imc"), p.get("glycemie"), p.get("pression_sys"),
                        p.get("pression_dia"), p.get("pathologies"), p.get("commune"), p.get("paiement"),
                        p.get("date_enregistrement")])
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode('utf-8')), mimetype='text/csv',
                     as_attachment=True, download_name='export_ventes_shopdata.csv')

# ==================== PAGE D'ACCUEIL ====================
@app.route("/")
def serve_frontend():
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>ShopData Cam - API E-commerce</h1><p>Fichier index.html non trouve.</p>", 200

# ==================== LANCEMENT ====================
if __name__ == "__main__":
    print("=" * 60)
    print("  ShopData Cam - Serveur E-commerce")
    print("  http://localhost:5000")
    print("=" * 60)
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
