# OtoRadar

🌐 **Canlı demo:** https://otoradar.net.tr

Araç ilanlarını yöneten, ilan fiyatlarını Pandas ve SQL ile analiz eden ve doğal dilde soru cevaplayan bir AI asistanı içeren Django uygulaması. İki node'lu bir K3s (Kubernetes) cluster'ında, PostgreSQL ve HTTPS ile çalışır.

**Kullanılan teknolojiler:** Python 3.12, Django 6, Django REST Framework, Pandas, Google Gemini (tool calling), PostgreSQL, Docker, K3s, Traefik, cert-manager + Let's Encrypt, WireGuard

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
| Otomatik testler (parser, router, analiz, sayfalar, API) | `listings/tests.py` |

## Mimari

```
Tarayıcı ──► Django (views, templates) ──► ORM / ham SQL ──► SQLite (local) / PostgreSQL (K3s)
                    │
                    └──► agent.py
                          ├─ basit fiyat sorusu ──► parser.py ──► analytics.py   (LLM yok)
                          └─ yorum / anomali    ──► Gemini ──tool çağrısı──► analytics.py
```

**Agent nasıl çalışır?** Soru önce hibrit router'a gelir. "2020 BMW 3 Serisi kaç TL?" gibi net bir fiyat sorusunda marka, model ve yıl kural tabanlı parser ile çıkarılır ve cevap doğrudan veritabanından üretilir: hızlı, ücretsiz ve her seferinde aynı. "Corolla alınır mı?" gibi yorum gerektiren veya "5 numaralı ilan normal mi?" gibi sorular Gemini'ye gider. Gemini'ye iki Python fonksiyonu tool olarak verilir (`get_price_stats`, `check_listing_anomaly`); model hangisini hangi parametreyle çağıracağına kendisi karar verir, fonksiyon gerçek veriyi döndürür, model de bunu yorumlayıp Türkçe cevap yazar. Sistem talimatı veri uydurmayı yasaklar.

Asistan sayfasında her cevabın yanında kaynağı yazar ("Veritabanından" veya "Gemini"). Aynı araç için "kaç TL?" ve "alınır mı?" soruları sorulduğunda iki yoldan gelen sayıların birebir aynı olması, modelin veri uydurmadığını gösterir.

**Anomali tespiti:** İlan, aynı marka + model ve ±2 model yılı grubuyla karşılaştırılır. `z = (fiyat − grup ortalaması) / grup standart sapması`; `|z| > 2` ise anomali. Normal dağılımda değerlerin yaklaşık %95'i ±2σ içinde kaldığı için bu eşik, "her 20 ilandan birinden daha nadir" fiyatları işaretler.

### Sunucu yapısı (K3s)

```
                         https://otoradar.net.tr
                                   │
┌───────────── node1 (control-plane) ─────────────┐   ┌──────── node2 (worker) ────────┐
│ K3s API + scheduler, kubectl                    │   │                                 │
│ Traefik (Ingress) + cert-manager                │◄─►│ Django pod'u                    │
│ PostgreSQL pod'u (kalıcı disk)                  │ WG│                                 │
│ Django pod'u                                    │   │                                 │
└─────────────────────────────────────────────────┘   └─────────────────────────────────┘
```

İki Django pod'u farklı node'larda çalışır (`topologySpreadConstraints`). node2 kapanırsa trafik node1'deki pod'a gider, site ayakta kalır. Node'lar arası pod trafiği açık internetten geçtiği için WireGuard (WG) ile şifrelenir.

**Bilinen sınırlama:** Bu yapı yalnızca web katmanını korur. node1 çökerse K3s yönetimi, Traefik ve PostgreSQL birlikte gider; sistemin tek zayıf noktası node1'dir. Üretimde çözüm, birden fazla control-plane, veritabanı replikasyonu ve yük dengeleyicinin node'lardan bağımsız olmasıdır.

### Kubernetes'e kurulum

```bash
kubectl apply -f k8s/00-namespace.yaml
DB_PASS=$(openssl rand -hex 16)
kubectl -n otoradar create secret generic otoradar-secrets \
  --from-literal=POSTGRES_PASSWORD="$DB_PASS" \
  --from-literal=DATABASE_URL="postgres://otoradar:${DB_PASS}@postgres:5432/otoradar" \
  --from-literal=DJANGO_SECRET_KEY="$(openssl rand -hex 32)" \
  --from-literal=GEMINI_API_KEY='...'
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.21.0/cert-manager.yaml
kubectl apply -f k8s/
kubectl -n otoradar exec deploy/otoradar-web -- python manage.py generate_data --count 3000
```

