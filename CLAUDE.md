# Meteostansiya — loyiha holati

_Oxirgi yangilanish: 2026-09-07 (yomg'ir baytining offseti topildi + DL1 takroriy uzilish muammosi hujjatlashtirildi)_

## Server kirish

Bu loyiha uchun mo'ljallangan server: Ubuntu + Coolify, Tailscale orqali kirish.

- Tailscale IP: `100.111.79.124`
- Tashqi (public) IP: `87.192.241.25` (UzTelecom, faqat 80/443 tashqaridan ochiq — pastga qarang)
- SSH user: `iep-server`
- SSH kalit: `~/.ssh/iep_server`
- Ulanish: `ssh -i ~/.ssh/iep_server iep-server@100.111.79.124`

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
3. **Standart parol muammosi (hali tuzatilmagan)** — ThingsBoard tenant admin login: `tenant@thingsboard.org` / `tenant` (demo standart parol). **Buni albatta o'zgartirish kerak**, ishlab chiqarishga chiqishdan oldin.
4. **Tashqi port muammosi (2026-09-04'da sslh bilan aylanib o'tildi — pastga, item 6'ga qarang)** — UzTelecom firewall'i faqat **80 va 443**ni tashqi internetdan ochiq qoldiradi (tekshirilgan: 8888, 1883, 9090 — hammasi tashqaridan timeout beradi). Server routeri (VORTEX CPE) o'zida port-forwarding funksiyasi yo'q — bu ISP darajasida boshqariladi. UzTelecom'ga alohida port ochish so'rovi yuborish o'rniga, allaqachon ochiq bo'lgan 443-portning o'zida `sslh` protokol-multiplekser orqali DL1 trafigini ham qabul qilish yo'li tanlandi (item 6).
5. **DHCP IP o'zgarishi sabab DL1 uzilib qolgani (tuzatildi, 2026-09-04)** — 2026-09-03 kuni kechqurun (~20:05 UTC) serverda reboot bo'lgan (sabab noaniq, ehtimol ofis elektr uzilishi — shu payt server ham, ehtimol butun ofis tarmog'i ham qayta ko'tarilgan). Reboot'dan keyin server DHCP orqali `eno1`ga **yangi IP (`192.168.1.2`)** olgan, lekin eski `192.168.1.44` DL1'ning `8.Set → b.LAN IP`sida yozilgan holicha qolgan — natijada DL1 "server"ga ma'lumot yuborsa ham, u endi mavjud bo'lmagan/boshqa manzilga ketgan va **~7 soat davomida hech qanday ma'lumot ThingsBoard'ga yetib bormagan** (`dl1-bridge` konteyner o'zi sog'lom edi, faqat DL1'dan ulanish kelmagan). Tashxis: DL1 ping'ga javob berardi, lekin `ss -tn`da 8888-portga bitta ham ulanish urinishi yo'q edi; `nc -zv 192.168.1.44 22` serverning o'z-o'ziga ham "No route to host" berdi — bu server LAN IP'sini yo'qotganini ko'rsatdi. **Yechim**: `eno1`ga statik IP (`192.168.1.44/24`) netplan orqali o'rnatildi (`sudo netplan try` bilan xavfsiz qo'llandi) — endi bu IP hech qachon o'zgarmaydi, DL1 sozlamasini qayta o'zgartirish shart emas. **Saboq**: kelgusida shunga o'xshash "ma'lumot kelmayapti" muammosida birinchi navbatda `ip -4 addr show eno1`ni tekshirish kerak — server IP DL1'da yozilgan manzil bilan mos kelishini tasdiqlash uchun.
6. **sslh port-multiplekser o'rnatildi — SIM uchun UzTelecom'ga murojaat shart emas (2026-09-04)** — DL1 SIM orqali ulanganda mobil operator tarmog'i orqali chiqadi, UzTelecom esa faqat 80/443ni tashqaridan ochiq qoldiradi (item 4). Alohida port (8888) ochishni so'rash o'rniga, serverda **`sslh`** (paket, apt orqali o'rnatilgan) 443-portning o'zida ikki turdagi trafikni ajratadi: TLS/HTTPS so'rovlarini Traefik'ga (`127.0.0.1:8443`), TLS bo'lmagan xom baytli trafikni (DL1'ning binary freymlari) esa `dl1-bridge`ga (`127.0.0.1:8888`) yo'naltiradi.
   - Traefik'ning (`coolify-proxy`) compose fayli (`/data/coolify/proxy/docker-compose.yml`) tahrirlandi: `443:443` → `127.0.0.1:8443:443` (host 443'ni sslh uchun bo'shatish). Zaxira nusxa: `docker-compose.yml.bak-20260904035246` (o'sha papkada).
   - sslh sozlamasi: `/etc/default/sslh` → `DAEMON_OPTS="--user sslh --listen 0.0.0.0:443 --tls 127.0.0.1:8443 --anyprot 127.0.0.1:8888"`, `systemctl enable --now sslh` bilan ishga tushirilgan (doimiy, boot'da avtomatik ko'tariladi).
   - Tekshirildi: sslh loglarida (`journalctl -u sslh`) xom bayt oqimi to'g'ri `127.0.0.1:8888`ga yo'nalgani ko'rindi; `downloader.saidmurod.com` (boshqa loyiha, xuddi shu Traefik orqali) tashqaridan hali ham muammosiz ishlayapti — production'ga hech qanday zarar yetmadi.
   - **Natija**: endi DL1'ning `8.Set → a.Wireless IP` (SIM) maydoniga `87.192.241.25:8888` emas, **`87.192.241.25:443`** yozish kerak — sslh avtomatik DL1 trafigini `dl1-bridge`ga uzatadi. Hali sinovdan o'tkazilmagan (SIM ertaga keladi).
   - Yon effekt (zararsiz): o'rnatish paytida serverda avvaldan yarim-o'rnatilgan **apache2** paketi ham konfiguratsiya qilinib, `systemd`ga yoqilib qoldi. Portlar band bo'lgani uchun ishga tushmayapti (`systemctl status apache2` → failed), lekin hali `enabled` holatda — xohlasa keyinroq `systemctl disable --now apache2 && systemctl mask apache2` bilan tozalash mumkin (bu ish keyinga qoldirildi).
7. **DL1 takroriy "osilib qolishi" (2026-09-07, qisman tuzatildi, ochiq muammo qoldi)** — yomg'ir sensorini qo'lda tekshirish paytida (yuqoridagi DL1 protokoli bo'limiga qarang) DL1 bir necha marta ma'lumot yuborishni to'xtatib qo'ydi:
   - **1-sabab (tuzatildi)**: `dl1_bridge.py`da `conn.settimeout(60)` bor edi — DL1 60 soniyadan ko'proq jim tursa, bridge ulanishni **jimgina** (log yozmasdan) yopib yuborardi, DL1 esa buni tez sezib qayta ulanmasdi (bir marta ~13 daqiqa, oxirida qo'lda o'chirib-yoqishga to'g'ri keldi). Tuzatildi: timeout 600s'ga oshirildi, va yopilganda endi log yoziladi (`"{ip}: idle timeout, closing connection"`).
   - **2-sabab (hali tuzatilmagan, DL1 tomonida)**: bundan tashqari, TCP-ulanish **ochiq (`ESTAB`) holatda turib**, DL1 baribir ma'lumot yuborishni to'xtatib qo'ygan holat ham kuzatildi (bridge tomonidan hech qanday xatolik yo'q, shunchaki DL1 jim). Bu safar ham faqat DL1'ni qo'lda o'chirib-yoqish yordam berdi. Sabab noaniq — ehtimol RS485 shinasi (ayniqsa yomg'ir sensori kabeli qo'lda tekshirilgandan keyin) yoki DL1 firmware'ining o'zidagi tuzatilmagan holat. **Kabellar hali tekshirilmagan** — keyingi safar shu muammo qaytarilsa, birinchi navbatda RS485 A/B ulanishlarini (ayniqsa Addr 0004) tekshirish kerak.
   - **Umumiy tavsiya**: agar grafik yana to'xtab qolsa — avval `ss -tn | grep 192.168.1.50` bilan ulanish holatini tekshiring (yopiqmi yoki "ESTAB" holida osilib qolganmi), keyin `docker logs dl1-bridge --tail 20`. Hozircha yagona ishonchli yechim — DL1'ni qo'lda o'chirib-yoqish.

## MUHIM KASHFIYOT: server ofis bilan bir lokal tarmoqda

`iep-server` nafaqat Tailscale (`100.111.79.124`) orqali, balki **ofisning o'zidagi lokal tarmoqda ham** mavjud ekan: **`192.168.1.44`** (xuddi shu Vortex router ostida, DL1 va bu noutbuk bilan bir subnetda). Bu tasdiqlangan (`ssh iep-server@192.168.1.44` → hostname `iep-server`, bir xil server).

Bu degani: **hozirgi Ethernet testi uchun UzTelecom port ochishini kutish shart emas edi** — DL1'ni to'g'ridan-to'g'ri `192.168.1.44:8888`ga ulash kifoya qildi. ⚠️ Bu faqat lokal (ofis) tarmoqqa tegishli — **ertaga SIM kelganda bu yordam bermaydi**, chunki mobil operator tarmog'i bu lokal Vortex tarmog'idan butunlay mustaqil; SIM uchun baribir UzTelecom'dan tashqi port (8888) ochilishi kerak bo'ladi.

## Joriy ishlaydigan sxema (2026-09-03, yangilangan — to'g'ridan-to'g'ri, ishlaydi)

```
DL1 (ofis, Ethernet, LAN IP Set = 192.168.1.44:8888) → iep-server (lokal tarmoq orqali, dl1-bridge konteyner) → ThingsBoard (localhost:9090, bir hostda)
```

**Noutbuk endi umuman kerak emas** — zanjir butunlay serverning o'zida ishlaydi. Tasdiqlangan (`docker logs dl1-bridge` orqali): `push to ThingsBoard OK`.

- Ishlayotgan konteyner: `iep-server`da **`dl1-bridge`** (`--network host --restart=always`, skript: `/home/iep-server/dl1-bridge/dl1_bridge.py`, `localhost:9090` orqali ThingsBoard'ga ulanadi)
- Manba nusxalari loyihada: `meteostansiya/bridge/dl1_bridge_server.py` (serverdagi versiya), `meteostansiya/bridge/dl1_bridge_local.py` (eski, noutbuk-orqali versiya — endi kerak emas, faqat tarix uchun saqlangan)
- Dashboard qayta yaratish skripti: **`meteostansiya/bridge/make_dashboard.py`** (server ichidan `python3` bilan ishga tushiriladi, `10.0.2.2:9090` orqali ThingsBoard API'siga ulanadi)
- Serverga ikkita yo'l bilan SSH ulanish mumkin: Tailscale (`100.111.79.124`, har qanday joydan) yoki ofis lokal tarmog'idan (`192.168.1.44`, tezroq, faqat shu ofisdan turib)

## ThingsBoard obyektlari (joriy)

- Tenant login: `tenant@thingsboard.org` / `tenant`
- Device: **Meteostansiya-1** (id: `d3db67d0-a7a5-11f1-94ba-71e730ea5bb5`), access token: `FQqLrpZpTDTzi73xnZk0`
- Dashboard: **Meteostansiya-1** (id: `dca756c0-a7a6-11f1-94ba-71e730ea5bb5`) — 6 ta time-series chart widget (Harorat, Namlik, Yorug'lik, Shamol tezligi, Shamol yo'nalishi, Yog'ingarchilik)
  - URL: `http://100.111.79.124:9090/dashboards/dca756c0-a7a6-11f1-94ba-71e730ea5bb5` (faqat Tailscale orqali ochiladi)

⚠️ Agar ThingsBoard yana redeploy qilinsa/konteyner qayta yaratilsa, yuqoridagi ID/tokenlar bekor bo'lishi mumkin (agar volume muammosi to'liq tuzatilmagan bo'lsa) — shu holatda device/dashboard'ni qaytadan yaratish kerak bo'ladi (jarayon yuqorida yozilgan, `make_dashboard.py` skripti orqali tez qayta yaratish mumkin, lekin bu skript ham vaqtinchalik scratchpad papkasida).

## Keyingi qadamlar (prioritet bo'yicha)

1. **Ertangi SIM uchun**: DL1'ning `8.Set → a.Wireless IP` maydoniga **`87.192.241.25:443`** yozish (8888 emas — sslh 443-portda ikkalasini ham ajratadi, "Infratuzilma holati" bo'limi, item 6'ga qarang). UzTelecom'ga port ochish so'rovi yuborish endi shart emas. Bu hali sinovdan o'tkazilmagan — SIM kelgach birinchi navbatda shuni tekshirish kerak (`docker logs dl1-bridge` va `journalctl -u sslh` orqali kuzatish mumkin).
2. ThingsBoard standart parolini (`tenant@thingsboard.org`/`tenant`) almashtirish.
3. Yomg'ir bayti endi to'g'ri offsetdan (`data[37]`) o'qilmoqda (2026-09-07'da tuzatildi, kod deploy qilindi), lekin ÷10 mm masshtabi va "umumiy yig'indimi yoki qisqa muddatli ko'rsatkichmi" degan savol hali **haqiqiy yomg'ir bilan tasdiqlanishi kerak** (yuqoridagi "DL1 protokoli" bo'limiga qarang).
4. Qolgan 4 ta stansiyani ham xuddi shu tartibda ulash — har biri uchun alohida ThingsBoard device yaratish + `dl1_bridge.py`dagi `DEVICE_TOKENS` xaritasiga IP→token yozuvi qo'shish kerak bo'ladi (server skriptida: `/home/iep-server/dl1-bridge/dl1_bridge.py`, konteynerni qayta ishga tushirish kerak bo'ladi o'zgartirilgach).
5. `dl1_bridge_local.py` (noutbuk-orqali eski versiya) endi shart emas — istasa o'chirib qo'yish mumkin, lekin zarari yo'q.
6. **Domen rejasi: `iep.uz`** — kelajakda korxona veb-saytini shu domenda, Coolify'dagi boshqa loyihalarni esa `subdomen.iep.uz` manzillarida yurgizish rejalashtirilgan (masalan ThingsBoard uchun `tb.iep.uz`). Infratuzilma buning uchun **allaqachon tayyor** — Traefik bir nechta domen/subdomenni parallel Host-based marshrutlash bilan xizmat qiladi va Let's Encrypt sertifikatini avtomatik oladi (bu `downloader.saidmurod.com`da tasdiqlangan). "Infratuzilma holati" bo'limidagi `sslh` o'zgarishi (item 6) bunga xalaqit bermaydi — HTTPS trafik har doim TLS bo'lgani uchun sslh uni avtomatik Traefik'ga yo'naltiradi, 80-port (Let's Encrypt HTTP-01 challenge uchun) umuman o'zgartirilmagan. UzTelecom'ga aloqasi yo'q — hammasi DNS + Coolify darajasida hal bo'ladi:
   - **DNS**: domen registratorda `A` yozuv `iep.uz` → `87.192.241.25`; qulayligi uchun wildcard `*.iep.uz` → `87.192.241.25` ham qo'shish tavsiya etiladi (shunda har yangi subdomen uchun alohida DNS yozuv shart bo'lmaydi).
   - **Coolify**: korxona sayti uchun yangi application yaratib, "Domains" maydoniga `iep.uz` (va xohlasa `www.iep.uz`) kiritish; boshqa har bir mavjud/kelajakdagi loyiha uchun ham shunga o'xshab o'z "Domains" maydoniga mos `nimadir.iep.uz` yozish — Traefik/sertifikat avtomatik ishlaydi.
7. Serverdagi qoldiq **apache2** paketini tozalash (ixtiyoriy, zararsiz — "Infratuzilma holati" bo'limidagi item 6'dagi eslatmaga qarang): `systemctl disable --now apache2 && systemctl mask apache2`.
8. **DL1'ning takroriy "osilib qolishi" muammosini sababini topish** ("Infratuzilma holati" bo'limi, item 7'ga qarang) — RS485 kabellarini (ayniqsa yomg'ir sensori) tekshirish hali qilinmagan. Agar takrorlansa, DL1 sotuvchisi/hujjatiga murojaat qilish kerak bo'lishi mumkin.
9. **Ma'lumot to'xtasa ogohlantirish tizimi** (ThingsBoard Notification Center orqali, device inactivity asosida) — foydalanuvchi so'ragan, lekin Chrome kengaytmasi ulanmagani sabab hali sozlanmagan. Kengaytma ishlagach yoki qadam-baqadam qo'lda sozlash orqali davom ettirish kerak.
