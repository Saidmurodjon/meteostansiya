# Meteostansiya — loyiha holati

> **Eslatma**: repo public. Haqiqiy IP, token va parollar bu faylda `<PLACEHOLDER>` ko'rinishida; qiymatlari gitignore qilingan `CLAUDE.local.md` (va skriptlar/compose uchun `v1-thingsboard/.env`, `v2-grafana/.env`) faylida.


_Oxirgi yangilanish: 2026-09-23 (Stansiya-1 SIM bilan dalada ishga tushirildi, vaqtinchalik Mac-ThingsBoard sxemasi orqali masofadan ulanish tekshirilmoqda — pastga, yangi bo'limga qarang)_

## Loyiha tuzilmasi: v1 va v2 — ikkita mustaqil tizim (2026-10-15)

Foydalanuvchi talabi: Grafana "test" emas, **v2 — ThingsBoard'dan mustaqil ishlaydigan alohida tizim**; v1 va v2 bir-biriga bog'liq bo'lmasligi, har birini alohida ishga tushirish mumkin bo'lishi kerak.

- **`v1-thingsboard/`** — DL1 → `bridge/dl1_bridge.py` → ThingsBoard. O'z `docker-compose.yml` (`thingsboard/tb-postgres:4.2.1.1` + bridge), `.env`/`.env.example`. `bridge/make_dashboard.py` dashboard'ni yaratadi/joyida yangilaydi. `legacy/` — eski ofis-server (`dl1_bridge_server.py`, IP→token xaritasi), noutbuk-relay (`dl1_bridge_local.py`) va `make_dashboard_office.py`.
- **`v2-grafana/`** — DL1 → `bridge/dl1_bridge.py` → VictoriaMetrics ← Grafana. O'z `docker-compose.yml` (VM `v1.102.1`, Grafana `11.2.0`, bridge `python:3.12-slim`), `.env`/`.env.example`, `grafana/provisioning` + `grafana/dashboards/meteo.json`. Volume nomlari qat'iy: `meteo-vm-data`, `meteo-grafana-data`.
- Ikkala bridge **kod almashmaydi** (parser ataylab har birida alohida nusxada — protokol o'zgarsa ikkalasini ham yangilash kerak). Ikkalasi ham manba IP'ga tayanmaydi (bitta standart device/station).
- **`tools/dl1_tee.py`** (ixtiyoriy) — DL1 faqat bitta IP:port'ga ulanadi; tee DL1 ulanishini qabul qilib, baytlarni bir nechta bridge'ga nusxalaydi. Target o'chiq bo'lsa o'tkazib yuboradi va keyingi chunk'da qayta ulanadi; Docker port-proksi orqasidagi konteyner restart bo'lganda ham buni (MSG_PEEK EOF tekshiruvi bilan) sezadi. Tee restart qilinsa DL1 qayta ulanadi; bridge'lar restart qilinsa — yo'q (tee DL1 ulanishini ushlab turadi).

**Mac'dagi joriy ish holati:**
```
DL1 → ngrok → :8888 tools/dl1_tee.py ─┬→ :8801 v1 bridge (python3 v1-thingsboard/bridge/dl1_bridge.py, log /tmp/dl1_bridge_v1.log) → ThingsBoard (meteo-thingsboard konteyner, :9090)
                                      └→ :8802 v2 bridge (meteo-v2-bridge konteyner, `docker logs`) → meteo-vm (:8428) ← meteo-grafana (:3001)
```
- v2: `cd v2-grafana && docker compose up -d`. v1 ThingsBoard hali eski qo'lda yaratilgan `meteo-thingsboard` konteynerida (compose'ga ko'chirilmagan — volume `mysqlteo-tb-data`); v1 bridge Mac'da oddiy fon jarayoni.
- Tee: `python3 tools/dl1_tee.py --listen 8888 --to 127.0.0.1:8801 --to 127.0.0.1:8802`, log `/tmp/dl1_tee.log`.
- Eski `bridge/log_to_vm.py` (v2'ni v1 logiga bog'lab qo'ygan) olib tashlandi.

## ⚠️ KUTILAYOTGAN QAROR: production'ga chiqish (hali BOSHLANMAGAN)

2026-09-13'da muhokama qilindi: hozirgi ofis server **vaqtincha o'chirilgan** holatda. Production'ga chiqish uchun joriy sxemani (ofisdagi jismoniy server + Tailscale + `sslh` port-hiylasi) arzon **cloud VPS**ga (masalan Hetzner, DigitalOcean yoki mahalliy provayder — `eskiz.uz` bu emas, u SMS-shlyuz xizmati) ko'chirish taklif qilindi:

- **Sabab**: joriy muammolarning ko'pi (UzTelecom faqat 80/443'ni ochiq qoldirishi → `sslh` kerak bo'lgani, server ofis elektr/tarmog'iga bog'liqligi, DHCP IP o'zgarib ketishi — "Infratuzilma holati" item 4-5-6'ga qarang) server ofisda jismoniy turgani sabab. Cloud VPS'da DL1 serverga **chiquvchi** ulanish qilgani uchun barcha portlar ochiq bo'ladi, sslh keraksiz bo'lib qoladi, server doim onlayn turadi.
- **Trade-off**: ko'chirish (ThingsBoard DB volume export/import, Coolify qayta o'rnatish, `dl1-bridge` qayta sozlash) vaqt talab qiladi, oylik xarajat qo'shiladi.

**MUHIM**: foydalanuvchi aniq aytdi — **"productionga chiqaramiz, buyrug'imni kut!"** — ya'ni bu migratsiya ishi (VPS sotib olish, ko'chirish) foydalanuvchining alohida, aniq buyrug'isiz **boshlanmasligi kerak**. Hozircha faqat hujjatlashtirilgan reja, harakat yo'q.

## 2026-09-23: Stansiya-1 dalaga o'rnatildi (SIM), ofis server o'chiq — vaqtinchalik Mac-ThingsBoard sxemasi

Bugun Stansiya-1 (test punkti emas, alohida jismoniy stansiya) **tashqariga o'rnatildi** va unga SIM joylandi (dastlab Uzmobile deb yozilgan, 2026-10-14 holatida — foydalanuvchining shaxsiy **Beeline** SIM'i) — DL1'ning o'zida signal "good", operator aniqlangan holatda ko'rinadi. Maqsad: shu stansiyadan ThingsBoard'ga masofadan (SIM/mobil tarmoq orqali) ma'lumot kelishi mumkinligini tasdiqlash, keyin esa doimiy hosting (VPS) sotib olib production sxemasini shu asosda qurish (yuqoridagi "KUTILAYOTGAN QAROR" bo'limi hali kuchda — bu ish o'sha migratsiyaning o'zi emas, faqat undan oldingi tekshiruv bosqichi).

