# OtoRadar

Araç ilanlarını yöneten, ilan fiyatlarını Pandas ve SQL ile analiz eden ve doğal dilde soru cevaplayan bir AI asistanı içeren Django uygulaması.

## Özellikler

| Özellik | Nerede |
|---|---|
| İlan listeleme (sayfalı), detay, ekleme, düzenleme, silme | `listings/views.py`, `listings/templates/` |
| Marka, maksimum fiyat ve yakıt filtresi; filtreler sayfalar arasında korunur | `ListingListView` |
| REST API, filtreleme, arama, sıralama, sayfalama | `/api/listings/` → `listings/api_views.py` |
| 3000 sentetik ilan (%3 bilinçli fiyat anomalisi) | `python manage.py generate_data` |
| Marka / model / yıl bazlı fiyat istatistiği (Pandas) | `analytics.price_stats` |
| Z-score ile fiyat anomalisi tespiti | `analytics.detect_anomaly`, ilan detay sayfası |
| Ham SQL (`GROUP BY`) marka özeti ve grafikler | `/istatistik/` → `analytics.brand_summary_sql` |
| Tool calling kullanan AI asistanı + hibrit router | `/asistan/` → `listings/agent.py` |
| Hata durumunda nazik yedek mesaj ve loglama | `agent.answer_question` |

## Mimari

```
Tarayıcı ──► Django (views, templates) ──► ORM / ham SQL ──► SQLite (local) / PostgreSQL (K3s)
                    │
                    └──► agent.py
                          ├─ basit fiyat sorusu ──► parser.py ──► analytics.py   (LLM yok)
                          └─ yorum / anomali    ──► Gemini ──tool çağrısı──► analytics.py
```

**Agent nasıl çalışır?** Soru önce hibrit router'a gelir. "2020 BMW 3 Serisi kaç TL?" gibi net bir fiyat sorusunda marka, model ve yıl kural tabanlı parser ile çıkarılır ve cevap doğrudan veritabanından üretilir: hızlı, ücretsiz ve her seferinde aynı. "Corolla alınır mı?" gibi yorum gerektiren veya "5 numaralı ilan normal mi?" gibi sorular Gemini'ye gider. Gemini'ye iki Python fonksiyonu tool olarak verilir (`get_price_stats`, `check_listing_anomaly`); model hangisini hangi parametreyle çağıracağına kendisi karar verir, fonksiyon gerçek veriyi döndürür, model de bunu yorumlayıp Türkçe cevap yazar. Sistem talimatı veri uydurmayı yasaklar.

**Anomali tespiti:** İlan, aynı marka + model ve ±2 model yılı grubuyla karşılaştırılır. `z = (fiyat − grup ortalaması) / grup standart sapması`; `|z| > 2` ise anomali. Normal dağılımda değerlerin yaklaşık %95'i ±2σ içinde kaldığı için bu eşik, "her 20 ilandan birinden daha nadir" fiyatları işaretler.

### Sunucu yapısı (K3s)

```
┌───────────── node1 (control-plane) ─────────────┐   ┌──────── node2 (worker) ────────┐
│ K3s API + scheduler, kubectl                    │◄─►│ Django pod'u                    │
│ PostgreSQL pod'u                                │   │                                 │
│ Django pod'u                                    │   │                                 │
└─────────────────────────────────────────────────┘   └─────────────────────────────────┘
```

İki Django pod'u farklı node'larda çalışır. node2 kapanırsa trafik node1'deki pod'a gider, site ayakta kalır.

**Bilinen sınırlama:** Bu yapı yalnızca web katmanını korur. node1 çökerse hem K3s yönetimi hem PostgreSQL gider; sistemin tek zayıf noktası node1'dir. Üretimde çözüm, birden fazla control-plane ve veritabanı replikasyonudur.

## Kurulum (local)

```bash
git clone <repo-adresi> otoradar
cd otoradar
python -m venv venv
venv\Scripts\activate            # Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env           # Mac/Linux: cp .env.example .env  → sonra değerleri doldur
python manage.py migrate
python manage.py generate_data --count 3000
python manage.py createsuperuser
python manage.py runserver
```

Tarayıcıda: http://127.0.0.1:8000

### Ortam değişkenleri

| Değişken | Açıklama |
|---|---|
| `DJANGO_SECRET_KEY` | Django gizli anahtarı |
| `DJANGO_DEBUG` | `True` sadece geliştirmede |
| `DJANGO_ALLOWED_HOSTS` | Virgülle ayrılmış alan adları / IP'ler |
| `GEMINI_API_KEY` | aistudio.google.com'dan alınan anahtar |
| `GEMINI_MODEL` | Kullanılacak Gemini modeli |
| `DATABASE_URL` | Tanımlıysa PostgreSQL kullanılır, değilse SQLite |

`.env` dosyası `.gitignore` içindedir; API anahtarları asla repoya girmez.

## Faydalı komutlar

```bash
python manage.py test listings            # birim testleri
python manage.py sqlmigrate listings 0001 # modelin ürettiği CREATE TABLE SQL'i
python manage.py generate_data --clear    # verileri silip yeniden üret
```

## API örnekleri

```
GET /api/listings/                         sayfalı liste (20'şer)
GET /api/listings/?brand=Toyota            marka filtresi
GET /api/listings/?search=corolla          arama
GET /api/listings/?ordering=-price         fiyata göre azalan
```

## Test senaryoları

| # | Girdi | Beklenen |
|---|---|---|
| 1 | Ana sayfa | İlanlar listeleniyor, sayfalama çalışıyor |
| 2 | Marka "BMW" + "Sonraki sayfa" | Filtre korunuyor |
| 3 | Yeni ilan / düzenle / sil | Üçü de çalışıyor, silmeden önce onay isteniyor |
| 4 | `/api/listings/?brand=Toyota` | Yalnızca Toyota, sayfalı JSON |
| 5 | Asistan: "2020 model BMW 3 Serisi kaç TL?" | "Veritabanından" etiketli istatistik cevabı |
| 6 | Asistan: "Toyota Corolla alınır mı?" | Gemini yorumu |
| 7 | Asistan: "5 numaralı ilanın fiyatı normal mi?" | `check_listing_anomaly` çağrılır |
| 8 | İlan detayı | Fiyat analizi paneli ve fiyat cetveli |
| 9 | `.env`'deki key bozuk | Nazik hata mesajı, terminalde gerçek hata |
| 10 | `/istatistik/` | Tablo ve grafikler |

## Ekran görüntüleri

> `docs/` klasörüne ekran görüntülerini ekleyip buraya bağla:
> `![İlanlar](docs/ilanlar.png)`
