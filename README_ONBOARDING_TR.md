# VentureAgent — Geliştirici Onboarding Rehberi

VentureAgent projesine hoş geldiniz! Bu belge, yeni yazılım mühendislerinin projenin amacını, teknoloji yığınını, mimarisini ve yerel geliştirme ortamını nasıl ayağa kaldıracaklarını hızlıca anlamalarına yardımcı olmak için tasarlanmıştır.

---

## 1. Proje Amacı ve Yönetici Özeti

**VentureAgent**, sanal bir kurucu ortak ve startup danışmanı olarak hizmet veren yapay zekâ destekli bir web uygulamasıdır. Girişimcilerin ve kurucu adaylarının bir fikri alıp yapılandırılmış, uygulanabilir bir iş planına dönüştürmelerine yardımcı olur.

Kullanıcı, pahalı ve zaman alan danışmanlık süreçlerinden geçmek yerine startup fikrini düz metin olarak girebilir. VentureAgent daha sonra bu fikri analiz eder, doğrular ve aşağıdaki gibi çeşitli iş çıktıları üretir:
- **Fikir Analizi ve Venture Skoru:** Güçlü yönleri, zayıf yönleri ve hazırlık durumunu değerlendirir.
- **SWOT Analizi:** Güçlü yönleri, Zayıf yönleri, Fırsatları ve Tehditleri belirler.
- **Rakip Araştırması:** Potansiyel rakipleri ve konumlandırma stratejilerini bulur.
- **Gelir Modelleri:** Fikirden nasıl gelir elde edilebileceğini önerir.
- **MVP Yol Haritası ve Kanban:** Adım adım bir yol haritası ve etkileşimli Kanban görevleri oluşturur.
- **Yatırımcı ve Sunum Tavsiyeleri:** Asansör konuşmaları (elevator pitch) ve yatırımcı stratejileri üretir.

---

## 2. Kullanılan Teknolojiler ve Framework'ler

Proje, yapay zekâ entegrasyonuna güçlü bir vurgu yapan monolitik bir web uygulaması olarak inşa edilmiştir.

- **Backend (Arka Uç):** Python 3 ve **Flask** (Yönlendirme, API uç noktaları ve şablon oluşturma sağlar).
- **Veritabanı:** **SQLite** (Yerleşik `sqlite3` modülü ile yönetilir. Üretilen analizleri, metrikleri ve panoları kalıcı olarak saklamak için kullanılır).
- **Yapay Zekâ / YDD (LLM) Entegrasyonları:**
  - **Google Gemini API** (Varsayılan model: `gemini-2.5-flash`). İş içgörüleri üretmek için kullanılır.
  - **Anthropic API** (Model: `claude-sonnet-5`). Yapılandırma yoluyla alternatif bir sağlayıcı olarak desteklenir.