**Muammo**: shu tekshiruvni boshlashda ma'lum bo'ldi — ofisdagi asosiy server (`iep-server`, `<TAILSCALE_IP>`) Tailscale bo'yicha **12 kundan beri offline** ekan (bu "KUTILAYOTGAN QAROR" bo'limida aytilgan "vaqtincha o'chirilgan" holatning o'zi). Demak DL1 SIM orqali `<PUBLIC_IP>:443`ga (sslh) ulansa ham, orqada hech narsa yo'q — ThingsBoard va `dl1-bridge` javob bermaydi.

**Vaqtinchalik yechim (foydalanuvchi buyrug'i bilan)**: ofis serverini yoqish o'rniga, **shu Mac (noutbuk)ning o'zi vaqtincha "server" sifatida** ishlatildi:

1. **Docker Desktop** ishga tushirildi, **ThingsBoard** (`thingsboard/tb-postgres` image, demo tenant bilan) lokal konteynerda ko'tarildi: konteyner nomi `meteo-thingsboard`, port `9090`, volume `mysqlteo-tb-data`. Bu — office serverdagi ThingsBoard'dan **butunlay alohida, yangi** instans (device/dashboard tarixi umumiy emas).
   - Tenant login: `<TB_USERNAME>` / `<TB_PASSWORD>` (demo standart, xuddi office serverdagidek — bu ham ishlab chiqarishga chiqishdan oldin almashtirilishi kerak).
   - Yangi device yaratildi: **Meteostansiya-1** (id `e595c5f0-b70a-11f1-8df9-f17783d629e6`), access token: `<TB_TOKEN_MAC>`.
2. Yangi bridge skripti yozildi: **`meteostansiya/bridge/dl1_bridge_mac.py`** (2026-10-15'dan: `v1-thingsboard/bridge/dl1_bridge.py`) — `dl1_bridge_server.py`ning aynan shu parserini (yomg'ir uchun to'g'ri `data[37]` offseti bilan) ishlatadi, lekin `localhost:9090`ga (shu Mac'dagi ThingsBoard'ga) push qiladi va IP bo'yicha filtrlamasdan **har qanday kelgan ulanishni** `Meteostansiya-1` tokeniga yo'naltiradi (hozircha faqat bitta stansiya ulangani uchun). Fon jarayonida ishlab turibdi (8888-portda tinglaydi), log: `/tmp/dl1_bridge_mac.log`.
3. **Tashqariga chiqarish muammosi**: bu Mac uyda/mobil tarmoqda NAT orqasida — DL1 SIM orqali unga to'g'ridan-to'g'ri ulana olmaydi, portni tashqariga chiqarish (tunnel) kerak bo'ldi:
   - **ngrok** — TCP tunnel uchun bepul tarifda ham **karta tasdiqlash** talab qilinishi aniqlandi (`ERR_NGROK_8013`, rasman hujjatlashtirilgan — "This card will NOT be charged", texnik xato emas, ularning siyosati; faqat HTTP tunnellarga tegishli emas, aynan TCP'ga tegishli).
   - **jprq** (ngrok'ga o'xshash, kartasiz muqobil deb sinaldi) — uning TCP tunnel xizmati (`tcp.jprq.io`) DNS darajasida umuman topilmadi (`NXDOMAIN`), ya'ni bu loyiha (2021'dan beri yangilanmagan) **o'lik/tashlab qo'yilgan** ekan. (Eslatma: global `pip install jprq` boshqa loyiha — `aider-chat` — kerak qiladigan `aiohttp`/`click`/`rich`/`certifi` versiyalarini pastga tushirib yuborgan edi, darhol tuzatildi va jprq alohida virtualenv'ga o'tkazildi, global muhitga zarar qolmadi.)
   - **serveo.net** (SSH reverse-tunnel, `ssh -R 0:localhost:8888 serveo.net`) — kartasiz ishlaydi, lekin ro'yxatdan o'tilmagan holatda atigi **10 daqiqa** (yoki 2 daqiqa trafiksiz tursa undan oldin) amal qiladi. GitHub orqali bepul akkaunt ochilib, maxsus kalit (`~/.ssh/serveo_key`, faqat shu maqsad uchun — server SSH kalitidan alohida) `console.serveo.net`da ro'yxatdan o'tkazildi — bu muddatni **30 daqiqagacha** uzaytirdi, lekin baribir cheklangan.
   - **Yakuniy yechim**: foydalanuvchi ngrok'ga karta qo'shishga rozi bo'ldi (haqiqatan pul yechilmadi) — shundan keyin **ngrok TCP tunnel muvaffaqiyatli ishga tushdi, vaqt chegarasisiz**. Joriy manzil: `<OLD_NGROK_HOST>:<OLD_NGROK_PORT>` (bir nechta IP'ga round-robin qiladi, ulardan biri: `<OLD_NGROK_IP>:<OLD_NGROK_PORT>` — DL1 IP-manzil kiritishni talab qilgani uchun domin emas, aynan shu IP ishlatildi). ⚠️ **Bu manzil doimiy emas** — agar ngrok jarayoni biror sababdan qayta ishga tushsa (Mac o'chsa/qayta yoqilsa, jarayon qulasa), **yangi host:port tayinlanadi** (bepul tarifda "reserved TCP address" yo'q) — DL1'ning `8.Set → a.Wireless IP`sini qayta yozish kerak bo'ladi.
   - **2026-10-14 yangilanish**: Mac qayta yuklangani sabab zanjir (TB konteyner, bridge, ngrok) to'xtab qolgan edi — DL1 esa baribir `Server: Normal` ko'rsatib turgan (bu faqat TCP ulanish ochilganini bildiradi, ma'lumot bizga yetganini emas). Qayta ishga tushirildi: ngrok binari `~/Downloads/ngrok` (PATH'da emas), log `/tmp/ngrok.log`. **Yangi manzil: `<NGROK_HOST>:<NGROK_PORT>`** → DL1 uchun IP `<NGROK_IP>`, port `<NGROK_PORT>` (tunnel shu IP orqali tekshirildi).
