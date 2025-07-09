import time
import pandas as pd
import requests
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from tqdm import tqdm

def fetch_latest_inies_data():
    url = "https://base-inies.fr/api/SearchProduits"
    payload = {
        "typeDeclaration": 0,
        "cov": 0,
        "onlineDate": 0,
        "lieuProduction": 0,
        "perfUF": 0,
        "norme": 0,
        "onlyArchive": False
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        try:
            data = response.json()
            if isinstance(data, list):
                inies_ids = [str(item) for item in data]
                print(f"✅ {len(inies_ids)} IDs INIES récupérés.")
                return inies_ids
            else:
                print("⚠️ Format de données inattendu.")
                return []
        except json.JSONDecodeError:
            print("⚠️ Erreur de décodage JSON.")
            return []
    else:
        print(f"❌ Erreur d'accès à l'API INIES : {response.status_code} {response.reason}")
        return []

def classer_declaration(text):
    text = text.lower()
    if "déclaration individuelle" in text:
        return "Individuelle"
    elif "déclaration collective" in text:
        return "Collective"
    elif "donnée générique" in text:
        return "DED"
    elif "donnée conventionnelle pour la re2020" in text:
        return "RE2020"
    elif "donnée conventionnelle issue du référenciel" in text:
        return "EC"
    else:
        return "N/A"

def extract_product_data(id_inies, driver):
    try:
        driver.get(f"https://base-inies.fr/consultation/infos-produit/{id_inies}")
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="workSpace"]'))
        )
        time.sleep(2)

        product_name = "Nom introuvable"
        try:
            product_name = driver.find_element(By.XPATH, '//*[@id="workSpace"]/div/infos-produit/div/div[3]/informations-generales-read-only/div/div[1]/div[2]/span[1]').text.strip()
        except:
            pass

        declaration_type = "N/A"
        try:
            declaration_text = driver.find_element(By.XPATH, '//*[@id="workSpace"]/div/infos-produit/div/div[3]/informations-generales-read-only').text
            declaration_type = classer_declaration(declaration_text)
        except:
            pass

        try:
            driver.find_element(By.XPATH, '//*[@id="workSpace"]/div/infos-produit/div/div[2]/button[2]').click()
            time.sleep(1)
        except:
            pass

        unite_fonctionnelle = "N/A"
        try:
            unite_fonctionnelle = driver.find_element(By.XPATH, '//*[@id="workSpace"]/div/infos-produit/div/div[3]/unite-fonctionnelle-read-only/div/div[1]/div[2]/span').text.strip()
        except:
            pass

        duree_vie = "N/A"
        try:
            duree_vie = driver.find_element(By.XPATH, '//*[@id="workSpace"]/div/infos-produit/div/div[3]/unite-fonctionnelle-read-only/div/div[3]/div[2]/span').text.strip()
        except:
            pass

        try:
            driver.find_element(By.XPATH, '//*[@id="workSpace"]/div/infos-produit/div/div[2]/button[3]').click()
            time.sleep(1)
        except:
            pass

        try:
            driver.find_element(By.XPATH, '//*[contains(text(), "Afficher les phases optionnelles")]').click()
            time.sleep(2)
        except:
            pass

        impact_co2 = "N/A"
        d_benefices = 0
        try:
            headers = driver.find_elements(By.XPATH, '//*[@id="workSpace"]/div/infos-produit/div/div[3]/indicateurs-read-only//table/thead/tr/th')
            columns = {header.text.strip(): idx + 1 for idx, header in enumerate(headers)}

            if "Total cycle de vie" in columns:
                impact_co2_xpath = f'//*[@id="workSpace"]/div/infos-produit/div/div[3]/indicateurs-read-only//table/tbody/tr[1]/td[{columns["Total cycle de vie"]}]/span'
                impact_co2 = driver.find_element(By.XPATH, impact_co2_xpath).text.strip()

            if "D-Bénéfices et charges au-delà des frontières du système" in columns:
                d_benefices_xpath = f'//*[@id="workSpace"]/div/infos-produit/div/div[3]/indicateurs-read-only//table/tbody/tr[1]/td[{columns["D-Bénéfices et charges au-delà des frontières du système"]}]/span'
                d_benefices_text = driver.find_element(By.XPATH, d_benefices_xpath).text.strip()
                if d_benefices_text and d_benefices_text != "-":
                    d_benefices = d_benefices_text
        except:
            pass

        return [id_inies, product_name, declaration_type, unite_fonctionnelle, duree_vie, impact_co2, d_benefices]
    
    except Exception as e:
        return [id_inies, f"Erreur: {str(e)}", "N/A", "N/A", "N/A", "N/A", "N/A"]

def update_inies_data():
    file_path = "base_inies_complete.xlsx"
    updated_file_path = "base_inies_complete_MAJ.xlsx"

    df = pd.read_excel(file_path)
    df.columns = df.columns.str.strip()
    id_column_name = "ID INIES"

    latest_ids = fetch_latest_inies_data()
    if not latest_ids:
        print("❌ Aucune nouvelle donnée récupérée, arrêt de la mise à jour.")
        return

    existing_ids = set(df[id_column_name].astype(str))
    new_entries = set(map(str, latest_ids)) - existing_ids

    if new_entries:
        service = Service("C:\\Users\\john.chuah\\Documents\\Python\\msedgedriver.exe")
        options = Options()
        options.add_argument("--start-maximized")
        driver = webdriver.Edge(service=service, options=options)

        product_data = [extract_product_data(id_inies, driver) for id_inies in tqdm(new_entries, desc="Extraction", unit="produit")]
        driver.quit()

        new_df = pd.DataFrame(product_data, columns=[id_column_name, "Nom du produit", "Type de Déclaration", "Unité Fonctionnelle", "Durée de Vie", "Impact CO₂ (kg)", "D-Bénéfices"])
        df = pd.concat([df, new_df], ignore_index=True)

    df.to_excel(updated_file_path, index=False)

update_inies_data()
