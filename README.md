# Cadeaulijst

Kleine Flask-cadeaulijst: publieke weergave, beheer alleen na login. De standaardopslag is een lokaal CSV-bestand `presents.txt`; dat moet op een blijvend schrijfbare schijf staan. Niet rechtstreeks met deze opslag naar Vercel Functions deployen: daar is het bestandssysteem niet duurzaam schrijfbaar. Geen account-, reserverings- of multiuserfunctie aanwezig.

## Bestanden

```text
app.py
requirements.txt
.env                 # zelf maken, nooit committen
templates/base.html
templates/index.html
templates/admin.html
templates/login.html
static/css/style.css
static/js/app.js
presents.txt         # bestaand databestand behouden, niet overschrijven
```

## Installatie

1. Maak eerst een backup van je bestaande `presents.txt` buiten de repository. Het aangeleverde voorbeeld heet `presents-2.txt`, maar de app zoekt `presents.txt`. Hernoem alleen als je zeker weet dat dat jouw actuele databestand is.
2. Maak een virtual environment en installeer dependencies:

```bash
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

3. Genereer een nieuwe geheime sleutel:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

4. Maak een nieuw adminwachtwoord (gebruik niet het oude wachtwoord uit je eerdere broncode) en maak daarvan lokaal een hash:

```bash
python -c "from werkzeug.security import generate_password_hash; import getpass; print(generate_password_hash(getpass.getpass('Nieuw adminwachtwoord: ')))"
```

5. Zet de twee resultaten in environment variables. Een `.env`-bestand wordt door deze app **niet automatisch geladen**. Kopieer `.env.example` naar `.env`, vul de waarden in en laad het bestand met je eigen shell-/IDE-configuratie, of zet de waarden direct in je omgeving. Voor PowerShell:

```powershell
$env:SECRET_KEY = 'jouw-gegenereerde-secret'
$env:ADMIN_PASSWORD_HASH = 'jouw-gegenereerde-hash'
$env:COOKIE_SECURE = '0'
python app.py
```

Voor macOS/Linux:

```bash
export SECRET_KEY='jouw-gegenereerde-secret'
export ADMIN_PASSWORD_HASH='jouw-gegenereerde-hash'
export COOKIE_SECURE=0
python app.py
```

Open daarna `http://127.0.0.1:5000/`. Open `/login` voor beheer. Gebruik `COOKIE_SECURE=1` wanneer de app achter HTTPS draait. Bij lokaal HTTP moet dit `0` zijn.

## Wat is veranderd?

- De homepage is publiek, maar toevoegen, verwijderen en afvinken vereisen een adminsessie.
- Alle POST-formulieren, inclusief login en JavaScript-toggle, gebruiken een CSRF-token.
- Adminwachtwoord wordt als hash geverifieerd; secret en hash staan niet in de code.
- Onveilige bestaande productlinks worden niet als link getoond; nieuwe links moeten http(s) zijn.
- De UI is mobielvriendelijk en bevat zoeken en statusfilters.
- Het bestaande CSV-formaat `Name,Link,Bought` blijft behouden; de brondata worden niet automatisch gemigreerd.

## Belangrijke beperkingen

Dit is een geschikte eerste versie voor lokaal of kleinschalig privégebruik op een host met duurzame opslag, **geen** productie-securitygarantie. Nog toe te voegen voor een publiek bereikbare deployment: login-rate-limiting, tests, HTTPS, backup-/hersteltest, duurzaam opslagontwerp en controle op gelijktijdige schrijfacties. CSV + indexposities zijn kwetsbaar bij gelijktijdige updates of wanneer iemand tegelijk items verwijdert; later overstappen op een database met stabiele IDs. Gebruik deze app niet met huidige CSV-schrijfopslag op Vercel Functions.