4. DL1'ning `8.Set → a.Wireless IP` maydoniga yuqoridagi ngrok IP:port kiritildi (foydalanuvchi tomonidan, dalada, qo'lda). **Bu sessiya oxirigacha DL1'dan haqiqiy ulanish loglarda hali ko'rinmagan edi** — keyingi sessiyada birinchi navbatda `/tmp/dl1_bridge_mac.log` va ngrok inspector (`curl localhost:4040/api/tunnels`)ni tekshirish kerak.

**2026-10-14: SIM orqali birinchi muvaffaqiyatli ulanish.** DL1'ga ngrok `<NGROK_IP>:<NGROK_PORT>` kiritilgach, 17:35'da Unitel (Beeline) tarmog'idan (`95.214.21x.x`) ulanish keldi, bridge freymlarni to'g'ri dekodlab ThingsBoard'ga yubordi. Eslatmalar:
- SIM — **Uzmobile emas, foydalanuvchining shaxsiy Beeline SIM'i** (vaqtinchalik). Doimiy ish uchun stansiyaga alohida SIM kerak.
- Ulangan zahoti DL1 ~200 ta **eski bufer freymini** sekundiga ~1 tadan ketma-ket yubordi (ichki vaqti 30s qadam bilan) — ya'ni Wireless kanalda bufer yuborilishi kuzatildi (09-07'dagi Ethernet "backfill yo'q" xulosasiga zid, sababi aniqlanmagan). Bridge kelgan vaqtni timestamp qilgani uchun bu eski qiymatlar ThingsBoard'da 17:35–17:41 oralig'iga siqilib, noto'g'ri vaqt bilan saqlangan. Shundan keyin foydalanuvchi DL1 xotirasini USB'ga export qilib, o'chirdi.
- 17:41'dan jonli freymlar har 30s keladi. Hozir DL1'ga **faqat shamol tezligi sensori** ulangan — boshqa maydonlar 0 keladi, shamol tezligi qo'lda aylantirilganda o'zgarishi tasdiqlandi (1.12 m/s).

**2026-10-14/15 kuzatuvlar:**
- Bridge (`dl1_bridge_mac.py`) endi freym uzunligini sarlavhadan (`data[2:4]`+2) oladi, `40 01` bilan boshlanmagan baytlarni tashlab "resync" qiladi va har freymning xom hex'ini logga yozadi. 19:47'da DL1 TCP oqimiga **Quectel AT buyruqlarini** (`AT+QISEND=0,46\r\n`, 43 bayt) aralashtirib yubordi — DL1 firmware/modem xatosi; resync buni muammosiz o'tkazib yubordi.
- **`data[38:40]` (uint16 BE) ÷ 100 = asosiy 12V batareya kuchlanishi (V) — yuqori ehtimol bilan tasdiqlangan (2026-10-15)**: 10-14 kechqurun ~11.0 V edi; 10-15 ertalab foydalanuvchi o'tirib qolgan asosiy 12V batareyani yangisiga almashtirgach, qiymat birdan ~12.05–12.17 V ga sakradi. 2026-10-15 08:35'dan bridge uni `battery_voltage` sifatida ThingsBoard'ga va (log_to_vm.py orqali) VictoriaMetrics'ga yozadi; ikkala dashboard'da "Batareya kuchlanishi" grafigi bor (`make_dashboard_mac.py` endi mavjud dashboard'ni joyida yangilaydi). Logdagi xom freymlardan tarix ham yuklangan: eski batareya 10-14 17:49'da 11.2 V → 22:01'da **10.15 V** gacha tushgan (DL1 shu payt ulanishni yo'qotgan). Ehtimol, DL1'ning "osilib qolishi"/qayta ulanmasligi va `AT+QISEND` oqib chiqishi past kuchlanish bilan bog'liq bo'lgan — yangi batareya bilan kuzatish kerak. `data[26]` ham `01` — shamol tezligi uint16 `data[26:28]` bo'lishi mumkin (2.08 vs 4.64 m/s), DL1 ekrani bilan tasdiqlanmagan.
- Mac kechasi baribir uxladi (`caffeinate -is` faqat zaryadkada ishlaydi; qopqoq yopilsa/batareyada uxlaydi) — 23:26–07:57 ngrok uzilgan. DL1'dan oxirgi ulanish 22:01–22:18; ngrok 07:57'da o'sha manzil bilan tiklangan bo'lsa ham DL1 qayta ulanmadi.
- (Tarix — 2026-10-15'da v2 sifatida mustaqil tizimga aylantirildi, yuqoridagi "Loyiha tuzilmasi" bo'limiga qarang.) Sinov uchun Grafana + VictoriaMetrics ko'tarildi: konteynerlar `meteo-vm` (127.0.0.1:8428, volume `meteo-vm-data`, retention 5y) va `meteo-grafana` (http://127.0.0.1:3001, admin / `<GRAFANA_PASSWORD>`), tarmoq `meteo-net`; provisioning `grafana-test/`. `bridge/log_to_vm.py` bridge logini o'qib VM'ga yozadi (bridge'ni restart qilmaslik uchun), log `/tmp/log_to_vm.log`.

