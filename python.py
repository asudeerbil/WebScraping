import time
import datetime
import undetected_chromedriver as uc
import json
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import requests


def setup_driver():
    options = uc.ChromeOptions()
    prefs = {
        "profile.default_content_setting_values.geolocation": 2  # 2 = Konum iznini reddet
    }
    options.add_experimental_option("prefs", prefs)
    try:
        driver = uc.Chrome(options=options)
        print("Tarayıcı başarıyla başlatıldı, konum izni devre dışı bırakıldı.")
        return driver
    except Exception as e:
        print(f"Tarayıcı başlatılırken bir hata oluştu: {e}")
        return None


def search_google(driver, keyword, page=0):
    print(f"Google'a gidiyor, sayfa: {page//10 + 1}...")
    driver.get(f"https://www.google.com/search?q={keyword}&start={page}")
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "q"))
        )
        time.sleep(3)
    except Exception as e:
        print("Google arama hatası:", e)


def extract_ads(driver):
    print("Reklamlar aranıyor...")
    ad_data = []

    try:
        ads = WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div[data-text-ad='1']"))
        )
        print(f"{len(ads)} adet reklam bulundu.")

        for ad in ads:
            try:
                url_element = ad.find_element(By.CSS_SELECTOR, "a")
                url = url_element.get_attribute("href")

                if url:
                    ad_data.append({"url": url, "type": "Ad"})
                    print(f"Reklam URL'si alındı: {url}")
                else:
                    print("Geçersiz URL, atlanıyor...")

            except NoSuchElementException:
                print("Reklamın içinde URL bulunamadı, atlanıyor...")

    except TimeoutException:
        print("Reklam bulunamadı veya sayfa çok yavaş yüklendi!")

    return ad_data


def extract_organic_results(driver):
    print("Organik sonuçlar aranıyor...")
    organic_data = []

    try:
        results = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.dURPMd div.MjjYud"))
        )
        print(f"{len(results)} organik sonuç bulundu.")

        for result in results:
            try:
                url_element = result.find_element(By.CSS_SELECTOR, 'a[jsname="UWckNb"]')
                url = url_element.get_attribute("href")

                if url:
                    organic_data.append({"url": url, "type": "Organic"})
                    print(f"Organik URL'si alındı: {url}")
                else:
                    print("Geçersiz URL, atlanıyor...")

            except NoSuchElementException:
                print("Organik sonucun içinde URL bulunamadı, atlanıyor...")

    except TimeoutException:
        print("Organik sonuçlar bulunamadı veya sayfa çok yavaş yüklendi!")

    return organic_data


def extract_seo_data(driver, ad):
    seo_data = {
        "URL": ad["url"],
        "PageTitle": "",
        "MetaDescription": "",
        "H1": "",
        "H2": "",
        "H3": "",
        "OpenGraphTitle": "",
        "OpenGraphDescription": "",
        "OpenGraphImage": "",
        "ImageAltTexts": [],
        "JSONLD": []
    }

    try:
        driver.get(ad["url"])
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        page_source = driver.page_source
        soup = BeautifulSoup(page_source, "html.parser")

        # Başlık, meta açıklama ve başlık etiketleri
        seo_data["PageTitle"] = driver.find_element(By.TAG_NAME, "title").get_attribute("textContent")
        seo_data["MetaDescription"] = soup.find("meta", {"name": "description"})["content"] if soup.find("meta", {"name": "description"}) else ""
        seo_data["H1"] = soup.find("h1").text if soup.find("h1") else ""
        seo_data["H2"] = soup.find("h2").text if soup.find("h2") else ""
        seo_data["H3"] = soup.find("h3").text if soup.find("h3") else ""

        # Open Graph verileri
        og_title = soup.find("meta", {"property": "og:title"})
        og_description = soup.find("meta", {"property": "og:description"})
        og_image = soup.find("meta", {"property": "og:image"})
        if og_title: seo_data["OpenGraphTitle"] = og_title["content"]
        if og_description: seo_data["OpenGraphDescription"] = og_description["content"]
        if og_image: seo_data["OpenGraphImage"] = og_image["content"]

        # Resimlerin alt metinleri
        images = soup.find_all("img")
        for img in images:
            alt_text = img.get("alt", "")
            if alt_text:
                seo_data["ImageAltTexts"].append(alt_text)

        # JSON-LD verisi (Schema.org)
        json_ld = soup.find("script", {"type": "application/ld+json"})
        if json_ld:
            try:
                seo_data["JSONLD"] = json.loads(json_ld.string)
            except json.JSONDecodeError:
                seo_data["JSONLD"] = {}

    except Exception as e:
        print("SEO verisi alınamadı:", e)

    return seo_data


def load_existing_data(keyword):
    try:
        with open(f"SEO_Analiz_{keyword}.json", 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
            return existing_data
    except FileNotFoundError:
        return []


def save_to_json(seo_list, keyword):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"SEO_Analiz_{keyword}.json"
    try:
        with open(file_name, 'w', encoding='utf-8') as f:
            json.dump(seo_list, f, ensure_ascii=False, indent=4)
        print(f"Veriler JSON dosyasına kaydedildi: {file_name}")
    except Exception as e:
        print(f"JSON dosyasına kaydederken hata oluştu: {e}")


def check_if_second_page(driver):
    url = driver.current_url
    if 'start=10' in url:
        print("İkinci sayfaya geçildi.")
        return True
    else:
        print("İkinci sayfaya geçilmedi.")
        return False


def main():
    keyword = input("Aramak istediğiniz kelimeyi girin: ")
    driver = setup_driver()

    try:
        # İlk sayfa için arama yapılır
        search_google(driver, keyword, page=0)

        # İlk sayfa reklamlarını ve organik sonuçlarını al
        ads = extract_ads(driver)
        organic_results = extract_organic_results(driver)

        all_data = []

        # Reklamlar ve organik sonuçlar için SEO verilerini al
        for ad in ads + organic_results:
            print(f"İşleniyor: {ad['url']}")
            seo_data = extract_seo_data(driver, ad)
            all_data.append(seo_data)
            time.sleep(2)  

        # Veriyi JSON dosyasına kaydet
        save_to_json(all_data, keyword)

        # İkinci sayfaya geçiş için URL'yi kullanarak arama yapılır
        search_google(driver, keyword, page=10)  # 10, ikinci sayfa için start parametresi

        # 2. sayfada reklamları ve organik sonuçları al
        if check_if_second_page(driver):
            ads = extract_ads(driver)
            organic_results = extract_organic_results(driver)

            for ad in ads + organic_results:
                print(f"İşleniyor: {ad['url']}")
                seo_data = extract_seo_data(driver, ad)
                all_data.append(seo_data)
                time.sleep(2)

            # Veriyi tekrar JSON dosyasına kaydet
            save_to_json(all_data, keyword)

        else:
            print("İkinci sayfada veri alınamadı.")

    finally:
        driver.quit()
        print("Tarayıcı kapatıldı.")


if __name__ == "__main__":
    main()
