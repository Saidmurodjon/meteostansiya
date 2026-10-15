# Server talablari: v1 va v2

5 ta meteostansiya uchun production server talablari. Ikkala versiyada ham DL1 qurilmalari serverga to'g'ridan-to'g'ri TCP orqali ulanadi (tunnel'siz), shuning uchun **statik IPv4 va ochiq TCP port** majburiy.

Yuk hisobi (ikkala versiya uchun bir xil):

- 5 ta stansiya × har 30 soniyada 1 ta 46 baytli freym ≈ sekundiga 0.17 xabar — server uchun juda kichik yuk
- 5 ta stansiya × 9 ta qiymat (harorat, namlik, yorug'lik, shamol tezligi, shamol yo'nalishi, yog'in, batareya kuchlanishi va h.k.) × kuniga 2880 o'lchov ≈ kuniga ~130 ming nuqta
- `Collect Time` 30 daqiqaga qo'yilsa, yuk va disk hajmi ~60 marta kamayadi

---

## v1 — ThingsBoard

```
DL1 ──TCP──▶ dl1-bridge (Python) ──HTTP──▶ ThingsBoard (+ PostgreSQL)
```

Papka: `v1-thingsboard/` (o'z `docker-compose.yml` va `.env` fayli bilan)

Komponentlar:

- `thingsboard/tb-postgres` (ThingsBoard CE + ichki PostgreSQL, Java)
- `bridge/dl1_bridge.py` (DL1 → ThingsBoard)
- ixtiyoriy: Coolify (deploy boshqaruvi)

Minimal talablar (ishlaydi, lekin chegarada):

- CPU: 1 vCPU
- RAM: 2 GB (Java heap'ni qo'lda cheklash shart, Coolify'siz)
- Disk: 20 GB SSD
- OS: Ubuntu 22.04 / 24.04, Docker

Tavsiya etiladigan:

- CPU: 2 vCPU
- RAM: 4 GB (Coolify bilan birga ishlatilsa — majburiy)
- Disk: 40 GB SSD
- OS: Ubuntu 22.04 / 24.04, Docker

O'lchangan resurs (shu Mac'dagi sinovda, 1 stansiya):

- ThingsBoard konteyneri: ~1.2 GB RAM, bo'sh holatda ~8% CPU

Disk o'sishi:

- PostgreSQL'da yiliga ~4–5 GB (30 soniyalik interval, 5 stansiya)

Tarmoq:

- Statik IPv4
- Ochiq TCP port DL1 uchun (masalan 8888)
- 443/80 — ThingsBoard veb interfeysi (HTTPS orqali)

Taxminiy narx:

- Hetzner CX22 (2 vCPU / 4 GB / 40 GB): oyiga ~€4–5
- DigitalOcean / Vultr shunga o'xshash: oyiga ~$12–24

Afzalliklari:

- To'liq IoT platforma: qurilma, token, mijoz, foydalanuvchi boshqaruvi
- Rule engine, Notification Center

Kamchiliklari:

- Og'ir (Java + PostgreSQL), ko'p RAM talab qiladi
- Har stansiya uchun alohida device va dashboard sozlash kerak
- Eski ma'lumotni to'g'ri vaqt bilan import qilish noqulay

---

## v2 — Grafana + VictoriaMetrics

```
DL1 ──TCP──▶ dl1-bridge (Python) ──▶ VictoriaMetrics (saqlaydi) ◀── Grafana (ko'rsatadi, ogohlantiradi)
```

Papka: `v2-grafana/` (o'z `docker-compose.yml` va `.env` fayli bilan). ThingsBoard'ga hech qanday bog'liqligi yo'q.

Komponentlar:

- `victoriametrics/victoria-metrics` (vaqt qatori bazasi)
- `grafana/grafana-oss` (dashboard va ogohlantirishlar)
- `bridge/dl1_bridge.py` (DL1 → VictoriaMetrics)

Minimal talablar:

- CPU: 1 vCPU
- RAM: 1 GB
- Disk: 10 GB SSD
- OS: Ubuntu 22.04 / 24.04, Docker

Tavsiya etiladigan:

- CPU: 1–2 vCPU
- RAM: 2 GB (Coolify bilan birga ishlatilsa — 4 GB)
- Disk: 20 GB SSD
- OS: Ubuntu 22.04 / 24.04, Docker

O'lchangan resurs (shu Mac'dagi sinovda, 1 stansiya):

- VictoriaMetrics: ~27 MB RAM
- Grafana: ~55 MB RAM
- Jami: ~82 MB RAM, bo'sh holatda ~0.5% CPU — ThingsBoard'dan ~14 marta kam

Disk o'sishi:

- VictoriaMetrics'da yiliga bir necha yuz MB (kuchli siqish tufayli)
- Saqlash muddati bitta sozlama bilan belgilanadi (`-retentionPeriod=5y`)

Tarmoq:

- Statik IPv4
- Ochiq TCP port DL1 uchun (masalan 8888)
- 443/80 — Grafana veb interfeysi (ixtiyoriy: Cloudflare proksi + Access orqali)

Taxminiy narx:

- Hetzner eng kichik tarif (1–2 vCPU / 2 GB): oyiga ~€3–4
- Cloudflare (DNS, HTTPS proksi, Access): bepul

Afzalliklari:

- Juda yengil, eng arzon VPS yetadi
- Bitta dashboard, stansiya menyudan tanlanadi
- Ogohlantirishlar ichida bor (Telegram, email)
- Eski ma'lumotni haqiqiy vaqti bilan import qilish oson

Kamchiliklari:

- "Qurilma" tushunchasi yo'q — stansiyalar `station` belgisi bilan ajratiladi
- Foydalanuvchi va ruxsat boshqaruvi soddaroq

---

## Ikkala versiya uchun umumiy talablar

- v1 va v2 bir-biridan mustaqil: istalgan birini alohida serverga o'rnatish mumkin. Ikkalasini bir vaqtda ishlatish uchun ixtiyoriy `tools/dl1_tee.py` DL1 oqimini ikkala bridge'ga nusxalaydi (bitta serverda ikkalasi uchun v1 + v2 resurslari qo'shiladi)

- Statik IPv4 manzil (DL1 domen nomini qabul qilmaydi, faqat IP)
- DL1 uchun ochiq TCP port, firewall'da ruxsat berilgan
- Har stansiyaga alohida SIM (oyiga ~10–20 MB trafik)
- Bridge stansiyani IP bo'yicha emas, freym ichidagi DL1 ID bo'yicha aniqlashi kerak (mobil IP o'zgarib turadi; ID offseti hali aniqlanmagan)
- Vaqtni server qo'yishi kerak — DL1 ichki soati ishonchsiz (qayta yoqilganda 2018-07-25 ga qaytadi)
- Kundalik avtomatik zaxira nusxa (backup)
- Standart parollarni almashtirish (ThingsBoard demo tenant, Grafana admin)
- Server joylashuvi muhim emas (Yevropa ham bo'ladi — 46 baytli freym uchun kechikish ahamiyatsiz)

Narxlar taxminiy, sotib olishdan oldin provayder saytida tekshirilishi kerak.