**Yon ish — eski USB eksport tahlili**: shu jarayon davomida foydalanuvchi DL1'ning ichki xotirasidan eski USB eksport faylini (`/Volumes/NO NAME/Data20180725093442.csv`, 8549 qator) taqdim etdi, undan interaktiv HTML dashboard (Artifact) qurib berildi. Muhim kashfiyot: faylning faqat dastlabki **107 qatori** (2025-08-18 – 2025-08-20) ishonchli sanaga ega — 109-qatordan boshlab DL1'ning ichki soati **"2018-07-25"ga** (yoki buzilgan "20@5-10-00"/"20@5-10-01" ko'rinishlarga) qulflanib qolgan, ya'ni RTC muammosi avvalgi hujjatlashtirilgan "daqiqa/soniya ~12 daq farq" muammosidan ancha jiddiyroq ekan — **sana maydoni butunlay ishonchsiz** bo'lishi mumkin, faqat vaqt (soat:daqiqa:soniya) taxminan izchil ko'rinadi. Bu holat hali sabab-oqibat jihatidan tekshirilmagan (RTC batareyasi tugaganmi yoki boshqa sabab bormi — aniqlanmagan).

**Muhim eslatma keyingi sessiya uchun**: bu butun Mac-ThingsBoard-ngrok zanjiri **faqat vaqtinchalik tekshiruv** uchun — production emas. Mac o'chirilsa yoki uxlab qolsa (`sleep`), butun zanjir to'xtaydi. Doimiy VPS/hosting sotib olingandan keyin bu vaqtinchalik sxema butunlay bekor qilinadi va yuqoridagi "KUTILAYOTGAN QAROR" bo'limidagi asl rejaga (ofis server yoki VPS + statik IP, tunnel'siz) qaytiladi.

## Server kirish

Bu loyiha uchun mo'ljallangan server: Ubuntu + Coolify, Tailscale orqali kirish.

- Tailscale IP: `<TAILSCALE_IP>`
- Tashqi (public) IP: `<PUBLIC_IP>` (UzTelecom, faqat 80/443 tashqaridan ochiq — pastga qarang)
- SSH user: `iep-server`
- SSH kalit: `~/.ssh/iep_server`
- Ulanish: `ssh -i ~/.ssh/iep_server iep-server@<TAILSCALE_IP>`

