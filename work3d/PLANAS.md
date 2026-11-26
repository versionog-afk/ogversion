# /merch 3D puslapis: darbo fazės

Tikslas: `ogversion.com/merch` – interaktyvus 3D puslapis. Scenoje stovi 3D žmogaus figūra su tikroviškais juodais NA2 marškinėliais (priekyje „NA2“ iš banknotų, nugaroje Šilainių žemėlapis). Figūrą galima sukti pirštu, slenkant kamera priartėja prie spaudos, apeina figūrą iki nugaros, tamsoje lieka šviesti tik žemėlapis.

Kiekviena fazė baigiama rezultatu, kurį savininkas pamato ir patvirtina. Į `main` (gyvą svetainę) niekas nekeliama be atskiro savininko leidimo.

## 0 fazė. Perkėlimas į kompiuterį

- Saugykla nuklonuojama kompiuteryje, atsidaroma šaka `claude/friendly-cori-d4z8b5`.
- `work3d/` aplanke paleidžiama `npm install` (three.js, kūrimo ir testavimo įrankiai).
- Savininkas į `work3d/ref/` įkelia originalus: tris nuotraukas, maketo lapą ir vaizdo įrašą (į internetą jie nekeliami).
- Patikrinama, kas yra kompiuteryje: operacinė sistema, vaizdo plokštė ir jos atmintis, Blender versija, Node, Git, Python.

Baigta, kai: puslapis susirenka ir atsidaro kompiuteryje (`npm run build`, `npm run serve`), o modelio tikrintuvas (`npm run check-model`) parodo figūrą.

## 1 fazė. Įrankiai (skills)

- Iš GitHub parenkami ir įdiegiami: tiltas, per kurį Claude valdo Blender; žmogaus figūros generatorius Blender'iui; audinio ir drabužių įrankiai; three.js / 3D puslapio įgūdžiai.
- Prieš diegiant kiekvienas patikrinamas: licencija (ar galima naudoti komerciškai), ką jis paleidžia kompiuteryje, kur jungiasi internetu.
- Bandymas: Claude pats sukuria sceną Blender'yje, padaro vaizdą ir išeksportuoja GLB failą.

Baigta, kai: bandymas praeina ir įrankių sąrašas su licencijomis įrašytas į `work3d/THIRD-PARTY.md`.

## 2 fazė. Žmogeliukas

- Pagrindinis kelias: parametrinė žmogaus figūra Blender'yje (laisvos licencijos), proporcijos ir poza pagal vaizdo įrašą.
- Papildomas kelias, jei vaizdo plokštė leidžia: 3D modelis iš tikrų nuotraukų ar įrašo kadrų. Jis naudojamas kaip formos pavyzdys arba tiesiogiai – tik su modelio (žmogaus) sutikimu.
- Sprendimas, kaip figūra atrodo: skulptūra / manekenas ar tikroviška oda ir plaukai.

Baigta, kai: savininkas patvirtina figūrą iš apsukimo vaizdų.

## 3 fazė. Rūbai

- Marškinėlių iškarpos pagal tikrus matmenis (krūtinės plotis, ilgis, rankovė, apykaklė) ir audinio simuliacija ant figūros: sunki medvilnė, nuleisti pečiai, plačios rankovės.
- Detalės: apykaklės ribas, palankai, siūlės, audinio storis; kelnės ir batai.
- Audinio medžiaga ir raukšlių reljefas.

Baigta, kai: 3D vaizdas šalia tikros nuotraukos atrodo kaip tie patys marškinėliai.

## 4 fazė. Spaudos

- Geriausia – originalūs spaudos failai iš savininko. Jei jų nėra: „NA2“ iškerpama iš stambaus plano nuotraukos, žemėlapis perpiešiamas iš įrašo kadrų (pradėta, grubūs variantai jau yra `work3d/art/`).
- Spaudos uždedamos tikrose vietose ir tikro dydžio, seka audinio raukšles.

Baigta, kai: abi spaudos ryškios iš arti ir sutampa su tikrais marškinėliais.

## 5 fazė. Eksportas į internetą

- Modelis supaprastinamas telefonams, iškepamos tekstūros, eksportuojamas ir suspaudžiamas GLB (tikslas – iki 1,4 MB).
- Tikrinama pagal modelio sutartį (`work3d/spec/SPEC.md`) ir bendru tikrintuvu.

Baigta, kai: tikrintuvas nerodo įspėjimų, o modelis telpa į biudžetą.

## 6 fazė. 3D puslapis

- Jau padaryta: scena su „NA2“ už figūros, sukimas pirštu, kameros kelias aplink figūrą, tamsos scena su šviečiančiu žemėlapiu, atsarginis plokščias puslapis.
- Liko: įdėti galutinį modelį ir spaudas, stovas su devyniomis nuotraukomis ant raudono bėgio, automatinis kokybės mažinimas silpniems telefonams, atsigavimas po klaidų, ramus režimas.

Baigta, kai: visas scenarijus veikia nuo pradžios iki galo.

## 7 fazė. Tikrinimas

- Tikri telefonai (iPhone ir Android), greitis, pritaikymas neįgaliesiems, atsarginis režimas.
- Nepriklausoma peržiūra ir taisymų ratai.
- Tekstai ir teisiniai klausimai: banknotų atvaizdai, žemėlapio šaltinis, žmogaus nuotraukose sutikimas.

Baigta, kai: nėra žinomų rimtų klaidų.

## 8 fazė. Paleidimas

- Peržiūra laikinu adresu, savininko sutikimas, tada kėlimas į `main`.
- Su savininko leidimu iš šakos istorijos išvalomi seno produkto paveikslėliai.
- Nuimamas `noindex`, kai puslapis paruoštas rodyti viešai.
