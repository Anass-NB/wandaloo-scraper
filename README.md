# Wandaloo Car Scraper

A comprehensive Python scraper for extracting car models and their detailed specifications from [Wandaloo.com](https://www.wandaloo.com/neuf/maroc/0,0,0,0,0,0,-,az,1.html).

## 🎯 What it extracts

For each car model, the scraper extracts:

1. **Basic Information:**

   - Car name
   - Model variant (e.g., "1.0 TCe 100 Essentiel")
   - Price
   - Direct link to model page

2. **Detailed Specifications:**
   - Engine & Technical Info (motorization, power, transmission, etc.)
   - Consumption & Performance (fuel consumption, max speed, acceleration)
   - Dimensions & Volumes (category, weight, length, width, height)
   - Safety features (airbags, ABS, ESP, etc.)
   - Comfort features (air conditioning, audio system, etc.)
   - Aesthetic features (wheels, upholstery, lights, etc.)

## 🚀 Quick Start

### Usage

```bash
git clone https://github.com/Anass-NB/wandaloo-scraper.git
```

```bash
cd wandaloo-scraper
```

```bash
pip install requests beautifulsoup4 pandas lxml
```

```bash
python wandaloo_scraper.py
```

## 📁 Output Files

### CSV File

### Sample JSON Structure

```json
{
  "car_name": "Dacia Sandero Streetway",
  "model_variant": "1.0 TCe 100 Essentiel",
  "url": "https://www.wandaloo.com/neuf/dacia/sandero-streetway/fiche-technique/1-0-tce-100-essentiel/18709.html",
  "price_preview": "128.000DH",
  "name": "DACIA Sandero Streetway1.0 TCe 100 Essentiel neuve au Maroc - Fiche Technique",
  "model": "Mon comparatif",
  "prix": "128.000DH ** Prix public",
  "specifications": {
    "Moteur & Infos techniques": [
      "Motorisation1.0 TCe 100",
      "EnergieEssence",
      "Puissance fiscale7cv",
      "Transmission2 roues motrices ( 4x2 ou 2WD )",
      "Architecture3 cylindres en ligne",
      "Cylindrée999cm³",
      "Couple maxi.160Nm"
    ],
    "Conso. & performances": [
      "Conso. ville6,4l/100 km",
      "Conso. route4,9l/100 km",
      "Conso. mixte5,5l/100 km",
      "Emission CO2140g/km",
      "Vitesse maxi.165km/h",
      "Accélération 0-100 km/h14,2sec."
    ]
  }
}
```