Eslatma:
- Ulanish uchun bu Mac'da Tailscale ishlab turishi kerak.
- `iep-server` foydalanuvchisi `docker` guruhida — `docker ps`/`docker logs`/`docker cp` `sudo`siz ishlaydi. `sudo`ning o'zi interaktiv TTY+parol talab qiladi, SSH orqali skript ichida ishlamaydi.
- Bu server allaqachon boshqa loyihalarni ham (masalan `media-downloader-bot`, Coolify, ThingsBoard) hosting qiladi — resurslarni tekshirishda buni hisobga olish kerak.
- Server uskunasi: **Fujitsu PRIMERGY TX1320 M4**, Xeon E-2136 (6 yadro/12 thread), 7GB RAM, 1.8TB HDD (WD Purple, ikkinchi 3.5" bay bo'sh). Ofis LAN'idagi IP (`eno1`, MAC `4c:52:62:2b:f7:44`) endi **statik `192.168.1.44/24`** (2026-09-04'dan, `/etc/netplan/00-installer-config.yaml` orqali sozlangan) — avval DHCP edi, shuning uchun reboot'da o'zgarib ketardi (pastga, incident #5'ga qarang).

## Loyiha maqsadi

5 ta mobil meteostansiya (meteo o'lchov punktlari) bor. Har biri SIM (mobil aloqa), Ethernet yoki LoRa (radio chastota) orqali bog'lanadi va ma'lumot uzatadi. Rasm/tasvir uzatish **kerak emas** (stansiya suratlari faqat referens uchun `Rasmlar/` papkasiga qo'lda yuklangan). Maqsad — stansiyalardan kelayotgan sensor ma'lumotlarini serverga uzatib, ThingsBoard'da qabul qilish, saqlash va monitoring qilish.

## Hardware (test stansiyasi, ofisda)

Quyosh panelli avtomatik meteostansiya, quyidagi sensorlar bilan (har birining RS485 manzili bor):
- **Addr 0001** — kombinatsiyalangan T/RH/Light sensor (harorat, namlik, yorug'lik — bitta korpusda)
- **Addr 0002** — Wind Speed (anemometr)
- **Addr 0003** — Wind Direction (shamol yo'nalishi flyugeri)
- **Addr 0004** — Rainfall (yomg'ir o'lchagich)

Markaziy blok: **"Intelligent Data Logger · DL1"** (plata: `LS-DL1-V1.21`, 2021.07.23; Software V3.6, Hardware V1.0, ID 64010044). Ichida:
- Cellular modul: **Quectel EC200S** (SIM slot, GPRS/4G)
- LoRa modul: **Ebyte E22-400T22S** (SX1268, 400MHz, 22dBm)
- Ethernet: standart RJ45 (HanRun HR911105A)
- RS485 klemma (A/B) + quyosh kontrolleri (PWM, 12/24V 10A) orqali quvvatlanadi
- Ma'lumotni ichida buferlaydi (aloqa uzilsa sensor o'qishlarining o'zi DL1 xotirasida yo'qolmaydi — "Export data" orqali USB'ga chiqarish mumkin). **Lekin 2026-09-07'dagi 3 marta real uzilishda tasdiqlandi: bu bufer TCP orqali avtomatik "backfill" qilinmaydi** — ulanish tiklanganda DL1 faqat o'sha paytdagi jonli o'qishni yuboradi, uzilish davridagi ma'lumot ThingsBoard bazasiga hech qachon tushmaydi (grafikda bo'shliq qoladi). Uni tiklash uchun hozircha faqat qo'lda USB export + alohida import kerak bo'ladi (bunday avtomatik import quvuri hali yo'q).

DL1 menyusi: `8.Set` → **a.Wireless IP** (SIM) / **b.LAN IP** (Ethernet) / **c.Data Router** (4G/LAN/RS232 kanallarini yoqish-o'chirish) / **d.LoRa**. Har birida server IP:Port maydoni bor. Muhim: faqat IP/Port kiritish yetarli emas — `c.Data Router`da tegishli kanal (masalan `LAN:YES`) ham yoqilgan bo'lishi kerak.

## DL1 protokoli (reverse-engineering orqali aniqlangan)

DL1 serverga har `Collect Time` intervalida (test uchun 30s qilib qo'yilgan, default 30min) TCP orqali **46 baytli** binary freym yuboradi:

```
40 01 00 2c c8 05 | 12 07 19 09 | MM SS | 00 18 01 | TT TT | HH HH | 00 LL | 02 0b 00 00 | WS | 03 0c | DD DD | 04 13 | 00×7 | CRC(4 bayt)
```

Tasdiqlangan maydonlar (0-indexdan, Python `struct` bilan):
- `data[10]` = daqiqa, `data[11]` = soniya (DL1'ning ichki soati — real vaqtdan ~12 daq farq qiladi, sinxronlanmagan)
- `data[17:19]` (uint16 BE) = **Harorat × 10** (°C) — 100% tasdiqlangan
- `data[19:21]` (uint16 BE) = **Namlik × 10** (%RH) — 100% tasdiqlangan
- `data[22]` (1 bayt) = **Yorug'lik ÷ 10** (Lux) — 100% tasdiqlangan
- `data[27]` (1 bayt) = **Shamol tezligi × 100** (m/s) — yuqori ehtimol (aniq mos, lekin shamol o'zgaruvchan bo'lgani uchun screen bilan solishtirish ±0.5 farq berishi mumkin)
- `data[31:33]` (uint16 BE) = **Shamol yo'nalishi** (gradus, xom qiymat) — 100% tasdiqlangan
- `data[37]` (1 bayt, ÷ 10, mm) — **2026-09-07'da qo'lda tirqillatib tasdiqlangan** (eski taxmin `data[38:40]` noto'g'ri edi — u doim `0x0000`). Test paytida qiymat `10 → 10 → 4 → 0` bo'lib ~2 daqiqada nolga tushdi (qo'lda tez-tez bosishdan keyin mexanik "bounce" bosilgani asosida) — bu **umumiy yig'indi emas, balki qisqa muddatli tip-count/intensity ko'rsatkichi** bo'lishi mumkin degan taxminni beradi. Aniq birlik/masshtab (÷10 mm to'g'rimi) va xulq-atvor (haqiqiy uzoq davomli yomg'irda ham nolga tushib turadimi yoki yig'iladimi) hali **haqiqiy yomg'ir bilan tasdiqlanishi kerak**.
- Oxirgi 4 bayt = checksum/CRC (formula aniqlanmagan, hozircha tekshirilmayapti)

To'liq parser: `dl1_bridge.py` (pastga qarang).

## Infratuzilma holati va tuzatilgan xatolar

1. **ThingsBoard port xatosi (tuzatildi)** — Coolify compose'da `9090:8080` yozilgan edi, lekin `thingsboard/tb-postgres` image ichida haqiqatda **9090**-portda ishlaydi (8080 emas). `9090:9090` qilib tuzatildi.
2. **Ma'lumotlar bazasi volume yo'qligi (tuzatildi)** — compose'da `/data` uchun nomlangan volume yo'q edi, har redeploy'da butun DB (barcha device/dashboard) o'chib ketardi. Endi compose'ga qo'shilgan:
   ```yaml
   volumes:
     - tb-data:/data
   volumes:
     tb-data:
   ```
   Natijada volume nomi: `pzvns7fnnnwjfhdhiy2ejrii_tb-data`. **Diqqat**: bu volume qo'shilgandan keyingi DB holati — joriy holat, undan oldingi barcha device/dashboard (bir necha marta) qayta yaratilgan.
3. **Standart parol muammosi (hali tuzatilmagan)** — ThingsBoard tenant admin login: `<TB_USERNAME>` / `<TB_PASSWORD>` (demo standart parol). **Buni albatta o'zgartirish kerak**, ishlab chiqarishga chiqishdan oldin.
4. **Tashqi port muammosi (2026-09-04'da sslh bilan aylanib o'tildi — pastga, item 6'ga qarang)** — UzTelecom firewall'i faqat **80 va 443**ni tashqi internetdan ochiq qoldiradi (tekshirilgan: 8888, 1883, 9090 — hammasi tashqaridan timeout beradi). Server routeri (VORTEX CPE) o'zida port-forwarding funksiyasi yo'q — bu ISP darajasida boshqariladi. UzTelecom'ga alohida port ochish so'rovi yuborish o'rniga, allaqachon ochiq bo'lgan 443-portning o'zida `sslh` protokol-multiplekser orqali DL1 trafigini ham qabul qilish yo'li tanlandi (item 6).
5. **DHCP IP o'zgarishi sabab DL1 uzilib qolgani (tuzatildi, 2026-09-04)** — 2026-09-03 kuni kechqurun (~20:05 UTC) serverda reboot bo'lgan (sabab noaniq, ehtimol ofis elektr uzilishi — shu payt server ham, ehtimol butun ofis tarmog'i ham qayta ko'tarilgan). Reboot'dan keyin server DHCP orqali `eno1`ga **yangi IP (`192.168.1.2`)** olgan, lekin eski `192.168.1.44` DL1'ning `8.Set → b.LAN IP`sida yozilgan holicha qolgan — natijada DL1 "server"ga ma'lumot yuborsa ham, u endi mavjud bo'lmagan/boshqa manzilga ketgan va **~7 soat davomida hech qanday ma'lumot ThingsBoard'ga yetib bormagan** (`dl1-bridge` konteyner o'zi sog'lom edi, faqat DL1'dan ulanish kelmagan). Tashxis: DL1 ping'ga javob berardi, lekin `ss -tn`da 8888-portga bitta ham ulanish urinishi yo'q edi; `nc -zv 192.168.1.44 22` serverning o'z-o'ziga ham "No route to host" berdi — bu server LAN IP'sini yo'qotganini ko'rsatdi. **Yechim**: `eno1`ga statik IP (`192.168.1.44/24`) netplan orqali o'rnatildi (`sudo netplan try` bilan xavfsiz qo'llandi) — endi bu IP hech qachon o'zgarmaydi, DL1 sozlamasini qayta o'zgartirish shart emas. **Saboq**: kelgusida shunga o'xshash "ma'lumot kelmayapti" muammosida birinchi navbatda `ip -4 addr show eno1`ni tekshirish kerak — server IP DL1'da yozilgan manzil bilan mos kelishini tasdiqlash uchun.
6. **sslh port-multiplekser o'rnatildi — SIM uchun UzTelecom'ga murojaat shart emas (2026-09-04)** — DL1 SIM orqali ulanganda mobil operator tarmog'i orqali chiqadi, UzTelecom esa faqat 80/443ni tashqaridan ochiq qoldiradi (item 4). Alohida port (8888) ochishni so'rash o'rniga, serverda **`sslh`** (paket, apt orqali o'rnatilgan) 443-portning o'zida ikki turdagi trafikni ajratadi: TLS/HTTPS so'rovlarini Traefik'ga (`127.0.0.1:8443`), TLS bo'lmagan xom baytli trafikni (DL1'ning binary freymlari) esa `dl1-bridge`ga (`127.0.0.1:8888`) yo'naltiradi.
   - Traefik'ning (`coolify-proxy`) compose fayli (`/data/coolify/proxy/docker-compose.yml`) tahrirlandi: `443:443` → `127.0.0.1:8443:443` (host 443'ni sslh uchun bo'shatish). Zaxira nusxa: `docker-compose.yml.bak-20260904035246` (o'sha papkada).
   - sslh sozlamasi: `/etc/default/sslh` → `DAEMON_OPTS="--user sslh --listen 0.0.0.0:443 --tls 127.0.0.1:8443 --anyprot 127.0.0.1:8888"`, `systemctl enable --now sslh` bilan ishga tushirilgan (doimiy, boot'da avtomatik ko'tariladi).
   - Tekshirildi: sslh loglarida (`journalctl -u sslh`) xom bayt oqimi to'g'ri `127.0.0.1:8888`ga yo'nalgani ko'rindi; `downloader.saidmurod.com` (boshqa loyiha, xuddi shu Traefik orqali) tashqaridan hali ham muammosiz ishlayapti — production'ga hech qanday zarar yetmadi.
   - **Natija**: endi DL1'ning `8.Set → a.Wireless IP` (SIM) maydoniga `<PUBLIC_IP>:8888` emas, **`<PUBLIC_IP>:443`** yozish kerak — sslh avtomatik DL1 trafigini `dl1-bridge`ga uzatadi. Hali sinovdan o'tkazilmagan (SIM ertaga keladi).
   - Yon effekt (zararsiz): o'rnatish paytida serverda avvaldan yarim-o'rnatilgan **apache2** paketi ham konfiguratsiya qilinib, `systemd`ga yoqilib qoldi. Portlar band bo'lgani uchun ishga tushmayapti (`systemctl status apache2` → failed), lekin hali `enabled` holatda — xohlasa keyinroq `systemctl disable --now apache2 && systemctl mask apache2` bilan tozalash mumkin (bu ish keyinga qoldirildi).
7. **DL1 takroriy "osilib qolishi" (2026-09-07, qisman tuzatildi, ochiq muammo qoldi)** — yomg'ir sensorini qo'lda tekshirish paytida (yuqoridagi DL1 protokoli bo'limiga qarang) DL1 bir necha marta ma'lumot yuborishni to'xtatib qo'ydi:
   - **1-sabab (tuzatildi)**: `dl1_bridge.py`da `conn.settimeout(60)` bor edi — DL1 60 soniyadan ko'proq jim tursa, bridge ulanishni **jimgina** (log yozmasdan) yopib yuborardi, DL1 esa buni tez sezib qayta ulanmasdi (bir marta ~13 daqiqa, oxirida qo'lda o'chirib-yoqishga to'g'ri keldi). Tuzatildi: timeout 600s'ga oshirildi, va yopilganda endi log yoziladi (`"{ip}: idle timeout, closing connection"`).
   - **2-sabab (hali tuzatilmagan, DL1 tomonida)**: bundan tashqari, TCP-ulanish **ochiq (`ESTAB`) holatda turib**, DL1 baribir ma'lumot yuborishni to'xtatib qo'ygan holat ham kuzatildi (bridge tomonidan hech qanday xatolik yo'q, shunchaki DL1 jim). RS485 kabellari tekshirildi — **hammasi mahkam, kabel muammosi emas**. Faqat DL1'ni qo'lda (yoki to'liq sovuq) o'chirib-yoqish vaqtincha yordam berdi (sovuq reboot ~6 daqiqagacha, tezkor restart ~1-4 daqiqagacha barqaror ishlatdi, keyin yana qaytardi).
   - **Asl sabab topildi (2026-09-07, tahlil qilindi)**: `dl1-bridge` konteyner ushbu voqealargacha **3 kun davomida bir marta ham qayta ishga tushirilmagan edi** va DL1 shu 3 kun uzluksiz, bo'shliqsiz ishlagan (loglar 09-05, 09-06 kunlari tasdiqlaydi). Bugun yomg'ir baytini tuzatish jarayonida men konteynerni ketma-ket ikki marta qayta ishga tushirdim (debug-log qo'shish uchun soat 09:42'da, tuzatishni joylashtirish uchun 09:46'da) — **aynan shundan keyin** birinchi uzilish paydo bo'ldi. Yomg'ir tuzatishining o'zi (`data[38:40]` → `data[37]`, faqat bitta bayt offseti) ulanish/tarmoq mantig'iga umuman tegmaydi, demak sabab kod xatosi emas. Ehtimoliy mexanizm: **DL1 uzoq vaqt ochiq turgan bitta ulanishda juda barqaror ishlaydi, lekin har safar yangi ulanish ochishga majbur bo'lganda (masalan bridge restart qilinganda), uning firmware'ida yangi ulanishlarni bir necha daqiqadan keyin "osilib qoldiradigan" nozik xato bor** — bu odatda kamdan-kam namoyon bo'ladi, chunki server odatda qayta ishga tushirilmaydi. Bugungi bir necha marta ketma-ket restart/qayta ulanish shu nozik xatoni ochib tashladi.
   - **Umumiy tavsiya**: (1) bridge konteynerini keraksiz qayta ishga tushirmaslik — har bir restart DL1'ni yangidan ulanishga majbur qiladi va yuqoridagi xatoni qo'zg'atish xavfini oshiradi; (2) agar grafik to'xtab qolsa, avval `ss -tn | grep 192.168.1.50` bilan ulanish holatini tekshiring (yopiqmi yoki "ESTAB" holida osilib qolganmi), keyin `docker logs dl1-bridge --tail 20`; (3) DL1 qayta ulangandan keyin uni tinch qo'yish (soatlab tegmasdan kuzatish) — bu 3 kunlik barqaror ishlashni tiklashi mumkin.

## MUHIM KASHFIYOT: server ofis bilan bir lokal tarmoqda

`iep-server` nafaqat Tailscale (`<TAILSCALE_IP>`) orqali, balki **ofisning o'zidagi lokal tarmoqda ham** mavjud ekan: **`192.168.1.44`** (xuddi shu Vortex router ostida, DL1 va bu noutbuk bilan bir subnetda). Bu tasdiqlangan (`ssh iep-server@192.168.1.44` → hostname `iep-server`, bir xil server).

Bu degani: **hozirgi Ethernet testi uchun UzTelecom port ochishini kutish shart emas edi** — DL1'ni to'g'ridan-to'g'ri `192.168.1.44:8888`ga ulash kifoya qildi. ⚠️ Bu faqat lokal (ofis) tarmoqqa tegishli — **ertaga SIM kelganda bu yordam bermaydi**, chunki mobil operator tarmog'i bu lokal Vortex tarmog'idan butunlay mustaqil; SIM uchun baribir UzTelecom'dan tashqi port (8888) ochilishi kerak bo'ladi.

## Joriy ishlaydigan sxema (2026-09-03, yangilangan — to'g'ridan-to'g'ri, ishlaydi)

```
DL1 (ofis, Ethernet, LAN IP Set = 192.168.1.44:8888) → iep-server (lokal tarmoq orqali, dl1-bridge konteyner) → ThingsBoard (localhost:9090, bir hostda)
```

**Noutbuk endi umuman kerak emas** — zanjir butunlay serverning o'zida ishlaydi. Tasdiqlangan (`docker logs dl1-bridge` orqali): `push to ThingsBoard OK`.

- Ishlayotgan konteyner: `iep-server`da **`dl1-bridge`** (`--network host --restart=always`, skript: `/home/iep-server/dl1-bridge/dl1_bridge.py`, `localhost:9090` orqali ThingsBoard'ga ulanadi)
- Manba nusxalari loyihada: `v1-thingsboard/legacy/dl1_bridge_server.py` (serverdagi versiya), `v1-thingsboard/legacy/dl1_bridge_local.py` (eski, noutbuk-orqali versiya — endi kerak emas, faqat tarix uchun saqlangan)
- Dashboard qayta yaratish skripti: **`v1-thingsboard/legacy/make_dashboard_office.py`** (server ichidan `python3` bilan ishga tushiriladi, `10.0.2.2:9090` orqali ThingsBoard API'siga ulanadi)
- Serverga ikkita yo'l bilan SSH ulanish mumkin: Tailscale (`<TAILSCALE_IP>`, har qanday joydan) yoki ofis lokal tarmog'idan (`192.168.1.44`, tezroq, faqat shu ofisdan turib)

## ThingsBoard obyektlari (joriy)

- Tenant login: `<TB_USERNAME>` / `<TB_PASSWORD>`
- Device: **Meteostansiya-1** (id: `d3db67d0-a7a5-11f1-94ba-71e730ea5bb5`), access token: `<TB_TOKEN_STATION1>`
- Dashboard: **Meteostansiya-1** (id: `dca756c0-a7a6-11f1-94ba-71e730ea5bb5`) — 6 ta time-series chart widget (Harorat, Namlik, Yorug'lik, Shamol tezligi, Shamol yo'nalishi, Yog'ingarchilik)
  - URL: `http://<TAILSCALE_IP>:9090/dashboards/dca756c0-a7a6-11f1-94ba-71e730ea5bb5` (faqat Tailscale orqali ochiladi)

⚠️ Agar ThingsBoard yana redeploy qilinsa/konteyner qayta yaratilsa, yuqoridagi ID/tokenlar bekor bo'lishi mumkin (agar volume muammosi to'liq tuzatilmagan bo'lsa) — shu holatda device/dashboard'ni qaytadan yaratish kerak bo'ladi (jarayon yuqorida yozilgan, `make_dashboard.py` skripti orqali tez qayta yaratish mumkin, lekin bu skript ham vaqtinchalik scratchpad papkasida).

## Keyingi qadamlar (prioritet bo'yicha)

1. **Ertangi SIM uchun**: DL1'ning `8.Set → a.Wireless IP` maydoniga **`<PUBLIC_IP>:443`** yozish (8888 emas — sslh 443-portda ikkalasini ham ajratadi, "Infratuzilma holati" bo'limi, item 6'ga qarang). UzTelecom'ga port ochish so'rovi yuborish endi shart emas. Bu hali sinovdan o'tkazilmagan — SIM kelgach birinchi navbatda shuni tekshirish kerak (`docker logs dl1-bridge` va `journalctl -u sslh` orqali kuzatish mumkin).
2. ThingsBoard standart parolini (`<TB_USERNAME>`/`<TB_PASSWORD>`) almashtirish.
3. Yomg'ir bayti endi to'g'ri offsetdan (`data[37]`) o'qilmoqda (2026-09-07'da tuzatildi, kod deploy qilindi), lekin ÷10 mm masshtabi va "umumiy yig'indimi yoki qisqa muddatli ko'rsatkichmi" degan savol hali **haqiqiy yomg'ir bilan tasdiqlanishi kerak** (yuqoridagi "DL1 protokoli" bo'limiga qarang).
4. Qolgan 4 ta stansiyani ham xuddi shu tartibda ulash — har biri uchun alohida ThingsBoard device yaratish + `dl1_bridge.py`dagi `DEVICE_TOKENS` xaritasiga IP→token yozuvi qo'shish kerak bo'ladi (server skriptida: `/home/iep-server/dl1-bridge/dl1_bridge.py`, konteynerni qayta ishga tushirish kerak bo'ladi o'zgartirilgach).
5. `dl1_bridge_local.py` (noutbuk-orqali eski versiya) endi shart emas — istasa o'chirib qo'yish mumkin, lekin zarari yo'q.
6. **Domen rejasi: `iep.uz`** — kelajakda korxona veb-saytini shu domenda, Coolify'dagi boshqa loyihalarni esa `subdomen.iep.uz` manzillarida yurgizish rejalashtirilgan (masalan ThingsBoard uchun `tb.iep.uz`). Infratuzilma buning uchun **allaqachon tayyor** — Traefik bir nechta domen/subdomenni parallel Host-based marshrutlash bilan xizmat qiladi va Let's Encrypt sertifikatini avtomatik oladi (bu `downloader.saidmurod.com`da tasdiqlangan). "Infratuzilma holati" bo'limidagi `sslh` o'zgarishi (item 6) bunga xalaqit bermaydi — HTTPS trafik har doim TLS bo'lgani uchun sslh uni avtomatik Traefik'ga yo'naltiradi, 80-port (Let's Encrypt HTTP-01 challenge uchun) umuman o'zgartirilmagan. UzTelecom'ga aloqasi yo'q — hammasi DNS + Coolify darajasida hal bo'ladi:
   - **DNS**: domen registratorda `A` yozuv `iep.uz` → `<PUBLIC_IP>`; qulayligi uchun wildcard `*.iep.uz` → `<PUBLIC_IP>` ham qo'shish tavsiya etiladi (shunda har yangi subdomen uchun alohida DNS yozuv shart bo'lmaydi).
   - **Coolify**: korxona sayti uchun yangi application yaratib, "Domains" maydoniga `iep.uz` (va xohlasa `www.iep.uz`) kiritish; boshqa har bir mavjud/kelajakdagi loyiha uchun ham shunga o'xshab o'z "Domains" maydoniga mos `nimadir.iep.uz` yozish — Traefik/sertifikat avtomatik ishlaydi.
7. Serverdagi qoldiq **apache2** paketini tozalash (ixtiyoriy, zararsiz — "Infratuzilma holati" bo'limidagi item 6'dagi eslatmaga qarang): `systemctl disable --now apache2 && systemctl mask apache2`.
8. **DL1'ning takroriy "osilib qolishi" muammosini sababini topish** ("Infratuzilma holati" bo'limi, item 7'ga qarang) — RS485 kabellarini (ayniqsa yomg'ir sensori) tekshirish hali qilinmagan. Agar takrorlansa, DL1 sotuvchisi/hujjatiga murojaat qilish kerak bo'lishi mumkin.
9. **Ma'lumot to'xtasa ogohlantirish tizimi** (ThingsBoard Notification Center orqali, device inactivity asosida) — foydalanuvchi so'ragan, lekin Chrome kengaytmasi ulanmagani sabab hali sozlanmagan. Kengaytma ishlagach yoki qadam-baqadam qo'lda sozlash orqali davom ettirish kerak.