- **Frontend (Ön Yüz):** Vanilla HTML, CSS ve JavaScript (Şu anda React veya Vue gibi ağır framework'ler kullanılmamaktadır, bu da ön yüzü hafif ve basit tutar).

---

## 3. Sistem Mimarisi ve İş Akışı

### Temel Mimari
VentureAgent, harici bir Yapay Zekâ Servisi bağımlılığı olan klasik bir İstemci-Sunucu (Client-Server) mimarisini izler.

1. **İstemci (Frontend):** Kullanıcı, Flask tarafından sunulan HTML şablonlarıyla etkileşime girer. Dinamik eylemler (örneğin yeni bir fikir analizi tetiklemek) için ön yüzden Flask arka ucuna AJAX/Fetch çağrıları yapılır.
2. **Sunucu (Flask Backend):** 
   - **Rotalar (`backend/routes/`):** Her ana özelliğin (SWOT, Kanban, Gelir, Rakipler) kendi yönlendirme modülü vardır. 
   - **Veritabanı (`backend/database.py`):** CRUD (Oluşturma, Okuma, Güncelleme, Silme) işlemlerini yönetir. Bir kullanıcı fikir gönderdiğinde, arka uç üretilen `venture_score`, `risk_level` ve ham yapay zekâ analizini `idea_analyses` tablosuna kaydeder.
3. **Yapay Zekâ Servisi (`backend/services/ai_client.py`):** Uygulama, karmaşık bir çoklu ajan sistemi yerine tek modelli, çok turlu (multi-turn) bir yaklaşıma dayanır. `ai_client.py` modülü, sağlayıcıdan bağımsız bir sarmalayıcı (wrapper) olarak işlev görür. İstemleri biçimlendirir, gerektiğinde JSON çıktısını zorunlu kılar ve kendi API'leri aracılığıyla Gemini (veya Claude) ile güvenli bir şekilde iletişim kurar.

### Veri Akışı Örneği (Fikir Analizi)
1. Kullanıcı, ön yüzde startup fikrini girer ve gönder (submit) butonuna tıklar.
2. İstek arka uç rotasına (örneğin `backend/routes/idea.py` içine) ulaşır.
3. Rota, belirli bir istem (prompt) oluşturur ve `ai_client.py` içinden `ask_ai()` fonksiyonunu çağırır.
4. `ai_client.py`, istemi Google Gemini API'sine gönderir.
5. Gemini API, yapılandırılmış bir yanıt (genellikle JSON formatında) döndürür.
6. Arka uç bu yanıtı ayrıştırır, elde edilen metrikleri `save_idea_analysis()` aracılığıyla SQLite veritabanına kaydeder ve verileri görüntülenmek üzere ön yüze döndürür.

---

## 4. Kurulum ve Çalıştırma Talimatları

Projeyi yerel ortamınızda ayağa kaldırmak için şu adımları izleyin:

### Ön Koşullar
- Python 3.9+ yüklü olmalıdır.
- Google Gemini (ve isteğe bağlı olarak Anthropic Claude) için API anahtarları.

### Adım Adım Kılavuz
1. **Depoyu Klonlayın (henüz yapmadıysanız):**
   ```bash
   git clone <repository-url>
   cd VentureAgent
   ```

2. **Sanal Ortam (Virtual Environment) Oluşturun:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Windows üzerinde: venv\Scripts\activate
   ```

3. **Bağımlılıkları Yükleyin:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Ortam Değişkenleri:**
   - Kendi ortam dosyanızı oluşturmak için örnek dosyayı kopyalayın:
     ```bash
     cp .env.example .env
     ```
   - `.env` dosyasını açın ve API anahtarlarınızı doldurun:
     ```env
     GEMINI_API_KEY=sizin_gemini_api_anahtariniz
     ANTHROPIC_API_KEY=sizin_anthropic_api_anahtariniz
     AI_PROVIDER=gemini  # veya claude
     FLASK_DEBUG=True
     PORT=5000
     ```

5. **Uygulamayı Çalıştırın:**
   ```bash
   python run.py
   ```
   Veritabanı tabloları ilk çalıştırmada otomatik olarak oluşturulacaktır.

6. **Web Uygulamasına Erişin:**
   Tarayıcınızı açın ve `http://localhost:5000` adresine gidin.

---

## 5. Proje Yapısı

İşte temel dizinlerin ve dosyaların bir dökümü:

```text
VentureAgent/
├── run.py                    # Uygulamanın giriş noktası. Flask sunucusunu başlatır.
├── requirements.txt          # Python bağımlılıkları (Flask, python-dotenv, anthropic vb.).
├── .env.example              # Ortam değişkenleri için şablon.
├── README.md                 # Orijinal proje özeti ve sprint notları.
├── backend/                  # Arka uç uygulama mantığı.
│   ├── __init__.py           # Flask app factory (create_app).
│   ├── database.py           # SQLite bağlantı kurulumu, şema oluşturma ve CRUD işlevleri.
│   ├── routes/               # Her özellik için modüler Flask blueprint'leri.
│   │   ├── idea.py           # İlk fikir analizi için rotalar.
│   │   ├── swot.py           # SWOT oluşturma için rotalar.
│   │   ├── kanban.py         # MVP görev oluşturma için rotalar.
│   │   └── ...               # (competitors, revenue, roadmap, pitch vb.)
│   └── services/
│       └── ai_client.py      # Gemini ve Claude API'leriyle iletişim kuran temel yapay zekâ sarmalayıcısı.
├── frontend/                 # Ön yüz varlıkları ve şablonları.
│   ├── static/               # CSS stilleri, JavaScript mantığı ve resimler/logolar.
│   └── templates/            # Flask tarafından işlenen (render edilen) HTML dosyaları.
└── data_science/             # Veri analitiği, not defterleri (notebooks) ve modeller (ör. keşifsel not defterleri, veri hatları).
```