| Dosya | İçerik |
|---|---|
| `k8s/00-namespace.yaml` | `otoradar` namespace'i |
| `k8s/10-configmap.yaml` | Gizli olmayan ayarlar (DEBUG, izinli alan adları) |
| `k8s/20-postgres.yaml` | PostgreSQL, node1'e sabit, kalıcı disk (PVC) |
| `k8s/30-migrate-job.yaml` | Veritabanı tablolarını oluşturan tek seferlik iş |
| `k8s/40-web.yaml` | 2 kopya Django, node'lara yayılmış, sağlık kontrolleri |
| `k8s/50-ingress.yaml` | Alan adı için HTTPS Ingress, HTTP→HTTPS yönlendirme, IP erişimi |
| `k8s/60-cluster-issuer.yaml` | Let's Encrypt sertifika tanımı |

Gizli değerler repoda değil, yalnızca cluster içindeki Secret'ta durur. Node'lar arası pod trafiği açık internet üzerinden geçtiği için Flannel `wireguard-native` backend'i ile şifrelenir.

**HTTPS:** cert-manager, Let's Encrypt'ten HTTP-01 doğrulamasıyla ücretsiz sertifika alır ve süresi dolmadan otomatik yeniler (`k8s/60-cluster-issuer.yaml`). Alan adına gelen `http://` istekleri Traefik middleware'i ile `https://` adresine yönlendirilir (`308 Permanent Redirect`); IP üzerinden erişim test amaçlı düz HTTP olarak bırakılmıştır.

### Yeni sürüm yayınlama

Kod değiştiğinde image yeni bir sürüm numarasıyla oluşturulur, iki node'a yüklenir ve deployment kesintisiz güncellenir:

```bash
# node1
cd ~/otoradar && git pull
docker build -t otoradar:1.1 .
docker save otoradar:1.1 -o /root/otoradar-1.1.tar
k3s ctr images import /root/otoradar-1.1.tar
scp /root/otoradar-1.1.tar root@<node2-ip>:/root/
# node2
k3s ctr images import /root/otoradar-1.1.tar
# node1
kubectl -n otoradar set image deployment/otoradar-web web=otoradar:1.1
```

Bir sonraki adım bu süreci CI/CD ile (örneğin GitHub Actions + bir container registry) otomatikleştirmek olurdu.

### Node failure demosu (ölçülmüş sonuçlar)

node1'den saniyede bir `curl` ile siteye istek atılırken node2 `poweroff` ile kapatıldı:

| Zaman | Olay |
|---|---|
| T+0 sn | node2 kapandı |
| T+1 – T+45 sn | Kısmi kesinti: isteklerin bir kısmı node2'deki pod'a gidip zaman aşımına uğradı, diğerleri node1'den `200` döndü. Site hiçbir an tamamen kapanmadı |
| ~T+45 sn | node2 `NotReady` işaretlendi, pod'u servis uç noktalarından çıkarıldı. Tüm istekler `200` |
| ~T+75 sn | `tolerationSeconds: 30` doldu, node2'deki pod `Terminating` oldu, node1'de yeni pod açıldı (11 sn'de hazır) |

node2 geri açıldığında pod'lar otomatik geri taşınmaz; `kubectl rollout restart deployment otoradar-web` ile kesintisiz (rolling update) yeniden dağıtıldı.

**Kesintiyi kısaltmak için:** Kubernetes'in node'un öldüğüne karar verme süresi (`node-monitor-grace-period`) kısaltılabilir veya Traefik'e aktif health-check eklenebilir. Bu sürenin çok kısa olması ise kısa ağ dalgalanmalarında gereksiz pod taşımalarına yol açar; varsayılan bilinçli olarak korundu.

## Kurulum (local)

```bash
git clone https://github.com/sevvalfirat/otoradar.git
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
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Formların gönderilebileceği adresler (`https://...`) |
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

Canlı örnek: https://otoradar.net.tr/api/listings/?brand=Toyota

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
| 11 | `http://otoradar.net.tr` | `https://` adresine yönlendirilir, geçerli sertifika |
| 12 | node2 kapatılır | Site ayakta kalır, pod node1'de yeniden açılır |

## Ekran görüntüleri

> `docs/` klasörüne ekran görüntülerini ekleyip buraya bağla:
> `![İlanlar](docs/ilanlar.png)`
